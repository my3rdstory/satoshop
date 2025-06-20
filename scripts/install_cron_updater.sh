#!/bin/bash
# SatoShop 환율 업데이트 스크립트 설치 및 설정 스크립트

set -e  # 오류 발생시 중단

echo "🚀 SatoShop 환율 업데이트 스크립트 설치 시작"

# 설치 디렉토리 설정
INSTALL_DIR="/opt/satoshop-exchange-updater"
SCRIPT_NAME="exchange_rate_updater.py"
CONFIG_FILE="config.env"
SERVICE_USER="satoshop"

# 루트 권한 확인
if [ "$EUID" -ne 0 ]; then
    echo "❌ 이 스크립트는 루트 권한으로 실행되어야 합니다."
    echo "sudo $0 를 사용하세요."
    exit 1
fi

echo "📁 설치 디렉토리 생성: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# 시스템 사용자 생성
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "👤 서비스 사용자 생성: $SERVICE_USER"
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
else
    echo "👤 서비스 사용자 이미 존재: $SERVICE_USER"
fi

# Python과 pip 설치 확인
echo "🐍 Python 설치 확인"
if ! command -v python3 &> /dev/null; then
    echo "Python3 설치 중..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv curl
fi

# uv 설치 확인 및 설치
echo "⚡ uv 패키지 매니저 설치 확인"
if ! command -v uv &> /dev/null; then
    echo "uv 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # PATH에 uv 추가
    export PATH="$HOME/.cargo/bin:$PATH"
    # 시스템 전체에서 사용할 수 있도록 심볼릭 링크 생성
    if [ -f "$HOME/.cargo/bin/uv" ]; then
        ln -sf "$HOME/.cargo/bin/uv" /usr/local/bin/uv
    fi
else
    echo "uv가 이미 설치되어 있습니다."
fi

# 가상환경 생성 (uv 우선 사용)
echo "🌍 Python 가상환경 생성"
if command -v uv &> /dev/null; then
    echo "uv를 사용하여 가상환경 생성"
    uv venv "$INSTALL_DIR/venv"
else
    echo "python3 venv를 사용하여 가상환경 생성"
    python3 -m venv "$INSTALL_DIR/venv"
fi

# 패키지 설치 (uv 우선 사용)
echo "📦 Python 패키지 설치"
if command -v uv &> /dev/null; then
    echo "uv를 사용하여 패키지 설치"
    cd "$INSTALL_DIR"
    uv pip install --python "$INSTALL_DIR/venv/bin/python" requests python-dotenv
else
    echo "pip를 사용하여 패키지 설치"
    "$INSTALL_DIR/venv/bin/pip" install requests python-dotenv
fi

# 스크립트 파일들 복사 (현재 디렉토리에서)
if [ -f "$SCRIPT_NAME" ]; then
    if [ "$(pwd)" = "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/$SCRIPT_NAME" ]; then
        echo "📄 메인 스크립트 파일이 이미 올바른 위치에 있습니다"
    else
        echo "📄 메인 스크립트 파일 복사"
        cp "$SCRIPT_NAME" "$INSTALL_DIR/"
    fi
else
    echo "❌ $SCRIPT_NAME 파일을 찾을 수 없습니다."
    echo "이 설치 스크립트를 exchange_rate_updater.py 파일과 같은 디렉토리에서 실행하세요."
    exit 1
fi

# 유틸리티 스크립트들 복사
echo "📄 유틸리티 스크립트 복사"
mkdir -p "$INSTALL_DIR/scripts"

# 스크립트 파일 목록
SCRIPT_FILES=(
    "show_webhook_token.sh"
    "generate_new_token.sh" 
    "generate_webhook_token.py"
    "manage_webhook_token.sh"
)

for script_file in "${SCRIPT_FILES[@]}"; do
    if [ -f "$script_file" ]; then
        cp "$script_file" "$INSTALL_DIR/scripts/"
        echo "  ✅ $script_file 복사 완료"
    else
        echo "  ⚠️ $script_file 파일 없음 (선택사항)"
    fi
done

# 전역 명령어 심볼릭 링크 생성
if [ -f "$INSTALL_DIR/scripts/manage_webhook_token.sh" ]; then
    ln -sf "$INSTALL_DIR/scripts/manage_webhook_token.sh" /usr/local/bin/satoshop-webhook
    echo "  🔗 전역 명령어 생성: satoshop-webhook"
fi

# 웹훅 토큰 자동 생성
echo "🔐 웹훅 토큰 자동 생성"
WEBHOOK_TOKEN=$(python3 -c "
import secrets
import string

def generate_webhook_token(length=32):
    return secrets.token_urlsafe(length)

print(generate_webhook_token())
")

echo "생성된 웹훅 토큰: $WEBHOOK_TOKEN"

# 설정 파일 생성
echo "⚙️ 설정 파일 생성"
cat > "$INSTALL_DIR/$CONFIG_FILE" << EOF
# SatoShop 환율 업데이트 스크립트 설정
# 자동 생성됨: $(date)

# 웹훅 인증 토큰 (자동 생성됨)
WEBHOOK_TOKEN=$WEBHOOK_TOKEN

# 웹훅 URL 목록 (쉼표로 구분, 선택사항)
# 설정하지 않으면 기본 URL들을 사용합니다
# WEBHOOK_URLS=https://your-domain1.com/webhook/update-exchange-rate/,https://your-domain2.com/webhook/update-exchange-rate/

# 기본 URL 목록:
# - https://satoshop-dev.onrender.com/webhook/update-exchange-rate/
# - https://satoshop.onrender.com/webhook/update-exchange-rate/
# - https://store.btcmap.kr/webhook/update-exchange-rate/
EOF

# 로그 디렉토리 및 파일 생성
echo "📝 로그 설정"
touch /var/log/satoshop_exchange_updater.log
chown "$SERVICE_USER":adm /var/log/satoshop_exchange_updater.log
chmod 640 /var/log/satoshop_exchange_updater.log

# 디렉토리 권한 설정
echo "🔐 권한 설정"
chown -R "$SERVICE_USER":root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"

# 모든 스크립트 파일에 실행 권한 부여
echo "🔧 스크립트 실행 권한 설정"
find "$INSTALL_DIR" -name "*.sh" -type f -exec chmod +x {} \;
find "$INSTALL_DIR" -name "*.py" -type f -exec chmod +x {} \;
echo "  ✅ 모든 스크립트 파일에 실행 권한 부여 완료"

# 실행 스크립트 생성
echo "🔧 실행 스크립트 생성"
cat > "$INSTALL_DIR/run_updater.sh" << EOF
#!/bin/bash
# 환경 변수 로드
set -a
source "$INSTALL_DIR/$CONFIG_FILE"
set +a

# 가상환경 활성화 및 스크립트 실행
cd "$INSTALL_DIR"
"$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/$SCRIPT_NAME"
EOF

chmod +x "$INSTALL_DIR/run_updater.sh"
chown "$SERVICE_USER":root "$INSTALL_DIR/run_updater.sh"

# logrotate 설정
echo "🔄 로그 로테이션 설정"
cat > /etc/logrotate.d/satoshop-exchange-updater << 'EOF'
/var/log/satoshop_exchange_updater.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    postrotate
        /bin/systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
EOF

echo ""
echo "✅ 설치 완료!"
echo ""
echo "🔐 생성된 웹훅 토큰:"
echo "   $WEBHOOK_TOKEN"
echo ""
echo "📋 서버 설정 (중요!):"
echo "1. 각 SatoShop 서버의 환경변수에 다음을 추가하세요:"
echo "   WEBHOOK_TOKEN=$WEBHOOK_TOKEN"
echo ""
echo "   🔧 Render.com 설정 방법:"
echo "   - Dashboard → Service → Environment"
echo "   - Add Environment Variable"
echo "   - Key: WEBHOOK_TOKEN"
echo "   - Value: $WEBHOOK_TOKEN"
echo ""
echo "📋 다음 단계:"
echo "1. 수동 테스트:"
echo "   sudo -u $SERVICE_USER $INSTALL_DIR/run_updater.sh"
echo ""
echo "2. crontab 설정 (10분마다 실행):"
echo "   sudo crontab -u $SERVICE_USER -e"
echo "   다음 라인 추가:"
echo "   */10 * * * * $INSTALL_DIR/run_updater.sh >/dev/null 2>&1"
echo ""
echo "3. 로그 확인:"
echo "   tail -f /var/log/satoshop_exchange_updater.log"
echo ""
echo "🔧 유틸리티 명령어:"
echo "   토큰 관리 (통합): satoshop-webhook [show|generate|test|help]"
echo "   토큰 확인: $INSTALL_DIR/scripts/show_webhook_token.sh"
echo "   새 토큰 생성: sudo $INSTALL_DIR/scripts/generate_new_token.sh"
echo ""
echo "💡 간편 사용법:"
echo "   satoshop-webhook show              # 현재 토큰 확인"
echo "   sudo satoshop-webhook generate     # 새 토큰 생성"
echo "   satoshop-webhook test <URL>        # 웹훅 테스트"
echo ""
echo "🔧 설치 위치: $INSTALL_DIR"
echo "📝 설정 파일: $INSTALL_DIR/$CONFIG_FILE"
echo "📝 로그 파일: /var/log/satoshop_exchange_updater.log"
echo "👤 실행 사용자: $SERVICE_USER"
echo ""
echo "⚠️ 중요: 생성된 웹훅 토큰을 모든 SatoShop 서버에 설정해야 합니다!" 