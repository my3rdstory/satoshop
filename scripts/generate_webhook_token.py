#!/usr/bin/env python3
"""
안전한 웹훅 토큰 생성 스크립트
GitHub Actions와 Django 서버 간 통신용 토큰을 생성합니다.
"""

import secrets
import string

def generate_webhook_token(length=32):
    """안전한 웹훅 토큰 생성"""
    return secrets.token_urlsafe(length)

def generate_alphanumeric_token(length=40):
    """영숫자로만 구성된 토큰 생성 (일부 시스템 호환성을 위해)"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    print("🔐 SatoShop 웹훅 토큰 생성기")
    print("=" * 50)
    
    # URL-safe 토큰 (권장)
    token1 = generate_webhook_token(32)
    print(f"📋 URL-safe 토큰 (권장):")
    print(f"   {token1}")
    print()
    
    # 영숫자 토큰 (호환성용)
    token2 = generate_alphanumeric_token(40)
    print(f"📋 영숫자 토큰 (호환성용):")
    print(f"   {token2}")
    print()
    
    print("🔧 설정 방법:")
    print("1. GitHub Secrets에 추가:")
    print("   - WEBHOOK_TOKEN: 위 토큰 중 하나 복사")
    print("   - WEBHOOK_URL: https://your-domain.com/webhook/update-exchange-rate/")
    print()
    print("2. 서버 환경변수에 추가:")
    print("   - WEBHOOK_TOKEN: GitHub과 동일한 토큰")
    print()
    print("⚠️  중요: 토큰을 안전한 곳에 보관하세요!") 