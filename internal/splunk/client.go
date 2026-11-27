package splunk

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type Client struct {
	BaseURL    string
	HECURL     string
	Username   string
	Password   string
	HECToken   string
	SessionKey string
	HTTPClient *http.Client
}

type Config struct {
	BaseURL            string
	HECURL             string
	Username           string
	Password           string
	HECToken           string
	InsecureSkipVerify bool
	Timeout            time.Duration
}

func NewClient(cfg Config) *Client {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: cfg.InsecureSkipVerify,
		},
	}
	timeout := cfg.Timeout
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &Client{
		BaseURL:  strings.TrimRight(cfg.BaseURL, "/"),
		HECURL:   strings.TrimRight(cfg.HECURL, "/"),
		Username: cfg.Username,
		Password: cfg.Password,
		HECToken: cfg.HECToken,
		HTTPClient: &http.Client{
			Transport: tr,
			Timeout:   timeout,
		},
	}
}

// Login obtains a session key via /services/auth/login
func (c *Client) Login(ctx context.Context) error {
	loginURL := fmt.Sprintf("%s/services/auth/login", c.BaseURL)
	data := url.Values{}
	data.Set("username", c.Username)
	data.Set("password", c.Password)
	data.Set("output_mode", "json")

	req, err := http.NewRequestWithContext(ctx, "POST", loginURL, strings.NewReader(data.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("login request failed: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return fmt.Errorf("login failed with status %d: %s", resp.StatusCode, string(body))
	}

	var jsonRes struct {
		SessionKey string `json:"sessionKey"`
	}
	if err := json.Unmarshal(body, &jsonRes); err == nil && jsonRes.SessionKey != "" {
		c.SessionKey = jsonRes.SessionKey
		return nil
	}

	// XML fallback
	var xmlRes struct {
		XMLName    xml.Name `xml:"response"`
		SessionKey string   `xml:"sessionKey"`
	}
	if err := xml.Unmarshal(body, &xmlRes); err == nil && xmlRes.SessionKey != "" {
		c.SessionKey = xmlRes.SessionKey
		return nil
	}

	return fmt.Errorf("could not extract session key from response: %s", string(body))
}

func (c *Client) applyAuth(req *http.Request) {
	if c.SessionKey != "" {
		req.Header.Set("Authorization", "Splunk "+c.SessionKey)
	} else if c.Username != "" {
		req.SetBasicAuth(c.Username, c.Password)
	}
}

// CheckHealth queries /services/server/info
func (c *Client) CheckHealth(ctx context.Context) (map[string]any, error) {
	u := fmt.Sprintf("%s/services/server/info?output_mode=json", c.BaseURL)
	req, err := http.NewRequestWithContext(ctx, "GET", u, nil)
	if err != nil {
		return nil, err
	}
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("server info error %d: %s", resp.StatusCode, string(body))
	}

	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

// Export runs an export search and returns parsed JSON event rows
func (c *Client) Export(ctx context.Context, spl, earliest, latest string, maxRows int) ([]map[string]any, error) {
	if !strings.HasPrefix(strings.TrimSpace(spl), "search ") && !strings.HasPrefix(strings.TrimSpace(spl), "|") {
		spl = "search " + spl
	}

	u := fmt.Sprintf("%s/services/search/v2/jobs/export", c.BaseURL)
	data := url.Values{}
	data.Set("search", spl)
	data.Set("output_mode", "json")
	if earliest != "" {
		data.Set("earliest_time", earliest)
	}
	if latest != "" {
		data.Set("latest_time", latest)
	}
	if maxRows > 0 {
		data.Set("max_count", strconv.Itoa(maxRows))
	}

	req, err := http.NewRequestWithContext(ctx, "POST", u, strings.NewReader(data.Encode()))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("export error status %d: %s", resp.StatusCode, string(b))
	}

	var rows []map[string]any
	dec := json.NewDecoder(resp.Body)
	for dec.More() {
		var row map[string]any
		if err := dec.Decode(&row); err != nil {
			break
		}
		if result, ok := row["result"].(map[string]any); ok {
			rows = append(rows, result)
		} else if _, isPreview := row["preview"]; !isPreview {
			rows = append(rows, row)
		}
		if maxRows > 0 && len(rows) >= maxRows {
			break
		}
	}
	return rows, nil
}

// ParseSPL checks syntax using POST /services/search/parser
func (c *Client) ParseSPL(ctx context.Context, spl string) (bool, string, error) {
	if !strings.HasPrefix(strings.TrimSpace(spl), "search ") && !strings.HasPrefix(strings.TrimSpace(spl), "|") {
		spl = "search " + spl
	}

	u := fmt.Sprintf("%s/services/search/parser", c.BaseURL)
	data := url.Values{}
	data.Set("q", spl)
	data.Set("output_mode", "json")

	req, err := http.NewRequestWithContext(ctx, "POST", u, strings.NewReader(data.Encode()))
	if err != nil {
		return false, "", err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return false, "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode == 200 {
		return true, string(body), nil
	}
	return false, string(body), nil
}

// CreateUser creates a user idempotently via /services/authentication/users
func (c *Client) CreateUser(ctx context.Context, username, password string, roles []string) error {
	u := fmt.Sprintf("%s/services/authentication/users", c.BaseURL)
	data := url.Values{}
	data.Set("name", username)
	data.Set("password", password)
	for _, r := range roles {
		data.Add("roles", r)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", u, strings.NewReader(data.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == 201 || resp.StatusCode == 200 {
		return nil
	}
	body, _ := io.ReadAll(resp.Body)
	if strings.Contains(string(body), "already exists") {
		return nil // idempotent
	}
	return fmt.Errorf("create user status %d: %s", resp.StatusCode, string(body))
}

type SavedSearchParam struct {
	Name        string
	Search      string
	Cron        string
	Earliest    string
	Latest      string
	IsScheduled bool
	Description string
	Actions     map[string]string
}

// CreateSavedSearch creates a saved search in /servicesNS/nobody/{app}/saved/searches
func (c *Client) CreateSavedSearch(ctx context.Context, app string, p SavedSearchParam) error {
	u := fmt.Sprintf("%s/servicesNS/nobody/%s/saved/searches", c.BaseURL, app)
	data := url.Values{}
	data.Set("name", p.Name)
	data.Set("search", p.Search)
	data.Set("description", p.Description)
	if p.Cron != "" {
		data.Set("cron_schedule", p.Cron)
		data.Set("is_scheduled", "1")
	}
	if p.Earliest != "" {
		data.Set("dispatch.earliest_time", p.Earliest)
	}
	if p.Latest != "" {
		data.Set("dispatch.latest_time", p.Latest)
	}
	for k, v := range p.Actions {
		data.Set(k, v)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", u, strings.NewReader(data.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == 201 || resp.StatusCode == 200 {
		return nil
	}
	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("create saved search failed with %d: %s", resp.StatusCode, string(body))
}

// ListSavedSearches lists saved searches in the given app
func (c *Client) ListSavedSearches(ctx context.Context, app string) ([]map[string]any, error) {
	u := fmt.Sprintf("%s/servicesNS/nobody/%s/saved/searches?output_mode=json&count=0", c.BaseURL, app)
	req, err := http.NewRequestWithContext(ctx, "GET", u, nil)
	if err != nil {
		return nil, err
	}
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("list saved search status %d: %s", resp.StatusCode, string(body))
	}

	var res struct {
		Entry []map[string]any `json:"entry"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return nil, err
	}
	return res.Entry, nil
}

// DeleteSavedSearch deletes a saved search
func (c *Client) DeleteSavedSearch(ctx context.Context, app, name string) error {
	u := fmt.Sprintf("%s/servicesNS/nobody/%s/saved/searches/%s", c.BaseURL, app, url.PathEscape(name))
	req, err := http.NewRequestWithContext(ctx, "DELETE", u, nil)
	if err != nil {
		return err
	}
	c.applyAuth(req)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 || resp.StatusCode == 204 || resp.StatusCode == 404 {
		return nil
	}
	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("delete saved search failed with %d: %s", resp.StatusCode, string(body))
}

type HECEvent struct {
	Time       int64          `json:"time,omitempty"`
	Host       string         `json:"host,omitempty"`
	Source     string         `json:"source,omitempty"`
	Sourcetype string         `json:"sourcetype,omitempty"`
	Index      string         `json:"index,omitempty"`
	Event      map[string]any `json:"event"`
}

// EnableHEC configures global HEC and creates a token input idempotently
func (c *Client) EnableHEC(ctx context.Context, token string, indexes []string) error {
	// Enable global HTTP
	u := fmt.Sprintf("%s/servicesNS/nobody/siem_agent/data/inputs/http/http", c.BaseURL)
	d1 := url.Values{}
	d1.Set("disabled", "0")
	d1.Set("enableSSL", "1")
	d1.Set("port", "8088")
	d1.Set("output_mode", "json")
	req, _ := http.NewRequestWithContext(ctx, "POST", u, strings.NewReader(d1.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	c.applyAuth(req)
	_, _ = c.HTTPClient.Do(req)

	// Create HEC token input
	u2 := fmt.Sprintf("%s/servicesNS/nobody/siem_agent/data/inputs/http", c.BaseURL)
	d2 := url.Values{}
	d2.Set("name", "siem_agent_hec")
	d2.Set("token", token)
	d2.Set("index", "soc_alerts")
	d2.Set("indexes", strings.Join(indexes, ","))
	d2.Set("disabled", "0")
	d2.Set("output_mode", "json")
	req2, _ := http.NewRequestWithContext(ctx, "POST", u2, strings.NewReader(d2.Encode()))
	req2.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	c.applyAuth(req2)
	resp2, err := c.HTTPClient.Do(req2)
	if err != nil {
		return err
	}
	defer resp2.Body.Close()
	return nil
}

// SendHEC batches and sends events to Splunk HTTP Event Collector
func (c *Client) SendHEC(ctx context.Context, events []HECEvent) error {
	u := fmt.Sprintf("%s/services/collector/event", c.HECURL)
	var buf bytes.Buffer
	for _, ev := range events {
		data, err := json.Marshal(ev)
		if err != nil {
			return err
		}
		buf.Write(data)
		buf.WriteByte('\n')
	}

	req, err := http.NewRequestWithContext(ctx, "POST", u, &buf)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Splunk "+c.HECToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("send HEC request error: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HEC failed with status %d: %s", resp.StatusCode, string(b))
	}
	return nil
}
