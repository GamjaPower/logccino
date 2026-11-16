#!/usr/bin/env bash
#
# Logccino systemd Service Installer
# 일반 사용자 권한(systemctl --user)으로 Logccino 백엔드 서버(FastAPI + Remote MCP)를 등록합니다.
# 사용법: bash scripts/install_systemd_service.sh
# (루트/시스템 전체 등록이 필요할 경우: sudo bash scripts/install_systemd_service.sh --system)
#

set -e

# 현재 스크립트가 있는 프로젝트 루트 경로 탐색
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$(which python3)"
fi

IS_SYSTEM=false
if [ "$1" = "--system" ]; then
    IS_SYSTEM=true
fi

echo "============================================================"
echo "☕ Logccino systemd 자동 시작 서비스 등록기"
echo "프로젝트 경로: $PROJECT_ROOT"
echo "파이썬 경로:   $VENV_PYTHON"

if [ "$IS_SYSTEM" = true ]; then
    if [ "$EUID" -ne 0 ]; then
        echo "❌ 시스템 모드(--system)는 root 권한이 필요합니다:"
        echo "   sudo bash scripts/install_systemd_service.sh --system"
        exit 1
    fi
    APP_USER="${SUDO_USER:-$USER}"
    APP_GROUP="$(id -gn "$APP_USER")"
    SERVICE_FILE="/etc/systemd/system/logccino.service"
    echo "등록 모드:     시스템 전체 (/etc/systemd/system/)"
    echo "실행 계정:     $APP_USER:$APP_GROUP"
    echo "============================================================"

    cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Logccino Agent-Native Big Data & Real-Time Intelligence Backend
After=network.target docker.service
Wants=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$PROJECT_ROOT"
EnvironmentFile=-$PROJECT_ROOT/.env
ExecStart=$VENV_PYTHON -m core.main
Restart=always
RestartSec=5
KillMode=process
TimeoutStopSec=15

StandardOutput=journal
StandardError=journal
SyslogIdentifier=logccino

[Install]
WantedBy=multi-user.target
EOF

    echo "✅ $SERVICE_FILE 생성 완료"
    systemctl daemon-reload
    systemctl enable logccino.service
    systemctl restart logccino.service

    echo "============================================================"
    echo "🎉 Logccino 서비스가 시스템 전체 서비스로 등록 및 시작되었습니다!"
    echo "📋 유용한 관리 명령어:"
    echo "   - 상태 확인:   sudo systemctl status logccino"
    echo "   - 실시간 로그: sudo journalctl -u logccino -f"
    echo "   - 서비스 재시작: sudo systemctl restart logccino"
    echo "   - 서비스 중지:   sudo systemctl stop logccino"
    echo "============================================================"
else
    # 일반 사용자 모드 (systemctl --user, sudo 불필요)
    USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
    mkdir -p "$USER_SYSTEMD_DIR"
    SERVICE_FILE="$USER_SYSTEMD_DIR/logccino.service"
    echo "등록 모드:     일반 사용자 (systemctl --user)"
    echo "서비스 파일:   $SERVICE_FILE"
    echo "============================================================"

    cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Logccino Agent-Native Big Data & Real-Time Intelligence Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$PROJECT_ROOT/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$PROJECT_ROOT"
EnvironmentFile=-$PROJECT_ROOT/.env
ExecStart=$VENV_PYTHON -m core.main
Restart=always
RestartSec=5
KillMode=process
TimeoutStopSec=15

StandardOutput=journal
StandardError=journal
SyslogIdentifier=logccino

[Install]
WantedBy=default.target
EOF

    echo "✅ $SERVICE_FILE 생성 완료"
    systemctl --user daemon-reload
    systemctl --user enable logccino.service
    systemctl --user restart logccino.service

    # 세션 종료 후에도 서비스가 유지되도록 linger 활성화 시도
    if command -v loginctl >/dev/null 2>&1; then
        loginctl enable-linger "$USER" 2>/dev/null || true
    fi

    echo "============================================================"
    echo "🎉 Logccino 서비스가 일반 사용자 서비스로 등록 및 시작되었습니다!"
    echo "👉 로그인 세션 및 시스템 재부팅 시에도 자동으로 백그라운드에서 구동됩니다."
    echo ""
    echo "📋 일반 사용자 관리 명령어 (sudo 불필요):"
    echo "   - 상태 확인:     systemctl --user status logccino"
    echo "   - 실시간 로그:   journalctl --user -u logccino -f"
    echo "   - 서비스 재시작: systemctl --user restart logccino"
    echo "   - 서비스 중지:   systemctl --user stop logccino"
    echo "============================================================"
fi
