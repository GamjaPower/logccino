#!/usr/bin/env python3
"""
Logccino Lightweight Stdio-to-SSE MCP Bridge
Claude Desktop (Stdio) <-> Logccino Remote Server (SSE /messages)
외부 패키지 의존성 없이 Python 표준 라이브러리만으로 동작합니다.
"""

import sys
import json
import urllib.request
import urllib.error
import threading
from urllib.parse import urljoin

def run_bridge(sse_url: str):
    # 1. SSE 핸드셰이크 및 세션 엔드포인트 획득
    req = urllib.request.Request(sse_url, headers={"Accept": "text/event-stream"})
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        sys.stderr.write(f"Logccino SSE connection error: {e}\n")
        sys.exit(1)

    post_endpoint = None

    def read_sse_stream():
        nonlocal post_endpoint
        buffer = ""
        event_type = "message"
        while True:
            line = response.readline()
            if not line:
                break
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

    # endpoint 수신 대기
    for _ in range(50):
        if post_endpoint:
            break
        threading.Event().wait(0.1)

    if not post_endpoint:
        sys.stderr.write("Failed to receive endpoint event from SSE server\n")
        sys.exit(1)

    # 2. stdin(Claude Desktop)으로부터 JSON-RPC 읽어서 POST 엔드포인트로 전달
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line_clean = line.strip()
        if not line_clean:
            continue
        try:
            req_data = line_clean.encode("utf-8")
            post_req = urllib.request.Request(
                post_endpoint,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(post_req, timeout=30) as p_res:
                _ = p_res.read()
        except Exception as err:
            sys.stderr.write(f"POST error: {err}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python bridge.py <sse_url>\n")
        sys.exit(1)
    run_bridge(sys.argv[1])
