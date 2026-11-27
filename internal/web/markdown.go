package web

import (
	"html"
	"html/template"
	"regexp"
	"strings"
)

var (
	reBold      = regexp.MustCompile(`\*\*([^*]+)\*\*`)
	reCode      = regexp.MustCompile("`([^`]+)`")
	reCite      = regexp.MustCompile(`\[근거:\s*([^\]]+)\]`)
	reConfirmed = regexp.MustCompile(`\[확인\]`)
	reInferred  = regexp.MustCompile(`\[추정\]`)
	reUnchecked = regexp.MustCompile(`\[미확인\]`)
)

// RenderMarkdown converts a subset of Markdown (headings, hr, lists, tables,
// fenced code blocks, inline code, bold, and SOC citation/basis tags) into
// XSS-safe HTML. Raw text is HTML-escaped prior to any tag substitution.
func RenderMarkdown(src string) template.HTML {
	if strings.TrimSpace(src) == "" {
		return template.HTML(`<p class="text-muted">No analysis report available yet.</p>`)
	}

	lines := strings.Split(strings.ReplaceAll(src, "\r\n", "\n"), "\n")
	var out strings.Builder
	out.WriteString(`<div class="md-report">`)

	inList := false
	inCode := false
	var tableRows [][]string

	flushList := func() {
		if inList {
			out.WriteString("</ul>")
			inList = false
		}
	}

	flushTable := func() {
		if len(tableRows) == 0 {
			return
		}
		out.WriteString(`<div class="table-wrap"><table class="data-table md-table">`)
		for idx, cells := range tableRows {
			if idx == 1 && isSeparatorRow(cells) {
				continue
			}
			tag := "td"
			if idx == 0 {
				out.WriteString("<thead><tr>")
				tag = "th"
			} else {
				if idx == 1 || (idx == 2 && len(tableRows) > 1 && isSeparatorRow(tableRows[1])) {
					out.WriteString("<tbody>")
				}
				out.WriteString("<tr>")
			}
			for _, cell := range cells {
				out.WriteString("<" + tag + ">" + formatInline(strings.TrimSpace(cell)) + "</" + tag + ">")
			}
			out.WriteString("</tr>")
			if idx == 0 {
				out.WriteString("</thead>")
			}
		}
		if len(tableRows) > 1 {
			out.WriteString("</tbody>")
		}
		out.WriteString("</table></div>")
		tableRows = nil
	}

	for _, rawLine := range lines {
		trimmed := strings.TrimSpace(rawLine)

		// Fenced code blocks
		if strings.HasPrefix(trimmed, "```") {
			flushList()
			flushTable()
			if !inCode {
				out.WriteString(`<pre class="code-block"><code>`)
				inCode = true
			} else {
				out.WriteString(`</code></pre>`)
				inCode = false
			}
			continue
		}
		if inCode {
			out.WriteString(html.EscapeString(rawLine) + "\n")
			continue
		}

		// Markdown pipe table detection
		if strings.HasPrefix(trimmed, "|") && strings.HasSuffix(trimmed, "|") && len(trimmed) > 2 {
			flushList()
			inner := strings.TrimSuffix(strings.TrimPrefix(trimmed, "|"), "|")
			cells := splitTableCells(inner)
			tableRows = append(tableRows, cells)
			continue
		}
		flushTable()

		if trimmed == "" {
			flushList()
			continue
		}

		if trimmed == "---" || trimmed == "***" {
			flushList()
			out.WriteString(`<hr class="md-hr">`)
			continue
		}

		if strings.HasPrefix(trimmed, "### ") {
			flushList()
			out.WriteString("<h4>" + formatInline(strings.TrimPrefix(trimmed, "### ")) + "</h4>")
			continue
		}
		if strings.HasPrefix(trimmed, "## ") {
			flushList()
			out.WriteString("<h3>" + formatInline(strings.TrimPrefix(trimmed, "## ")) + "</h3>")
			continue
		}
		if strings.HasPrefix(trimmed, "# ") {
			flushList()
			out.WriteString("<h2>" + formatInline(strings.TrimPrefix(trimmed, "# ")) + "</h2>")
			continue
		}

		if strings.HasPrefix(trimmed, "- ") || strings.HasPrefix(trimmed, "* ") {
			if !inList {
				out.WriteString(`<ul class="md-list">`)
				inList = true
			}
			itemText := strings.TrimSpace(trimmed[2:])
			out.WriteString("<li>" + formatInline(itemText) + "</li>")
			continue
		}

		flushList()
		out.WriteString("<p>" + formatInline(trimmed) + "</p>")
	}

	if inCode {
		out.WriteString(`</code></pre>`)
	}
	flushList()
	flushTable()
	out.WriteString(`</div>`)
	return template.HTML(out.String())
}

func splitTableCells(inner string) []string {
	var cells []string
	var cur strings.Builder
	inBacktick := false
	for i := 0; i < len(inner); i++ {
		ch := inner[i]
		if ch == '`' {
			inBacktick = !inBacktick
			cur.WriteByte(ch)
			continue
		}
		if ch == '|' && !inBacktick {
			cells = append(cells, cur.String())
			cur.Reset()
			continue
		}
		cur.WriteByte(ch)
	}
	cells = append(cells, cur.String())
	return cells
}

func isSeparatorRow(cells []string) bool {
	if len(cells) == 0 {
		return false
	}
	for _, c := range cells {
		s := strings.TrimSpace(c)
		s = strings.ReplaceAll(s, "-", "")
		s = strings.ReplaceAll(s, ":", "")
		if s != "" {
			return false
		}
	}
	return true
}

func formatInline(raw string) string {
	// Escape raw user/LLM text first to prevent XSS.
	escaped := html.EscapeString(raw)

	// Highlight SOC evidence citations before generic inline code so `[근거: E1]` renders cleanly.
	escaped = reCite.ReplaceAllString(escaped, `<span class="cite-chip">근거: $1</span>`)
	escaped = reConfirmed.ReplaceAllString(escaped, `<span class="basis-tag tag-confirmed">확인</span>`)
	escaped = reInferred.ReplaceAllString(escaped, `<span class="basis-tag tag-inferred">추정</span>`)
	escaped = reUnchecked.ReplaceAllString(escaped, `<span class="basis-tag tag-unchecked">미확인</span>`)

	escaped = reBold.ReplaceAllString(escaped, `<strong>$1</strong>`)
	escaped = reCode.ReplaceAllString(escaped, `<code class="inline-code">$1</code>`)
	return escaped
}
