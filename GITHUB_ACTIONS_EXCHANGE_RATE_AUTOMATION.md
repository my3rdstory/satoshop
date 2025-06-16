# GitHub Actions를 사용한 환율조회 자동화 가이드

SatoShop에서 GitHub Actions를 활용하여 업비트 BTC/KRW 환율을 자동으로 업데이트하는 시스템 구축 가이드입니다.

## 🎯 개요

GitHub Actions를 사용하여 주기적으로 업비트 API에서 BTC/KRW 환율을 가져와 데이터베이스에 자동 업데이트하는 시스템입니다.

### 핵심 특징
- ✅ **완전 자동화**: 5분마다 자동 실행
- ✅ **클라우드 기반**: GitHub 인프라 활용으로 안정성 보장
- ✅ **실시간 환율**: 업비트 API 연동으로 정확한 환율 제공
- ✅ **오류 처리**: 실패 시 자동 알림 및 로깅
- ✅ **비용 효율**: GitHub Actions 무료 사용량 내에서 운영

## 🏗️ 시스템 아키텍처

```mermaid
graph TD
    A[GitHub Actions<br/>Scheduler] -->|5분마다 실행| B[Ubuntu Runner]
    B --> C[Python 환경 설정]
    C --> D[의존성 설치<br/>uv sync]
    D --> E[Django 명령어 실행<br/>update_exchange_rate]
    E --> F[업비트 API 호출]
    F --> G[환율 데이터 수신]
    G --> H[PostgreSQL DB 저장]
    H --> I[환율 업데이트 완료]
    
    F -->|API 실패| J[오류 로깅]
    J --> K[GitHub Actions 실패 알림]
    
    E --> L[시간 간격 체크]
    L -->|아직 시간 안됨| M[스킵 처리]
```

## 📁 주요 구성 요소

### 1. GitHub Actions 워크플로우
**파일**: `.github/workflows/update-exchange-rate.yml`

```yaml
name: 환율 자동 업데이트

on:
  schedule:
    # 5분마다 실행 (UTC 기준)
    - cron: '*/5 * * * *'
  workflow_dispatch: # 수동 실행 버튼

jobs:
  update-exchange-rate:
    runs-on: ubuntu-latest
    
    steps:
    - name: 코드 체크아웃
      uses: actions/checkout@v4
    
    - name: Python 3.13 설정
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: uv 설치
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: 의존성 설치
      run: uv sync
    
    - name: 환율 업데이트 실행
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        SECRET_KEY: ${{ secrets.SECRET_KEY }}
        ALLOWED_HOSTS: ${{ secrets.ALLOWED_HOSTS }}
        ENABLE_DJANGO_SCHEDULER: false
      run: |
        echo "🚀 GitHub Actions에서 환율 업데이트 시작"
        uv run python manage.py update_exchange_rate --verbose
        echo "✅ 환율 업데이트 완료"
    
    - name: 실행 결과 알림 (실패 시)
      if: failure()
      run: |
        echo "❌ 환율 업데이트 실패"
        echo "GitHub Actions 로그를 확인하세요: https://github.com/${{ github.repository }}/actions"
```

### 2. Django 관리 명령어
**파일**: `myshop/management/commands/update_exchange_rate.py`

핵심 기능:
- 업비트 API 호출 및 환율 데이터 수집
- 데이터베이스 저장 및 중복 방지
- 상세한 로깅 및 오류 처리
- GitHub Actions 최적화된 출력

### 3. 환율 서비스 모듈
**파일**: `myshop/services.py`

```python
class UpbitExchangeService:
    """업비트 환율 서비스"""
    
    UPBIT_API_URL = "https://api.upbit.com/v1/ticker"
    
    @classmethod
    def fetch_btc_krw_rate(cls):
        """업비트 API에서 BTC/KRW 환율 가져오기"""
        # API 호출 및 데이터 처리 로직
```

### 4. 데이터 모델
**파일**: `myshop/models.py`

```python
class ExchangeRate(models.Model):
    """업비트 BTC/KRW 환율 데이터"""
    btc_krw_rate = models.DecimalField(max_digits=15, decimal_places=2)
    api_response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
```

## 🚀 설정 방법

### 1. GitHub Secrets 설정

GitHub 리포지토리의 Settings > Secrets and variables > Actions에서 다음 시크릿을 추가:

```env
DATABASE_URL=postgresql://username:password@hostname:port/database
SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

### 2. 워크플로우 파일 생성

`.github/workflows/update-exchange-rate.yml` 파일을 위의 내용으로 생성합니다.

### 3. Django 설정 확인

환율 업데이트 간격을 Django 어드민에서 설정:
- **경로**: `/admin/myshop/sitesettings/`
- **설정값**: `exchange_rate_update_interval` (기본: 10분)

### 4. 워크플로우 활성화

- 파일 커밋 후 GitHub에 푸시
- Actions 탭에서 워크플로우 확인
- "Run workflow" 버튼으로 수동 테스트 가능

## 📊 모니터링 및 관리

### 1. GitHub Actions 대시보드

**위치**: `https://github.com/your-username/your-repo/actions`

확인 가능한 정보:
- ✅ 실행 상태 (성공/실패)
- 📊 실행 시간 및 로그
- 📈 성공률 통계
- 🔄 재실행 기능

### 2. 실행 로그 예시

#### 성공적인 실행
```
🚀 [2025-06-15 10:05:00] 환율 업데이트 시작 (GitHub Actions)
⚙️ 환율 업데이트 간격: 10분
📊 현재 환율: 1 BTC = 145,602,000 KRW
🌐 업비트 API에서 환율 데이터 가져오는 중...
✅ 환율 업데이트 성공!
   새로운 환율: 1 BTC = 145,615,000 KRW
   업데이트 시간: 2025-06-15 10:05:02
📈 환율 상승: +13,000 KRW (+0.01%)
💾 저장된 환율 데이터: 15개
🎉 [2025-06-15 10:05:02] 환율 업데이트 완료
   실행 시간: 1.23초
```

#### 시간 간격으로 인한 스킵
```
🚀 [2025-06-15 10:03:00] 환율 업데이트 시작 (GitHub Actions)
⚙️ 환율 업데이트 간격: 10분
⏰ 아직 업데이트 시간이 되지 않았습니다.
   마지막 업데이트: 2025-06-15 10:00:15
   경과 시간: 0:02:45
   업데이트 간격: 10분
```

### 3. Django 어드민 모니터링

**환율 데이터 관리**: `/admin/myshop/exchangerate/`
- 최신 환율 확인
- 환율 변화 추이 분석
- 수동 환율 업데이트 버튼

## 🔧 고급 설정

### 1. 스케줄 커스터마이징

다양한 크론 표현식 옵션:

```yaml
# 5분마다 (현재 설정)
- cron: '*/5 * * * *'

# 10분마다
- cron: '*/10 * * * *'

# 30분마다
- cron: '*/30 * * * *'

# 1시간마다
- cron: '0 * * * *'

# 평일 업무시간에만 (9-18시)
- cron: '0 9-18 * * 1-5'
```

### 2. 다중 환경 지원

브랜치별 다른 설정:

```yaml
on:
  schedule:
    - cron: '*/5 * * * *'  # 프로덕션용
  push:
    branches: [ dev ]       # 개발용 즉시 실행
```

### 3. 알림 확장

Slack, Discord 등 외부 알림 서비스 연동:

```yaml
- name: Slack 알림
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## 🛠️ 문제 해결

### 1. 일반적인 문제들

#### API 호출 실패
```bash
# 수동 테스트
curl "https://api.upbit.com/v1/ticker?markets=KRW-BTC"
```

#### 데이터베이스 연결 오류
- `DATABASE_URL` 시크릿 확인
- PostgreSQL 서비스 상태 점검

#### 권한 오류
- GitHub Secrets 설정 확인
- Actions 권한 검증

### 2. 디버깅 방법

#### 로컬 테스트
```bash
# 환경 변수 설정 후
uv run python manage.py update_exchange_rate --verbose --force
```

#### 워크플로우 재실행
1. GitHub Actions 탭 이동
2. 실패한 워크플로우 선택
3. "Re-run jobs" 클릭

## 📈 성능 최적화

### 1. API 호출 최적화
- 타임아웃 설정: 10초
- 재시도 로직 구현
- 응답 캐싱 활용

### 2. 데이터 정리
- 오래된 환율 데이터 자동 삭제 (최근 5개만 유지)
- 인덱스 최적화로 조회 성능 향상

### 3. 리소스 사용량
- GitHub Actions 무료 사용량: 월 2,000분
- 예상 사용량: 월 약 50분 (5분마다 실행 시)

## 🔒 보안 고려사항

### 1. 시크릿 관리
- 모든 민감한 정보는 GitHub Secrets 사용
- 환경 변수 최소 권한 원칙 적용

### 2. API 보안
- 업비트 API는 공개 엔드포인트 (인증 불필요)
- Rate Limiting 고려하여 호출 간격 조정

### 3. 로그 보안
- 민감한 정보 로그 출력 금지
- 성공/실패 여부만 기록

## 📋 배포 체크리스트

- [ ] GitHub Secrets 설정 완료
  - [ ] `DATABASE_URL`
  - [ ] `SECRET_KEY`
  - [ ] `ALLOWED_HOSTS`
- [ ] 워크플로우 파일 생성 및 커밋
- [ ] Django 관리 명령어 테스트
- [ ] 수동 워크플로우 실행 테스트
- [ ] 환율 데이터 확인 (Django 어드민)
- [ ] 스케줄 실행 모니터링 (첫 24시간)
- [ ] 알림 설정 확인 (실패 시)

## 🆚 다른 방법과의 비교

| 방법 | GitHub Actions | Render Cron | Django Scheduler |
|------|----------------|-------------|------------------|
| **비용** | 무료 (2,000분/월) | 유료 | 무료 |
| **안정성** | 높음 | 높음 | 중간 |
| **설정 복잡도** | 중간 | 낮음 | 높음 |
| **확장성** | 높음 | 중간 | 낮음 |
| **모니터링** | 우수 | 우수 | 기본 |

## 🎉 마무리

GitHub Actions를 활용한 환율조회 자동화 시스템은 다음과 같은 이점을 제공합니다:

1. **완전한 자동화**: 수동 개입 없이 지속적인 환율 업데이트
2. **높은 안정성**: GitHub 인프라의 안정성과 신뢰성
3. **투명한 모니터링**: 모든 실행 과정을 실시간으로 추적 가능
4. **비용 효율성**: GitHub Actions 무료 사용량 내에서 운영
5. **확장 가능성**: 다양한 추가 기능과 알림 서비스 통합 가능

이 시스템을 통해 SatoShop은 항상 최신의 BTC/KRW 환율을 제공하며, 사용자에게 정확한 가격 정보를 보장할 수 있습니다. 