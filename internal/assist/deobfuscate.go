package assist

import (
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"net/url"
	"regexp"
	"strings"
	"unicode/utf16"
)

var DangerousTokens = []string{
	"Invoke-WebRequest",
	"DownloadString",
	"DownloadFile",
	"WebClient",
	"ExecutionPolicy",
	"Bypass",
	"Start-Process",
	"Hidden",
	"IEX",
	"Invoke-Expression",
	"cmd.exe",
	"certutil",
	"bitsadmin",
}

var psEncodedRegex = regexp.MustCompile(`(?i)(?:-encodedcommand|-enc|-e)\s+([A-Za-z0-9+/=]+)`)
var hexRegex = regexp.MustCompile(`(?i)(?:0x[0-9a-f]{2}\s*)+`)

type DeobfuscateResult struct {
	OriginalText  string   `json:"original_text"`
	DecodedText   string   `json:"decoded_text"`
	LayersDecoded int      `json:"layers_decoded"`
	Highlights    []string `json:"highlights"`
	HasEncodedCmd bool     `json:"has_encoded_cmd"`
}

// Deobfuscate performs deterministic multi-layer decoding
func Deobfuscate(input string) *DeobfuscateResult {
	res := &DeobfuscateResult{
		OriginalText: input,
		DecodedText:  input,
	}

	current := input
	depth := 0
	maxDepth := 5

	for depth < maxDepth {
		modified := false

		// 1. PowerShell -EncodedCommand (UTF-16LE Base64)
		if m := psEncodedRegex.FindStringSubmatch(current); len(m) > 1 {
			res.HasEncodedCmd = true
			if decoded, ok := decodePSBase64(m[1]); ok {
				current = strings.Replace(current, m[0], fmt.Sprintf("\n[DECODED_POWERSHELL]\n%s\n[/DECODED_POWERSHELL]\n", decoded), 1)
				modified = true
				depth++
			}
		}

		// 2. URL decoding
		if unescaped, err := url.QueryUnescape(current); err == nil && unescaped != current && len(unescaped) < len(current) {
			current = unescaped
			modified = true
			depth++
		}

		// 3. Hex decoding (\x41 or 0x41)
		if strings.Contains(current, `\x`) {
			cleanHex := strings.ReplaceAll(current, `\x`, "")
			if b, err := hex.DecodeString(cleanHex); err == nil && isPrintable(b) {
				current = string(b)
				modified = true
				depth++
			}
		}

		if !modified {
			break
		}
	}

	res.DecodedText = current
	res.LayersDecoded = depth

	// 위험 토큰 하이라이트
	for _, tok := range DangerousTokens {
		if strings.Contains(strings.ToLower(current), strings.ToLower(tok)) {
			res.Highlights = append(res.Highlights, tok)
		}
	}

	return res
}

func decodePSBase64(b64Str string) (string, bool) {
	raw, err := base64.StdEncoding.DecodeString(b64Str)
	if err != nil || len(raw)%2 != 0 {
		return "", false
	}
	u16 := make([]uint16, len(raw)/2)
	for i := 0; i < len(u16); i++ {
		u16[i] = uint16(raw[i*2]) | (uint16(raw[i*2+1]) << 8)
	}
	decoded := string(utf16.Decode(u16))
	return decoded, true
}

func isPrintable(b []byte) bool {
	for _, c := range b {
		if (c < 32 && c != '\n' && c != '\r' && c != '\t') || c > 126 {
			return false
		}
	}
	return true
}
