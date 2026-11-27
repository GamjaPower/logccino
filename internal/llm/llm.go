package llm

import (
	"context"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/openai/openai-go/shared"
)

type Message struct {
	Role       string     `json:"role"` // system, user, assistant, tool
	Content    string     `json:"content"`
	ToolCallID string     `json:"tool_call_id,omitempty"`
	ToolCalls  []ToolCall `json:"tool_calls,omitempty"`
}

type ToolCall struct {
	ID       string `json:"id"`
	Type     string `json:"type"` // "function"
	Function struct {
		Name      string `json:"name"`
		Arguments string `json:"arguments"`
	} `json:"function"`
}

type Tool struct {
	Type     string       `json:"type"` // "function"
	Function FunctionSpec `json:"function"`
}

type FunctionSpec struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Parameters  map[string]any `json:"parameters"`
}

type JSONSchema struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Strict      bool           `json:"strict,omitempty"`
	Schema      map[string]any `json:"schema"`
}

type Response struct {
	Content      string     `json:"content"`
	ToolCalls    []ToolCall `json:"tool_calls,omitempty"`
	Refusal      string     `json:"refusal,omitempty"`
	FinishReason string     `json:"finish_reason"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type Capability struct {
	ModelName          string `json:"model_name"`
	APIType            string `json:"api_type"`
	SupportsTools      bool   `json:"supports_tools"`
	SupportsJSONSchema bool   `json:"supports_json_schema"`
	Status             string `json:"status"` // ok, key_missing, key_invalid, model_not_found, unreachable
}

type Client interface {
	Chat(ctx context.Context, messages []Message, tools []Tool, schema *JSONSchema) (Response, Usage, error)
	CheckCapability(ctx context.Context, model string) (Capability, error)
	WithModel(model string) Client
	GetModel() string
}

// ----------------------------------------------------------------------------
// OpenAIClient Implementation
// ----------------------------------------------------------------------------
type OpenAIClient struct {
	client       openai.Client
	defaultModel string
	baseURL      string
	apiKey       string
}

func NewOpenAIClient(apiKey, baseURL, defaultModel, httpsProxy string) (*OpenAIClient, error) {
	var opts []option.RequestOption
	if apiKey != "" {
		opts = append(opts, option.WithAPIKey(apiKey))
	}
	if baseURL != "" {
		opts = append(opts, option.WithBaseURL(baseURL))
	}
	if httpsProxy != "" {
		if proxyURL, err := url.Parse(httpsProxy); err == nil {
			tr := &http.Transport{Proxy: http.ProxyURL(proxyURL)}
			httpClient := &http.Client{Transport: tr, Timeout: 60 * time.Second}
			opts = append(opts, option.WithHTTPClient(httpClient))
		}
	}

	cli := openai.NewClient(opts...)
	return &OpenAIClient{
		client:       cli,
		defaultModel: defaultModel,
		baseURL:      baseURL,
		apiKey:       apiKey,
	}, nil
}

func (c *OpenAIClient) CheckCapability(ctx context.Context, model string) (Capability, error) {
	if model == "" {
		model = c.defaultModel
	}
	cap := Capability{
		ModelName: model,
		APIType:   "chat_completions",
	}

	if c.apiKey == "" {
		cap.Status = "key_missing"
		return cap, nil
	}

	// GET /v1/models/{model} 확인
	_, err := c.client.Models.Get(ctx, model)
	if err != nil {
		errStr := err.Error()
		if strings.Contains(errStr, "401") || strings.Contains(errStr, "Incorrect API key") {
			cap.Status = "key_invalid"
		} else if strings.Contains(errStr, "404") || strings.Contains(errStr, "model_not_found") {
			cap.Status = "model_not_found"
		} else {
			cap.Status = "unreachable"
		}
		return cap, err
	}

	cap.Status = "ok"
	cap.SupportsTools = true
	cap.SupportsJSONSchema = true
	return cap, nil
}

func (c *OpenAIClient) Chat(ctx context.Context, messages []Message, tools []Tool, schema *JSONSchema) (Response, Usage, error) {
	var chatMsgs []openai.ChatCompletionMessageParamUnion
	for _, m := range messages {
		switch m.Role {
		case "system":
			chatMsgs = append(chatMsgs, openai.SystemMessage(m.Content))
		case "user":
			chatMsgs = append(chatMsgs, openai.UserMessage(m.Content))
		case "assistant":
			if len(m.ToolCalls) > 0 {
				var tcParams []openai.ChatCompletionMessageToolCallParam
				for _, tc := range m.ToolCalls {
					tcParams = append(tcParams, openai.ChatCompletionMessageToolCallParam{
						ID:   tc.ID,
						Type: "function",
						Function: openai.ChatCompletionMessageToolCallFunctionParam{
							Name:      tc.Function.Name,
							Arguments: tc.Function.Arguments,
						},
					})
				}
				chatMsgs = append(chatMsgs, openai.ChatCompletionMessageParamUnion{
					OfAssistant: &openai.ChatCompletionAssistantMessageParam{
						Content: openai.ChatCompletionAssistantMessageParamContentUnion{
							OfString: openai.String(m.Content),
						},
						ToolCalls: tcParams,
					},
				})
			} else {
				chatMsgs = append(chatMsgs, openai.AssistantMessage(m.Content))
			}
		case "tool":
			chatMsgs = append(chatMsgs, openai.ToolMessage(m.ToolCallID, m.Content))
		}
	}

	params := openai.ChatCompletionNewParams{
		Model:           openai.ChatModel(c.defaultModel),
		Messages:        chatMsgs,
		ReasoningEffort: shared.ReasoningEffort("none"),
	}

	if len(tools) > 0 {
		var toolParams []openai.ChatCompletionToolParam
		for _, t := range tools {
			toolParams = append(toolParams, openai.ChatCompletionToolParam{
				Type: "function",
				Function: openai.FunctionDefinitionParam{
					Name:        t.Function.Name,
					Description: openai.String(t.Function.Description),
					Parameters:  t.Function.Parameters,
				},
			})
		}
		params.Tools = toolParams
	}

	if schema != nil {
		params.ResponseFormat = openai.ChatCompletionNewParamsResponseFormatUnion{
			OfJSONSchema: &shared.ResponseFormatJSONSchemaParam{
				JSONSchema: shared.ResponseFormatJSONSchemaJSONSchemaParam{
					Name:        schema.Name,
					Description: openai.String(schema.Description),
					Strict:      openai.Bool(schema.Strict),
					Schema:      schema.Schema,
				},
			},
		}
	}

	resp, err := c.client.Chat.Completions.New(ctx, params)
	if err != nil {
		return Response{}, Usage{}, err
	}

	var out Response
	if len(resp.Choices) > 0 {
		choice := resp.Choices[0]
		out.Content = choice.Message.Content
		out.Refusal = choice.Message.Refusal
		out.FinishReason = string(choice.FinishReason)

		for _, tc := range choice.Message.ToolCalls {
			out.ToolCalls = append(out.ToolCalls, ToolCall{
				ID:   tc.ID,
				Type: string(tc.Type),
				Function: struct {
					Name      string `json:"name"`
					Arguments string `json:"arguments"`
				}{
					Name:      tc.Function.Name,
					Arguments: tc.Function.Arguments,
				},
			})
		}
	}

	var usage Usage
	if resp.Usage.PromptTokens > 0 || resp.Usage.CompletionTokens > 0 {
		usage.PromptTokens = int(resp.Usage.PromptTokens)
		usage.CompletionTokens = int(resp.Usage.CompletionTokens)
		usage.TotalTokens = int(resp.Usage.TotalTokens)
	}

	return out, usage, nil
}

func (c *OpenAIClient) WithModel(model string) Client {
	if model == "" {
		return c
	}
	return &OpenAIClient{
		client:       c.client,
		defaultModel: model,
		baseURL:      c.baseURL,
		apiKey:       c.apiKey,
	}
}

func (c *OpenAIClient) GetModel() string {
	return c.defaultModel
}

// ----------------------------------------------------------------------------
// MockClient Implementation (Deterministic for Testing)
// ----------------------------------------------------------------------------
type MockClient struct {
	Responses   []Response
	Index       int
	CustomReply func(messages []Message) (Response, Usage, error)
}

func NewMockClient() *MockClient {
	return &MockClient{}
}

func (m *MockClient) CheckCapability(ctx context.Context, model string) (Capability, error) {
	return Capability{
		ModelName:          model,
		APIType:            "mock",
		SupportsTools:      true,
		SupportsJSONSchema: true,
		Status:             "ok",
	}, nil
}

func (m *MockClient) Chat(ctx context.Context, messages []Message, tools []Tool, schema *JSONSchema) (Response, Usage, error) {
	if m.CustomReply != nil {
		return m.CustomReply(messages)
	}
	if len(m.Responses) > 0 {
		if m.Index >= len(m.Responses) {
			m.Index = 0
		}
		r := m.Responses[m.Index]
		m.Index++
		return r, Usage{PromptTokens: 100, CompletionTokens: 50, TotalTokens: 150}, nil
	}

	// Default fallback JSON for triage verdict
	defaultJSON := `{
		"verdict": "true_positive",
		"confidence": 0.95,
		"summary_claims": [
			{"claim": "Multiple sensitive paths probed by scanner", "evidence_ids": ["E1"], "basis": "confirmed"}
		],
		"unchecked_items": [],
		"proposed_actions": ["block_ip"],
		"tuning_suggestion": ""
	}`
	return Response{
		Content:      defaultJSON,
		FinishReason: "stop",
	}, Usage{PromptTokens: 50, CompletionTokens: 50, TotalTokens: 100}, nil
}

func (m *MockClient) WithModel(model string) Client {
	return m
}

func (m *MockClient) GetModel() string {
	return "mock"
}
