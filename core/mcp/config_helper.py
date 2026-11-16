"""
Logccino MCP Configuration Helper
Claude Desktop, Antigravity, Cursor 등 외부 AI 에이전트 설정 파일에 바로 붙여넣을 수 있는
MCP 설정 JSON 스니펫을 생성합니다.
"""

import os
import sys
from typing import Dict, Any

def get_python_executable() -> str:
    return sys.executable

def get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def generate_claude_desktop_config() -> Dict[str, Any]:
    """Claude Desktop config (~/.config/Claude/claude_desktop_config.json) 형식 (로컬 Stdio 방식)"""
    root = get_project_root()
    return {
        "mcpServers": {
            "logccino": {
                "command": get_python_executable(),
                "args": ["-m", "core.mcp.server"],
                "cwd": root,
                "env": {
                    "PYTHONPATH": root
                }
            }
        }
    }

def generate_remote_claude_config(endpoint_url: str = "http://localhost:8000/sse") -> Dict[str, Any]:
    """AWS Marketplace 또는 사내 K8s 클러스터 배포 시 Claude Desktop 원격 연동 형식 (SSE 방식)"""
    return {
        "mcpServers": {
            "logccino": {
                "url": endpoint_url
            }
        }
    }

def generate_antigravity_config() -> Dict[str, Any]:
    """Google Antigravity / Gemini CLI MCP 설정 형식"""
    root = get_project_root()
    return {
        "mcpServers": {
            "logccino": {
                "command": get_python_executable(),
                "args": ["-m", "core.mcp.server"],
                "cwd": root,
                "env": {
                    "PYTHONPATH": root
                }
            }
        }
    }

def generate_cursor_config() -> Dict[str, Any]:
    """Cursor IDE MCP config 형식"""
    root = get_project_root()
    return {
        "mcpServers": {
            "logccino": {
                "command": get_python_executable(),
                "args": ["-m", "core.mcp.server"],
                "cwd": root
            }
        }
    }

def get_all_mcp_configs(remote_url: str = "http://localhost:8000/sse") -> Dict[str, Any]:
    return {
        "claude_desktop_local": generate_claude_desktop_config(),
        "claude_desktop_remote_k8s_aws": generate_remote_claude_config(remote_url),
        "antigravity": generate_antigravity_config(),
        "cursor": generate_cursor_config()
    }
