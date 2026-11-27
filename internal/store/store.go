package store

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

type Store struct {
	db *sql.DB
	mu sync.RWMutex
}

func New(dbPath string) (*Store, error) {
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create db directory: %w", err)
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open sqlite db: %w", err)
	}

	// 동시 접근 및 저널링 모드 설정 (WAL)
	if _, err := db.Exec(`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`); err != nil {
		return nil, fmt.Errorf("failed to set pragma: %w", err)
	}

	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		return nil, fmt.Errorf("failed to migrate db: %w", err)
	}
	return s, nil
}

func (s *Store) DB() *sql.DB {
	return s.db
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) Ping() error {
	return s.db.Ping()
}

func (s *Store) migrate() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	queries := []string{
		`CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			username TEXT UNIQUE NOT NULL,
			password_hash TEXT NOT NULL,
			role TEXT NOT NULL DEFAULT 'analyst',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS tickets (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			alert_id TEXT UNIQUE NOT NULL,
			rule_id TEXT NOT NULL,
			rule_name TEXT NOT NULL,
			severity TEXT NOT NULL,
			entity_type TEXT NOT NULL,
			entity_value TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'new',
			verdict TEXT DEFAULT '',
			confidence REAL DEFAULT 0.0,
			agent_report TEXT DEFAULT '',
			human_notes TEXT DEFAULT '',
			approved_by TEXT DEFAULT '',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS evidence (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			ticket_id INTEGER NOT NULL,
			evidence_id TEXT NOT NULL,
			spl_query TEXT NOT NULL,
			time_range TEXT NOT NULL,
			status TEXT NOT NULL,
			row_count INTEGER NOT NULL,
			summary_json TEXT NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
		);`,
		`CREATE TABLE IF NOT EXISTS deployments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			deployment_id TEXT UNIQUE NOT NULL,
			commit_hash TEXT NOT NULL,
			rules_count INTEGER NOT NULL,
			status TEXT NOT NULL,
			backup_json TEXT NOT NULL,
			logs TEXT DEFAULT '',
			deployed_by TEXT NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS drift_logs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			rule_id TEXT NOT NULL,
			search_name TEXT NOT NULL,
			drift_type TEXT NOT NULL,
			expected_spl TEXT NOT NULL,
			actual_spl TEXT NOT NULL,
			resolved BOOLEAN DEFAULT FALSE,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS action_logs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			ticket_id INTEGER NOT NULL,
			action_type TEXT NOT NULL,
			target TEXT NOT NULL,
			approved_by TEXT NOT NULL,
			executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			status TEXT NOT NULL DEFAULT 'success',
			details TEXT DEFAULT ''
		);`,
		`CREATE TABLE IF NOT EXISTS llm_capabilities (
			model_name TEXT PRIMARY KEY,
			api_type TEXT NOT NULL,
			supports_tools BOOLEAN NOT NULL,
			supports_json_schema BOOLEAN NOT NULL,
			checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS llm_calls (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			ticket_id INTEGER DEFAULT 0,
			role_name TEXT NOT NULL,
			model_name TEXT NOT NULL,
			api_used TEXT NOT NULL,
			prompt_version TEXT NOT NULL,
			input_hash TEXT NOT NULL,
			input_redacted_fields TEXT NOT NULL,
			tokens_prompt INTEGER DEFAULT 0,
			tokens_completion INTEGER DEFAULT 0,
			latency_ms INTEGER DEFAULT 0,
			retries INTEGER DEFAULT 0,
			status TEXT NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS eval_runs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id TEXT UNIQUE NOT NULL,
			model_name TEXT NOT NULL,
			prompt_version TEXT NOT NULL,
			total_samples INTEGER NOT NULL,
			accuracy REAL NOT NULL,
			confusion_matrix_json TEXT NOT NULL,
			total_tokens INTEGER NOT NULL,
			avg_latency_ms INTEGER NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE TABLE IF NOT EXISTS change_requests (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			request_id TEXT UNIQUE NOT NULL,
			rule_id TEXT NOT NULL,
			rule_name TEXT NOT NULL,
			diff_content TEXT NOT NULL,
			ai_review_comments_json TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'open',
			author TEXT NOT NULL,
			reviewed_by TEXT DEFAULT '',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
	}

	for _, q := range queries {
		if _, err := s.db.Exec(q); err != nil {
			return fmt.Errorf("migration query error: %s: %w", q, err)
		}
	}
	return nil
}

func (s *Store) RecordLLMCall(ticketID int, roleName, modelName, apiUsed, promptVer, inputHash, fields string, pTokens, cTokens, latency, retries int, status string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	_, err := s.db.Exec(`
		INSERT INTO llm_calls (ticket_id, role_name, model_name, api_used, prompt_version, input_hash, input_redacted_fields, tokens_prompt, tokens_completion, latency_ms, retries, status, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, ticketID, roleName, modelName, apiUsed, promptVer, inputHash, fields, pTokens, cTokens, latency, retries, status, time.Now())
	return err
}
