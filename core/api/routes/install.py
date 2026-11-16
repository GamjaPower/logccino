"""
Logccino One-Liner Remote Installer Router
curl -sSL http://<host>:8000/install | bash
또는 curl -sSL http://<host>:8000/install.py | python3
한 줄로 클라이언트 PC에 Claude MCP 및 스킬을 즉시 설치하는 엔드포인트
"""

from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["One-Click Installer"])

BASH_TEMPLATE = '''#!/bin/bash
set -e

echo "============================================================"
echo "☕ Logccino AI Agent (Claude) 원클릭 자동 설정 설치기"
echo "서버 엔드포인트: __SSE_URL__"
echo "============================================================"

# OS 감지 및 설정 경로 탐색
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
else
    CONFIG_DIR="$HOME/.config/Claude"
fi

CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
mkdir -p "$CONFIG_DIR"

echo "📂 Claude Desktop 설정 파일: $CONFIG_FILE"

# Python 스크립트로 안전한 JSON Merge 수행
python3 - << 'EOF'
import json
import os
from pathlib import Path

os_name = os.uname().sysname
if os_name == "Darwin":
    config_file = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
else:
    config_file = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

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

config["mcpServers"]["logccino"] = {
    "url": sse_url
}

with open(config_file, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("✅ Claude Desktop MCP 설정 등록 완료!")
EOF

# 스킬 및 커스텀 프롬프트 디렉토리 구성 (선택)
SKILLS_DIR="$HOME/.claude/skills/logccino"
mkdir -p "$SKILLS_DIR"
cat << 'EOF' > "$SKILLS_DIR/skill.json"
{
  "name": "logccino-bigdata-analyst",
  "description": "대규모 분산 OpenSearch 로그 및 실시간 스트림 분석 스킬",
  "endpoint": "__SSE_URL__"
}
EOF
echo "✅ Logccino Claude 스킬(Skill) 패키지 설치 완료: $SKILLS_DIR"

echo "============================================================"
echo "🎉 모든 설정이 성공적으로 완료되었습니다!"
echo "👉 지금 'Claude Desktop' 앱을 완전히 종료 후 다시 실행하세요."
echo "============================================================"
'''

PYTHON_TEMPLATE = '''# -*- coding: utf-8 -*-
import os
import sys
import json
import platform
from pathlib import Path

SSE_URL = "__SSE_URL__"

def get_claude_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

def main():
    print("=" * 60)
    print("☕ Logccino AI Agent (Claude) 원클릭 원격 자동 설정기")
    print(f"서버 엔드포인트: {SSE_URL}")
    print("=" * 60)

    config_path = get_claude_config_path()
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"기존 Claude 설정을 발견했습니다: {config_path}")
        except Exception:
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["logccino"] = {
        "url": SSE_URL
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 스킬(Skill) 저장
    skills_dir = Path.home() / ".claude" / "skills" / "logccino"
    skills_dir.mkdir(parents=True, exist_ok=True)
    with open(skills_dir / "skill.json", "w", encoding="utf-8") as f:
        json.dump({
            "name": "logccino-bigdata-analyst",
            "description": "Logccino 빅데이터 및 실시간 스트림 분석 스킬",
            "endpoint": SSE_URL
        }, f, indent=2)

    print("✅ Claude Desktop MCP 서버 등록 완료!")
    print(f"✅ Logccino 스킬(Skill) 패키지 설치 완료: {skills_dir}")
    print("=" * 60)
    print("🎉 모든 설정이 성공적으로 완료되었습니다!")
    print("👉 'Claude Desktop' 앱을 완전히 종료 후 다시 실행해 주세요.")
    print("=" * 60)

if __name__ == "__main__":
    main()
'''

POWERSHELL_TEMPLATE = '''$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "☕ Logccino AI Agent (Claude) 원클릭 원격 자동 설정기" -ForegroundColor Cyan
Write-Host "서버 엔드포인트: __SSE_URL__" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$configDir = "$env:APPDATA\\Claude"
$configFile = "$configDir\\claude_desktop_config.json"

if (!(Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

$config = @{ mcpServers = @{} }

if (Test-Path $configFile) {
    try {
        $content = Get-Content $configFile -Raw | ConvertFrom-Json
        if ($content.mcpServers) {
            $config = $content
        }
    } catch {
        Write-Host "기존 설정 파싱 실패, 새로 작성합니다." -ForegroundColor Yellow
    }
}

if ($null -eq $config.mcpServers) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{} -Force
}

$logccinoConfig = [PSCustomObject]@{
    url = "__SSE_URL__"
}

$config.mcpServers | Add-Member -MemberType NoteProperty -Name "logccino" -Value $logccinoConfig -Force
$config | ConvertTo-Json -Depth 10 | Set-Content $configFile -Encoding UTF8

Write-Host "✅ Claude Desktop MCP 서버 등록 완료: $configFile" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🎉 모든 설정이 성공적으로 완료되었습니다!" -ForegroundColor Green
Write-Host "👉 'Claude Desktop' 앱을 완전히 종료 후 다시 켜주세요." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
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

@router.get("/install.ps1")
async def get_powershell_installer(request: Request):
    sse_url = _get_sse_url(request)
    script = POWERSHELL_TEMPLATE.replace("__SSE_URL__", sse_url)
    return Response(content=script, media_type="text/plain")
