package main

import (
	"bufio"
	"context"
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"logccino/internal/config"
	"logccino/internal/datagen"
	"logccino/internal/splunk"
)

type datasetSpec struct {
	Name        string
	Category    string // "dlp" or "network"
	URL         string
	FileName    string
	Sourcetype  string
	TargetIndex []string
}

func main() {
	destDir := flag.String("dir", "testdata/exfiltration", "Directory to store downloaded datasets")
	targetIdx := flag.String("index", "all", "Target index filter ('all', 'test_dlp', 'test_network', 'test_exfiltration')")
	dailyFlag := flag.Bool("daily", false, "Run as background scheduler generating test data daily at 06:00 AM")
	flag.Parse()

	cfg, err := config.Load(".env")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	if *dailyFlag {
		fmt.Printf("==> Starting Daily Test Data Scheduler (%02d:%02d daily). Press Ctrl+C to stop...\n", cfg.TestDataScheduleHour, cfg.TestDataScheduleMinute)
		sched := datagen.NewScheduler(cfg)
		sched.Start()
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		<-quit
		sched.Stop()
		return
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

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	if err := os.MkdirAll(*destDir, 0755); err != nil {
		log.Fatalf("Failed to create dataset directory: %v", err)
	}

	// 1. Ensure test indexes exist
	testIndexes := []string{"test_dlp", "test_network", "test_exfiltration", "dlp", "proxy"}
	fmt.Println("==> [1/4] Ensuring Splunk indexes exist...")
	for _, idx := range testIndexes {
		if err := cli.CreateIndex(ctx, idx); err != nil {
			log.Printf("[WARN] Index %s creation notice: %v", idx, err)
		} else {
			fmt.Printf("    - Index '%s' ready.\n", idx)
		}
	}

	// 2. Define curated Data Exfiltration & DLP datasets from Splunk STRT (splunk/attack_data)
	datasets := []datasetSpec{
		{
			Name:        "O365 SharePoint / OneDrive Suspicious File Exfiltration",
			Category:    "dlp",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1567/o365_sus_file_activity/o365_sus_file_activity.log",
			FileName:    "o365_sus_file_activity.log",
			Sourcetype:  "o365:management:activity",
			TargetIndex: []string{"test_dlp", "test_exfiltration", "dlp"},
		},
		{
			Name:        "HTTP Plain Exfiltration Network Stream Traffic",
			Category:    "network",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1048.003/plain_exfil_data/stream_http_events.log",
			FileName:    "stream_http_plain_exfil.log",
			Sourcetype:  "stream:http",
			TargetIndex: []string{"test_network", "test_exfiltration"},
		},
		{
			Name:        "HTTP Archive POST Exfiltration Stream Traffic",
			Category:    "network",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1048.003/archive_http_post/stream_http_events.log",
			FileName:    "stream_http_archive_exfil.log",
			Sourcetype:  "stream:http",
			TargetIndex: []string{"test_network", "test_exfiltration"},
		},
		{
			Name:        "Large Web Upload Exfiltration via Nginx Proxy",
			Category:    "network",
			URL:         "https://media.githubusercontent.com/media/splunk/attack_data/master/datasets/attack_techniques/T1567/web_upload_nginx/web_upload_nginx.log",
			FileName:    "web_upload_nginx.log",
			Sourcetype:  "nginx:plus:access",
			TargetIndex: []string{"test_network", "test_exfiltration", "proxy"},
		},
	}

	// 3. Download & Ingest datasets
	fmt.Println("\n==> [2/4] Downloading and ingesting datasets into Splunk...")
	httpClient := &http.Client{
		Timeout: 90 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}

	for _, ds := range datasets {
		localPath := filepath.Join(*destDir, ds.FileName)
		if err := downloadFileIfMissing(httpClient, ds.URL, localPath); err != nil {
			log.Printf("[ERROR] Failed to download %s: %v", ds.Name, err)
			continue
		}

		fi, err := os.Stat(localPath)
		if err != nil || fi.Size() == 0 {
			log.Printf("[ERROR] Downloaded file is empty: %s", localPath)
			continue
		}
		fmt.Printf("==> Processing dataset: %s (%.2f KB)\n", ds.Name, float64(fi.Size())/1024.0)

		// Filter targets if flag set
		for _, idx := range ds.TargetIndex {
			if *targetIdx != "all" && *targetIdx != idx {
				continue
			}
			fmt.Printf("    -> Ingesting into index '%s' (sourcetype: %s)...\n", idx, ds.Sourcetype)
			count, err := ingestFileInBatches(ctx, cli, idx, ds.Sourcetype, localPath)
			if err != nil {
				log.Printf("    [ERROR] Ingest failed for %s into %s: %v", ds.FileName, idx, err)
			} else {
				fmt.Printf("    [OK] Ingested %d events into '%s'\n", count, idx)
			}
		}
	}

	// 4. Ingest Enterprise DLP Policy Violation Events (Financial, Source Code, PII Leaks)
	fmt.Println("\n==> [3/4] Ingesting Enterprise DLP policy violation events...")
	dlpEvents := generateEnterpriseDLPEvents()

	for _, idx := range []string{"test_dlp", "test_exfiltration", "dlp"} {
		if *targetIdx != "all" && *targetIdx != idx {
			continue
		}
		ingestedCount := 0
		for _, ev := range dlpEvents {
			b, _ := json.Marshal(ev)
			if err := cli.IngestRaw(ctx, idx, "dlp:event", string(b)); err != nil {
				log.Printf("    [ERROR] Ingest enterprise DLP failed for %s: %v", idx, err)
			} else {
				ingestedCount++
			}
		}
		fmt.Printf("    [OK] Ingested %d enterprise DLP policy events into '%s'\n", ingestedCount, idx)
	}

	// 5. Verification queries
	fmt.Println("\n==> [4/4] Verifying ingested data with Splunk search queries...")
	time.Sleep(2 * time.Second) // allow indexing buffer commit

	verifyIndexes := []string{"test_dlp", "test_network", "test_exfiltration"}
	for _, idx := range verifyIndexes {
		spl := fmt.Sprintf("search index=%s | stats count by sourcetype", idx)
		rows, err := cli.Export(ctx, spl, "-24h", "now", 50)
		if err != nil {
			// Try without time boundary
			rows, _ = cli.Export(ctx, fmt.Sprintf("search index=%s | stats count by sourcetype", idx), "0", "now", 50)
		}
		fmt.Printf("\n--- Index: %s Summary ---\n", idx)
		if len(rows) == 0 {
			fmt.Println("    (No events counted yet or pending index commit)")
		} else {
			for _, r := range rows {
				fmt.Printf("    - Sourcetype: %-32v | Count: %v\n", r["sourcetype"], r["count"])
			}
		}
	}

	fmt.Println("\n==> Data loading and verification complete!")
}

func downloadFileIfMissing(client *http.Client, url, destPath string) error {
	if fi, err := os.Stat(destPath); err == nil && fi.Size() > 0 {
		return nil
	}

	fmt.Printf("    -> Downloading %s...\n", filepath.Base(destPath))
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "logccino-data-loader/1.0")

	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP error %d: %s", resp.StatusCode, resp.Status)
	}

	tmpFile := destPath + ".tmp"
	out, err := os.Create(tmpFile)
	if err != nil {
		return err
	}
	defer out.Close()

	if _, err := io.Copy(out, resp.Body); err != nil {
		_ = os.Remove(tmpFile)
		return err
	}
	out.Close()

	return os.Rename(tmpFile, destPath)
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
	if err := scanner.Err(); err != nil {
		return 0, err
	}

	// Limit to top 1000 events if huge, to ensure fast processing
	if len(lines) > 1000 {
		lines = lines[:1000]
	}

	total := len(lines)
	workers := 12
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
			"event_id":           "DLP-EXFIL-001",
			"timestamp":          now - 120,
			"_time":              now - 120,
			"user":               "jdoe@corp.internal",
			"host":               "corp-win-finance-02",
			"file_name":          "FY2026_Q3_Financial_Forecast_Confidential.xlsx",
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
			"event_id":           "DLP-EXFIL-002",
			"timestamp":          now - 95,
			"_time":              now - 95,
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
		{
			"event_id":           "DLP-EXFIL-003",
			"timestamp":          now - 60,
			"_time":              now - 60,
			"user":               "mrodriguez@corp.internal",
			"host":               "corp-win-hr-05",
			"file_name":          "customer_pii_credit_cards_2026.csv",
			"file_hash":          "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
			"bytes_out":          8940220,
			"channel":            "usb",
			"destination_domain": "removable_disk:E",
			"action":             "alert",
			"policy_name":        "PII_DATA_LOSS_PREVENTION",
			"severity":           "critical",
			"description":        "Customer PII and financial records copied to unencrypted removable USB drive",
		},
		{
			"event_id":           "DLP-EXFIL-004",
			"timestamp":          now - 30,
			"_time":              now - 30,
			"user":               "klee@corp.internal",
			"host":               "corp-win-sec-01",
			"file_name":          "executive_salary_records.pdf",
			"file_hash":          "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
			"bytes_out":          3201400,
			"channel":            "web_converter",
			"destination_domain": "convert-pdf-online-free.biz",
			"action":             "alert",
			"policy_name":        "HR_CONFIDENTIAL_CONVERTER",
			"severity":           "high",
			"description":        "HR compensation file submitted to untrusted external PDF conversion service",
		},
	}
}
