package config

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

type Config struct {
	SplunkImage              string
	SplunkPassword           string
	SplunkWebPort            string
	SplunkMgmtPort           string
	SplunkHECPort            string
	SplunkS2SPort            string
	SplunkHECToken           string
	SplunkMgmtURL            string
	SplunkHECURL             string
	SplunkCAFile             string
	SplunkInsecureSkipVerify bool

	SplunkROUser         string
	SplunkROPassword     string
	SplunkDeployUser     string
	SplunkDeployPassword string

	AppListenAddr    string
	AppAdminUser     string
	AppAdminPassword string
	AppSessionKey    string

	SQLitePath    string
	RulesRepoPath string

	DefaultModel          string
	OpenAIAPIKey          string
	OpenAIBaseURL         string
	LLMProvider           string
	LLMJudgeModel         string
	LLMRebuttalModel      string
	LLMRulemakerModel     string
	LLMAssistModel        string
	LLMRedactFields       []string
	LLMMaxConcurrency     int
	LLMMaxRetries         int
	LLMMaxTokensPerTicket int
	LLMDailyTokenLimit    int

	HTTPSProxy string
	NoProxy    string

	TriageMaxToolCalls     int
	RulemakerMaxIterations int
}

func Load(envPath string) (*Config, error) {
	// 1. .env 파일이 존재하면 파싱하여 비어있는 환경변수 채우기 (이미 존재하는 환경변수 우선)
	if envPath == "" {
		envPath = ".env"
	}
	loadEnvFile(envPath)

	cfg := &Config{
		SplunkImage:              getEnv("SPLUNK_IMAGE", "splunk/splunk:latest"),
		SplunkPassword:           getEnv("SPLUNK_PASSWORD", ""),
		SplunkWebPort:            getEnv("SPLUNK_WEB_PORT", "8000"),
		SplunkMgmtPort:           getEnv("SPLUNK_MGMT_PORT", "8089"),
		SplunkHECPort:            getEnv("SPLUNK_HEC_PORT", "8088"),
		SplunkS2SPort:            getEnv("SPLUNK_S2S_PORT", "9997"),
		SplunkHECToken:           getEnv("SPLUNK_HEC_TOKEN", ""),
		SplunkMgmtURL:            getEnv("SPLUNK_MGMT_URL", "https://localhost:8089"),
		SplunkHECURL:             getEnv("SPLUNK_HEC_URL", "https://localhost:8088"),
		SplunkCAFile:             getEnv("SPLUNK_CA_FILE", ""),
		SplunkInsecureSkipVerify: getEnv("SPLUNK_INSECURE_SKIP_VERIFY", "true") == "true",

		SplunkROUser:         getEnv("SPLUNK_RO_USER", "siem_agent_ro"),
		SplunkROPassword:     getEnv("SPLUNK_RO_PASSWORD", getEnv("SPLUNK_PASSWORD", "")),
		SplunkDeployUser:     getEnv("SPLUNK_DEPLOY_USER", "dac_deployer"),
		SplunkDeployPassword: getEnv("SPLUNK_DEPLOY_PASSWORD", getEnv("SPLUNK_PASSWORD", "")),

		AppListenAddr:    getEnv("APP_LISTEN_ADDR", ":5090"),
		AppAdminUser:     getEnv("APP_ADMIN_USER", "admin"),
		AppAdminPassword: getEnv("APP_ADMIN_PASSWORD", "admin123456!"),
		AppSessionKey:    getEnv("APP_SESSION_KEY", "super-secret-session-key-32chars!!"),

		SQLitePath:    getEnv("SQLITE_PATH", "./data/siem_agent.db"),
		RulesRepoPath: getEnv("RULES_REPO_PATH", "./rules"),

		DefaultModel:      getEnv("DEFAULT_MODEL", "gpt-4o-mini"),
		OpenAIAPIKey:      getEnv("OPENAI_API_KEY", ""),
		OpenAIBaseURL:     getEnv("OPENAI_BASE_URL", ""),
		LLMProvider:       getEnv("LLM_PROVIDER", "openai"),
		LLMJudgeModel:     getEnv("LLM_JUDGE_MODEL", ""),
		LLMRebuttalModel:  getEnv("LLM_REBUTTAL_MODEL", ""),
		LLMRulemakerModel: getEnv("LLM_RULEMAKER_MODEL", ""),
		LLMAssistModel:    getEnv("LLM_ASSIST_MODEL", ""),

		LLMMaxConcurrency:     4,
		LLMMaxRetries:         4,
		LLMMaxTokensPerTicket: 60000,
		LLMDailyTokenLimit:    5000000,

		HTTPSProxy: getEnv("HTTPS_PROXY", ""),
		NoProxy:    getEnv("NO_PROXY", "splunk,localhost,127.0.0.1"),

		TriageMaxToolCalls:     10,
		RulemakerMaxIterations: 3,
	}

	redactFields := getEnv("LLM_REDACT_FIELDS", "user,src_user,email,dest_host,src_host")
	for _, f := range strings.Split(redactFields, ",") {
		f = strings.TrimSpace(f)
		if f != "" {
			cfg.LLMRedactFields = append(cfg.LLMRedactFields, f)
		}
	}

	return cfg, nil
}

func (c *Config) Validate() []string {
	var missing []string
	if c.SplunkPassword == "" {
		missing = append(missing, "SPLUNK_PASSWORD")
	}
	if c.SplunkHECToken == "" {
		missing = append(missing, "SPLUNK_HEC_TOKEN")
	}
	if c.LLMProvider == "openai" && c.OpenAIAPIKey == "" {
		missing = append(missing, "OPENAI_API_KEY")
	}
	return missing
}

func MaskSecret(s string) string {
	if s == "" {
		return "(not set)"
	}
	if len(s) <= 4 {
		return "****"
	}
	return strings.Repeat("*", len(s)-4) + s[len(s)-4:]
}

func getEnv(key, defaultVal string) string {
	if val, ok := os.LookupEnv(key); ok && val != "" {
		return val
	}
	return defaultVal
}

func loadEnvFile(path string) {
	file, err := os.Open(path)
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			k := strings.TrimSpace(parts[0])
			v := strings.TrimSpace(parts[1])
			v = strings.Trim(v, `"'`)
			// 시스템 환경변수에 없는 경우만 설정
			if _, exists := os.LookupEnv(k); !exists {
				_ = os.Setenv(k, v)
			}
		}
	}
}

func (c *Config) PrintSummary() {
	fmt.Printf("[Config] Splunk URL: %s (User: %s, VerifyTLS: %v)\n", c.SplunkMgmtURL, c.SplunkROUser, !c.SplunkInsecureSkipVerify)
	fmt.Printf("[Config] Listen Addr: %s\n", c.AppListenAddr)
	fmt.Printf("[Config] LLM Provider: %s (Default Model: %s, API Key: %s)\n", c.LLMProvider, c.DefaultModel, MaskSecret(c.OpenAIAPIKey))
	fmt.Printf("[Config] SQLite DB: %s\n", c.SQLitePath)
}
