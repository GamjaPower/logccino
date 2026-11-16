#!/usr/bin/env bash
#
# Logccino systemd Service Installer
# 시스템 재부팅 시에도 Logccino 백엔드 서버(FastAPI + Remote MCP)가 자동 시작되도록 서비스로 등록합니다.
# 사용법: sudo bash scripts/install_systemd_service.sh
#

set -e

# 현재 스크립트가 있는 프로젝트 루트 경로 탐색
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 실제 실행 사용자 결정 (sudo로 실행 시 SUDO_USER, 아니면 현재 USER)
APP_USER="${SUDO_USER:-$USER}"
APP_GROUP="$(id -gn "$APP_USER")"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$(which python3)"
fi

SERVICE_FILE="/etc/systemd/system/logccino.service"

echo "============================================================"
echo "☕ Logccino systemd 자동 시작 서비스 등록기"
echo "프로젝트 경로: $PROJECT_ROOT"
echo "실행 계정:     $APP_USER:$APP_GROUP"
echo "파이썬 경로:   $VENV_PYTHON"
echo "서비스 파일:   $SERVICE_FILE"
echo "============================================================"

# root 권한 확인
if [ "$EUID" -ne 0 ]; then
    echo "❌ root 권한이 필요합니다. 아래 명령어로 실행해 주세요:"
    echo "   sudo bash scripts/install_systemd_service.sh"
    exit 1
fi

# systemd 유닛 파일 생성
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

# 로깅
StandardOutput=journal
StandardError=journal
SyslogIdentifier=logccino

[Install]
WantedBy=multi-user.target
EOF

echo "✅ $SERVICE_FILE 생성 완료"

# systemd 데몬 리로드 및 서비스 등록
systemctl daemon-reload
systemctl enable logccino.service

echo "🚀 logccino.service 시작 중..."
systemctl restart logccino.service

echo "============================================================"
echo "🎉 Logccino 서비스가 성공적으로 등록 및 시작되었습니다!"
echo "👉 시스템이 재부팅되어도 자동으로 백그라운드에서 구동됩니다."
echo ""
echo "📋 유용한 관리 명령어:"
echo "   - 상태 확인:   sudo systemctl status logccino"
echo "   - 실시간 로그: sudo journalctl -u logccino -f"
echo "   - 서비스 재시작: sudo systemctl restart logccino"
echo "   - 서비스 중지:   sudo systemctl stop logccino"
echo "============================================================"
