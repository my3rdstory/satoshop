#!/bin/bash
# 새로운 웹훅 토큰 생성 및 설정 업데이트 스크립트

INSTALL_DIR="/opt/satoshop-exchange-updater"
CONFIG_FILE="$INSTALL_DIR/config.env"
BACKUP_FILE="$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"

# 루트 권한 확인
if [ "$EUID" -ne 0 ]; then
    echo "❌ 이 스크립트는 루트 권한으로 실행되어야 합니다."
    echo "sudo $0 를 사용하세요."
    exit 1
fi

echo "🔐 새로운 웹훅 토큰 생성"
echo "=" * 50

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 설정 파일을 찾을 수 없습니다: $CONFIG_FILE"
    echo "먼저 install_cron_updater.sh를 실행하세요."
    exit 1
fi

# 기존 토큰 확인
OLD_TOKEN=$(grep "WEBHOOK_TOKEN=" "$CONFIG_FILE" | cut -d'=' -f2)
if [ -n "$OLD_TOKEN" ]; then
    echo "📋 기존 토큰: $OLD_TOKEN"
fi

# 새 토큰 생성
NEW_TOKEN=$(python3 -c "
import secrets

def generate_webhook_token(length=32):
    return secrets.token_urlsafe(length)

print(generate_webhook_token())
")

echo "🆕 새로운 토큰: $NEW_TOKEN"

# 설정 파일 백업
echo "💾 설정 파일 백업: $BACKUP_FILE"
cp "$CONFIG_FILE" "$BACKUP_FILE"

# 토큰 업데이트
echo "🔄 설정 파일 업데이트"
sed -i "s/WEBHOOK_TOKEN=.*/WEBHOOK_TOKEN=$NEW_TOKEN/" "$CONFIG_FILE"

# 업데이트 확인
UPDATED_TOKEN=$(grep "WEBHOOK_TOKEN=" "$CONFIG_FILE" | cut -d'=' -f2)
if [ "$UPDATED_TOKEN" = "$NEW_TOKEN" ]; then
    echo "✅ 토큰 업데이트 성공!"
else
    echo "❌ 토큰 업데이트 실패!"
    echo "백업 파일로 복구하세요: mv $BACKUP_FILE $CONFIG_FILE"
    exit 1
fi

echo ""
echo "🚨 중요한 작업 필요:"
echo "1. 모든 SatoShop 서버의 환경변수를 새 토큰으로 업데이트하세요:"
echo "   WEBHOOK_TOKEN=$NEW_TOKEN"
echo ""
echo "2. Render.com 설정:"
echo "   - Dashboard → Service → Environment"
echo "   - WEBHOOK_TOKEN 값을 다음으로 변경:"
echo "   - $NEW_TOKEN"
echo ""
echo "3. 업데이트 후 테스트:"
echo "   sudo -u satoshop $INSTALL_DIR/run_updater.sh"
echo ""
echo "📝 백업 파일: $BACKUP_FILE"
echo "📝 설정 파일: $CONFIG_FILE"
echo ""
echo "⚠️ 모든 서버에 새 토큰을 설정할 때까지 환율 업데이트가 작동하지 않습니다!" 