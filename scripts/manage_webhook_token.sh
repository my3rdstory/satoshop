#!/bin/bash
# SatoShop 웹훅 토큰 관리 통합 스크립트

INSTALL_DIR="/opt/satoshop-exchange-updater"
CONFIG_FILE="$INSTALL_DIR/config.env"

show_help() {
    echo "🔐 SatoShop 웹훅 토큰 관리 도구"
    echo "=" * 50
    echo ""
    echo "사용법:"
    echo "  $0 show          # 현재 토큰 확인"
    echo "  $0 generate      # 새 토큰 생성 (루트 권한 필요)"
    echo "  $0 test          # 토큰으로 웹훅 테스트"
    echo "  $0 help          # 이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 show"
    echo "  sudo $0 generate"
    echo "  $0 test https://your-domain.com/webhook/update-exchange-rate/"
}

show_token() {
    echo "🔐 현재 웹훅 토큰 확인"
    echo "=" * 50
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ 설정 파일을 찾을 수 없습니다: $CONFIG_FILE"
        echo "먼저 install_cron_updater.sh를 실행하세요."
        exit 1
    fi
    
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
    echo "📝 설정 파일 위치: $CONFIG_FILE"
}

generate_token() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ 토큰 생성은 루트 권한이 필요합니다."
        echo "sudo $0 generate 를 사용하세요."
        exit 1
    fi
    
    if [ -f "$INSTALL_DIR/scripts/generate_new_token.sh" ]; then
        "$INSTALL_DIR/scripts/generate_new_token.sh"
    else
        echo "❌ generate_new_token.sh 스크립트를 찾을 수 없습니다."
        echo "설치가 완전하지 않을 수 있습니다."
        exit 1
    fi
}

test_webhook() {
    local url="$1"
    
    if [ -z "$url" ]; then
        echo "🧪 웹훅 테스트"
        echo "=" * 50
        echo "사용법: $0 test <웹훅_URL>"
        echo ""
        echo "예시:"
        echo "  $0 test https://your-domain.com/webhook/update-exchange-rate/"
        echo ""
        echo "기본 URL 목록:"
        echo "  - https://satoshop-dev.onrender.com/webhook/update-exchange-rate/"
        echo "  - https://satoshop.onrender.com/webhook/update-exchange-rate/"
        echo "  - https://store.btcmap.kr/webhook/update-exchange-rate/"
        return 1
    fi
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ 설정 파일을 찾을 수 없습니다: $CONFIG_FILE"
        exit 1
    fi
    
    WEBHOOK_TOKEN=$(grep "SATOSHOP_WEBHOOK_TOKEN=" "$CONFIG_FILE" | cut -d'=' -f2)
    
    if [ -z "$WEBHOOK_TOKEN" ]; then
        echo "❌ 웹훅 토큰을 찾을 수 없습니다."
        exit 1
    fi
    
    echo "🧪 웹훅 테스트: $url"
    echo "=" * 50
    echo "🔐 사용할 토큰: ${WEBHOOK_TOKEN:0:8}..."
    echo ""
    
    # curl 명령 실행
    echo "📡 요청 전송 중..."
    response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "{\"token\":\"$WEBHOOK_TOKEN\",\"source\":\"manual_test_$(date +%s)\"}" \
        -w "%{http_code}" \
        --connect-timeout 10 \
        --max-time 30)
    
    # HTTP 상태 코드 추출 (마지막 3자리)
    http_code="${response: -3}"
    response_body="${response%???}"
    
    echo "📊 응답 결과:"
    echo "   HTTP 상태 코드: $http_code"
    
    case $http_code in
        200)
            echo "   ✅ 성공! 웹훅이 정상 동작합니다."
            if [ -n "$response_body" ]; then
                echo "   📄 응답 내용:"
                echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
            fi
            ;;
        401)
            echo "   ❌ 인증 실패 (HTTP 401)"
            echo "   🔑 토큰이 서버와 일치하지 않습니다."
            ;;
        404)
            echo "   ❌ 엔드포인트를 찾을 수 없음 (HTTP 404)"
            echo "   🌐 URL이 올바른지 확인하세요."
            ;;
        500)
            echo "   ❌ 서버 내부 오류 (HTTP 500)"
            echo "   🔧 서버에서 환율 업데이트 중 오류가 발생했습니다."
            ;;
        000)
            echo "   ❌ 연결 실패"
            echo "   🌐 서버가 다운되었거나 네트워크 문제입니다."
            ;;
        *)
            echo "   ❌ 예상치 못한 응답 (HTTP $http_code)"
            echo "   🌐 서버 상태를 확인하세요."
            ;;
    esac
    
    if [ -n "$response_body" ] && [ "$http_code" != "200" ]; then
        echo "   📄 오류 상세:"
        echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
    fi
}

# 메인 실행 로직
case "${1:-help}" in
    "show"|"s")
        show_token
        ;;
    "generate"|"gen"|"g")
        generate_token
        ;;
    "test"|"t")
        test_webhook "$2"
        ;;
    "help"|"h"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ 알 수 없는 명령어: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 