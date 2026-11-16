#!/usr/bin/env python3
"""
Logccino Claude Desktop One-Click MCP Installer
Claude Desktop 설정 파일(Windows/Mac/Linux)을 자동으로 감지하여 
Logccino MCP 설정을 한 방에 등록/병합합니다.
"""

import os
import sys
import json
import platform
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

def install(mode: str = "sse", sse_url: str = "http://localhost:8000/sse"):
    config_path = get_claude_config_path()
    config_dir = config_path.parent

    # 디렉토리 생성
    config_dir.mkdir(parents=True, exist_ok=True)

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

    # 모드에 따른 설정 생성
    project_root = Path(__file__).resolve().parent.parent
    venv_python = project_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = Path(sys.executable)

    if mode == "stdio":
        existing_config["mcpServers"]["logccino"] = {
            "command": str(venv_python),
            "args": ["-m", "core.mcp.server"],
            "cwd": str(project_root),
            "env": {
                "PYTHONPATH": str(project_root)
            }
        }
    else: # sse (default & recommended)
        existing_config["mcpServers"]["logccino"] = {
            "url": sse_url
        }

    # 파일 저장
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(existing_config, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("🎉 Logccino Claude MCP 연동 설정이 성공적으로 완료되었습니다!")
    print(f"📁 설정 파일 위치: {config_path}")
    print(f"🔗 연동 모드: {mode.upper()} ({sse_url if mode == 'sse' else str(venv_python)})")
    print("=" * 60)
    print("\n👉 이제 'Claude Desktop' 앱을 완전히 종료 후 다시 켜면 바로 사용하실 수 있습니다!\n")

if __name__ == "__main__":
    mode_arg = "sse"
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["stdio", "local"]:
        mode_arg = "stdio"
    install(mode=mode_arg)
