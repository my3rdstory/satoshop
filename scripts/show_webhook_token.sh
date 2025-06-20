#!/bin/bash
# 설치된 웹훅 토큰 확인 스크립트

INSTALL_DIR="/opt/satoshop-exchange-updater"
CONFIG_FILE="$INSTALL_DIR/config.env"

echo "🔐 SatoShop 웹훅 토큰 확인"
echo "=" * 50

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 설정 파일을 찾을 수 없습니다: $CONFIG_FILE"
    echo "먼저 install_cron_updater.sh를 실행하세요."
    exit 1
fi

# 토큰 추출
WEBHOOK_TOKEN=$(grep "SATOSHOP_WEBHOOK_TOKEN=" "$CONFIG_FILE" | cut -d'=' -f2)

if [ -z "$WEBHOOK_TOKEN" ]; then
    echo "❌ 웹훅 토큰을 찾을 수 없습니다."
    exit 1
fi

echo "📋 현재 설정된 웹훅 토큰:"
echo "   $WEBHOOK_TOKEN"
echo ""
echo "📋 서버 환경변수 설정:"
echo "   WEBHOOK_TOKEN=$WEBHOOK_TOKEN"
echo ""
echo "🔧 Render.com 설정 방법:"
echo "   1. Dashboard → Service → Environment"
echo "   2. Add Environment Variable"
echo "   3. Key: WEBHOOK_TOKEN"
echo "   4. Value: $WEBHOOK_TOKEN"
echo ""
echo "🧪 웹훅 테스트:"
echo "   curl -X POST \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"token\": \"$WEBHOOK_TOKEN\", \"source\": \"manual_test\"}' \\"
echo "     https://your-domain.com/webhook/update-exchange-rate/"
echo ""
echo "📝 설정 파일 위치: $CONFIG_FILE" 