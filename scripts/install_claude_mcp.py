#!/usr/bin/env python3
"""
Logccino Claude Desktop One-Click MCP Installer
Claude Desktop 설정 파일(Windows/Mac/Linux)을 자동으로 감지하여 
Claude Desktop이 요구하는 표준 command & args 규격으로 Logccino MCP를 등록/병합합니다.
"""

import os
import sys
import json
import platform
import shutil
from pathlib import Path

def get_claude_config_path() -> Path:
    system = platform.system()
    if system == "Darwin": # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else: # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

def install(remote_sse_url: str = None):
    config_path = get_claude_config_path()
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    project_root = Path(__file__).resolve().parent.parent
    venv_python = project_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = Path(sys.executable)

    # 기존 설정 불러오기
    existing_config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                existing_config = json.load(f)
            print(f"기존 Claude 설정을 발견했습니다: {config_path}")
        except Exception as e:
            print(f"기존 설정 읽기 오류 (새로 생성합니다): {e}")

    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}

    skills_dir = Path.home() / ".claude" / "skills" / "logccino"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # 원격 SSE 지정 여부에 따른 command & args 설정
    if remote_sse_url:
        # 브릿지 스크립트 복사
        bridge_src = project_root / "core" / "mcp" / "bridge.py"
        bridge_dest = skills_dir / "bridge.py"
        shutil.copyfile(bridge_src, bridge_dest)

        existing_config["mcpServers"]["logccino"] = {
            "command": sys.executable,
            "args": [str(bridge_dest), remote_sse_url]
        }
        mode_desc = f"원격 SSE 브릿지 ({remote_sse_url})"
    else:
        # 로컬 직접 실행 (가장 안정적인 기본 모드)
        existing_config["mcpServers"]["logccino"] = {
            "command": str(venv_python),
            "args": ["-m", "core.mcp.server"],
            "cwd": str(project_root),
            "env": {
                "PYTHONPATH": str(project_root)
            }
        }
        mode_desc = f"로컬 Stdio ({venv_python})"

    # 스킬 메타데이터 저장
    with open(skills_dir / "skill.json", "w", encoding="utf-8") as f:
        json.dump({
            "name": "logccino-bigdata-analyst",
            "description": "Logccino 대규모 분산 OpenSearch 로그 및 실시간 스트림 분석 스킬"
        }, f, indent=2)

    # Claude Desktop 설정 파일 저장
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(existing_config, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("🎉 Logccino Claude MCP 설정이 유효한 규격으로 등록되었습니다!")
    print(f"📁 설정 파일 위치: {config_path}")
    print(f"⚙️ 실행 방식: {mode_desc}")
    print("=" * 60)
    print("\n👉 이제 'Claude Desktop' 앱을 완전히 종료 후 다시 실행해 주세요!\n")

if __name__ == "__main__":
    remote_arg = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else None
    install(remote_sse_url=remote_arg)
