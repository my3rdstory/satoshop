#!/usr/bin/env python3
"""
안전한 웹훅 토큰 생성 스크립트
GitHub Actions와 Django 서버 간 통신용 토큰을 생성합니다.

사용법:
    uv run python scripts/generate_webhook_token.py
"""

import secrets
import string
import os

def generate_webhook_token(length=32):
    """안전한 웹훅 토큰 생성 (URL-safe)"""
    return secrets.token_urlsafe(length)

def generate_alphanumeric_token(length=40):
    """영숫자로만 구성된 토큰 생성 (일부 시스템 호환성을 위해)"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_token(length=32):
    """16진수 토큰 생성"""
    return secrets.token_hex(length)

def print_setup_instructions(token):
    """설정 방법 상세 안내"""
    print("🔧 설정 방법:")
    print("=" * 50)
    print()
    
    print("1️⃣ GitHub Secrets 설정:")
    print("   - GitHub 리포지토리 → Settings → Secrets and variables → Actions")
    print("   - New repository secret 클릭")
    print("   - 다음 두 개 시크릿 추가:")
    print()
    print(f"   📋 Name: WEBHOOK_URL")
    print(f"       Secret: https://your-render-app.onrender.com/webhook/update-exchange-rate/")
    print()
    print(f"   📋 Name: WEBHOOK_TOKEN")
    print(f"       Secret: {token}")
    print()
    
    print("2️⃣ 서버 환경변수 설정:")
    print("   - Render.com Dashboard → Your Service → Environment")
    print("   - Add Environment Variable 클릭")
    print()
    print(f"   📋 Key: WEBHOOK_TOKEN")
    print(f"       Value: {token}")
    print()
    
    print("3️⃣ 웹훅 테스트:")
    print("   # 로컬 테스트")
    print("   curl -X POST \\")
    print("     -H \"Content-Type: application/json\" \\")
    print(f"     -d '{{\"token\": \"{token}\", \"source\": \"manual_test\"}}' \\")
    print("     http://localhost:8000/webhook/update-exchange-rate/")
    print()
    print("   # 실제 서버 테스트")
    print("   curl -X POST \\")
    print("     -H \"Content-Type: application/json\" \\")
    print(f"     -d '{{\"token\": \"{token}\", \"source\": \"manual_test\"}}' \\")
    print("     https://your-render-app.onrender.com/webhook/update-exchange-rate/")
    print()
    
    print("4️⃣ GitHub Actions 테스트:")
    print("   - GitHub → Actions 탭")
    print("   - \"환율 자동 업데이트 (웹훅 방식)\" 워크플로우 선택")
    print("   - \"Run workflow\" 버튼 클릭")
    print()

if __name__ == "__main__":
    print("🔐 SatoShop 웹훅 토큰 생성기")
    print("=" * 50)
    print("GitHub Actions 환율 자동 업데이트용 보안 토큰을 생성합니다.")
    print()
    
    # URL-safe 토큰 (권장)
    token1 = generate_webhook_token(32)
    print(f"📋 URL-safe 토큰 (권장):")
    print(f"   {token1}")
    print(f"   길이: {len(token1)}자")
    print()
    
    # 영숫자 토큰 (호환성용)
    token2 = generate_alphanumeric_token(40)
    print(f"📋 영숫자 토큰 (호환성용):")
    print(f"   {token2}")
    print(f"   길이: {len(token2)}자")
    print()
    
    # 16진수 토큰
    token3 = generate_hex_token(32)
    print(f"📋 16진수 토큰:")
    print(f"   {token3}")
    print(f"   길이: {len(token3)}자")
    print()
    
    # 권장 토큰 선택
    recommended_token = token1
    print(f"✅ 권장 토큰: {recommended_token}")
    print()
    
    # 상세 설정 가이드
    print_setup_instructions(recommended_token)
    
    print("⚠️  보안 주의사항:")
    print("   - 토큰을 안전한 곳에 보관하세요")
    print("   - 토큰을 코드에 하드코딩하지 마세요")
    print("   - 3-6개월마다 토큰을 갱신하세요")
    print("   - 토큰이 노출되면 즉시 새로 생성하세요")
    print()
    
    print("📚 추가 도움말:")
    print("   - WEBHOOK_SETUP_GUIDE.md: 빠른 설정 가이드")
    print("   - GITHUB_ACTIONS_EXCHANGE_RATE_AUTOMATION.md: 상세 가이드") 