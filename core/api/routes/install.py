"""
Logccino One-Liner Remote Installer Router
curl -sSL http://<host>:8000/install | bash
또는 curl -sSL http://<host>:8000/install.py | python3
Claude Desktop 공식 스키마(command + args)에 100% 호환되는 자동 설치기
"""

from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["One-Click Installer"])

BASH_TEMPLATE = r'''#!/bin/bash
set -e

echo "============================================================"
echo "☕ Logccino AI Agent (Claude) 원클릭 자동 설정 설치기"
echo "서버 엔드포인트: __SSE_URL__"
echo "============================================================"

# OS 감지 및 설정 디렉토리
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
else
    CONFIG_DIR="$HOME/.config/Claude"
fi

CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
mkdir -p "$CONFIG_DIR"

SKILLS_DIR="$HOME/.claude/skills/logccino"
mkdir -p "$SKILLS_DIR"

# 초경량 Stdio-to-SSE 브릿지 스크립트 작성
cat << 'EOFBRIDGE' > "$SKILLS_DIR/bridge.py"
import sys, json, urllib.request, urllib.error, threading
from urllib.parse import urljoin

def run_bridge(sse_url):
    req = urllib.request.Request(sse_url, headers={"Accept": "text/event-stream"})
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        sys.stderr.write(f"Logccino SSE connection error: {e}\n")
        sys.exit(1)

    post_endpoint = None

    def read_sse_stream():
        nonlocal post_endpoint
        event_type = "message"
        while True:
            line = response.readline()
            if not line: break
            line_str = line.decode("utf-8")
            if line_str.startswith("event:"):
                event_type = line_str[6:].strip()
            elif line_str.startswith("data:"):
                data_str = line_str[5:].strip()
                if event_type == "endpoint":
                    post_endpoint = urljoin(sse_url, data_str)
                elif event_type == "message":
                    sys.stdout.write(data_str + "\n")
                    sys.stdout.flush()
            elif line_str.strip() == "":
                event_type = "message"

    sse_thread = threading.Thread(target=read_sse_stream, daemon=True)
    sse_thread.start()

    for _ in range(50):
        if post_endpoint: break
        threading.Event().wait(0.1)

    if not post_endpoint:
        sys.stderr.write("Failed to receive endpoint from SSE server\n")
        sys.exit(1)

    while True:
        line = sys.stdin.readline()
        if not line: break
        line_clean = line.strip()
        if not line_clean: continue
        try:
            req_data = line_clean.encode("utf-8")
            post_req = urllib.request.Request(post_endpoint, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(post_req, timeout=30) as p_res:
                _ = p_res.read()
        except Exception as err:
            sys.stderr.write(f"POST error: {err}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    run_bridge(sys.argv[1])
EOFBRIDGE

# Python으로 설정 파일 안전하게 병합
python3 - "$CONFIG_FILE" "$SKILLS_DIR" << 'EOF'
import json, sys
from pathlib import Path

config_file = Path(sys.argv[1])
skills_dir = Path(sys.argv[2])
bridge_path = skills_dir / "bridge.py"
sse_url = "__SSE_URL__"

config = {}
if config_file.exists():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        config = {}

if "mcpServers" not in config:
    config["mcpServers"] = {}

# Claude Desktop 표준 command & args 규격
config["mcpServers"]["logccino"] = {
    "command": sys.executable,
    "args": [str(bridge_path), sse_url]
}

with open(config_file, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("✅ Claude Desktop 설정 완료 (" + str(config_file) + ")")
EOF

echo "============================================================"
echo "🎉 모든 설정이 성공적으로 완료되었습니다!"
echo "👉 지금 'Claude Desktop' 앱을 완전히 종료 후 다시 실행하세요."
echo "============================================================"
'''

PYTHON_TEMPLATE = r'''# -*- coding: utf-8 -*-
import os, sys, json, platform
from pathlib import Path

SSE_URL = "__SSE_URL__"

BRIDGE_CODE = ''' + repr(open(__file__.replace("install.py", "../mcp/bridge.py")).read() if False else '''import sys, json, urllib.request, urllib.error, threading
from urllib.parse import urljoin

def run_bridge(sse_url):
    req = urllib.request.Request(sse_url, headers={"Accept": "text/event-stream"})
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        sys.stderr.write(f"Logccino SSE connection error: {e}\n")
        sys.exit(1)

    post_endpoint = None

    def read_sse_stream():
        nonlocal post_endpoint
        event_type = "message"
        while True:
            line = response.readline()
            if not line: break
            line_str = line.decode("utf-8")
            if line_str.startswith("event:"):
                event_type = line_str[6:].strip()
            elif line_str.startswith("data:"):
                data_str = line_str[5:].strip()
                if event_type == "endpoint":
                    post_endpoint = urljoin(sse_url, data_str)
                elif event_type == "message":
                    sys.stdout.write(data_str + "\n")
                    sys.stdout.flush()
            elif line_str.strip() == "":
                event_type = "message"

    sse_thread = threading.Thread(target=read_sse_stream, daemon=True)
    sse_thread.start()

    for _ in range(50):
        if post_endpoint: break
        threading.Event().wait(0.1)

    if not post_endpoint:
        sys.stderr.write("Failed to receive endpoint from SSE server\n")
        sys.exit(1)

    while True:
        line = sys.stdin.readline()
        if not line: break
        line_clean = line.strip()
        if not line_clean: continue
        try:
            req_data = line_clean.encode("utf-8")
            post_req = urllib.request.Request(post_endpoint, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(post_req, timeout=30) as p_res:
                _ = p_res.read()
        except Exception as err:
            sys.stderr.write(f"POST error: {err}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    run_bridge(sys.argv[1])
''') + r'''

def get_claude_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata: return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

def main():
    config_path = get_claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    skills_dir = Path.home() / ".claude" / "skills" / "logccino"
    skills_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = skills_dir / "bridge.py"
    with open(bridge_path, "w", encoding="utf-8") as f:
        f.write(BRIDGE_CODE)

    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception: pass

    if "mcpServers" not in config: config["mcpServers"] = {}

    config["mcpServers"]["logccino"] = {
        "command": sys.executable,
        "args": [str(bridge_path), SSE_URL]
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("✅ Claude Desktop MCP 설정 등록 완료 (" + str(config_path) + ")")
    print("👉 'Claude Desktop' 앱을 완전히 종료 후 다시 실행해 주세요.")

if __name__ == "__main__":
    main()
'''

def _get_sse_url(request: Request) -> str:
    host = request.headers.get("host", "localhost:8000")
    proto = "https" if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https" else "http"
    return f"{proto}://{host}/sse"

@router.get("/install")
@router.get("/install.sh")
async def get_bash_installer(request: Request):
    sse_url = _get_sse_url(request)
    script = BASH_TEMPLATE.replace("__SSE_URL__", sse_url)
    return Response(content=script, media_type="text/x-shellscript")

@router.get("/install.py")
async def get_python_installer(request: Request):
    sse_url = _get_sse_url(request)
    script = PYTHON_TEMPLATE.replace("__SSE_URL__", sse_url)
    return Response(content=script, media_type="text/x-python")
