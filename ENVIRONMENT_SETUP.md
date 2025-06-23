# 환경별 설정 가이드

이 문서는 satoshop-dev 프로젝트의 환경별 설정 방법을 설명합니다.

## 🏗️ 환경 구분

### 1. 로컬 개발 환경
- **용도**: 개발자 로컬 머신에서 개발 및 테스트
- **도메인**: `localhost:8000` 또는 ngrok 터널
- **설정 방법**: `.env.local` 파일

### 2. 개발 서버 환경 (렌더)
- **용도**: 팀 공유 개발 서버, 스테이징
- **도메인**: `dev-app.onrender.com`
- **설정 방법**: 렌더 환경변수 설정

### 3. 운영 서버 환경 (렌더)
- **용도**: 실제 서비스 운영
- **도메인**: `your-app.onrender.com`
- **설정 방법**: 렌더 환경변수 설정

## ⚙️ 라이트닝 인증 도메인 설정

### 로컬 개발 환경

#### Option 1: localhost 사용
```bash
# .env.local
DEBUG=True
LNURL_AUTH_ROOT_DOMAIN=localhost:8000
```
- **장점**: 설정 간단
- **단점**: 실제 라이트닝 지갑에서 테스트 불가 (외부 접근 불가)

#### Option 2: ngrok 사용 (권장)
```bash
# .env.local
DEBUG=True
NGROK_DOMAIN=abc123.ngrok-free.app
LNURL_AUTH_ROOT_DOMAIN=abc123.ngrok-free.app
```
- **장점**: 실제 라이트닝 지갑으로 테스트 가능
- **단점**: ngrok 도메인이 변경될 때마다 설정 업데이트 필요

### 운영 환경
```bash
# .env.production
DEBUG=False
LNURL_AUTH_ROOT_DOMAIN=yourdomain.com
```

## 🚀 환경별 배포 가이드

### 로컬 개발 환경 설정

1. **환경 파일 생성**
   ```bash
   cp env.local.example .env.local
   ```

2. **ngrok 설정 (선택사항)**
   ```bash
   # ngrok 실행
   ngrok http 8000
   
   # 생성된 도메인을 .env.local에 설정
   NGROK_DOMAIN=abc123.ngrok-free.app
   LNURL_AUTH_ROOT_DOMAIN=abc123.ngrok-free.app
   ```

3. **Django 개발 서버 실행**
   ```bash
   uv run python manage.py runserver
   ```

### 렌더 배포 환경 설정

#### 개발 서버 (dev-app.onrender.com)
```bash
# 렌더 환경변수 설정
SECRET_KEY=your-dev-secret-key
DEBUG=True  # 개발 서버는 디버그 모드
ALLOWED_HOSTS=dev-app.onrender.com
RENDER=true

# 라이트닝 인증
LNURL_AUTH_ROOT_DOMAIN=dev-app.onrender.com
LNURL_AUTH_K1_TIMEOUT=3600

# 기타 개발용 설정...
```

#### 운영 서버 (your-app.onrender.com)
```bash
# 렌더 환경변수 설정
SECRET_KEY=your-production-secret-key
DEBUG=False  # 운영은 디버그 모드 비활성화
ALLOWED_HOSTS=your-app.onrender.com
RENDER=true

# 라이트닝 인증
LNURL_AUTH_ROOT_DOMAIN=your-app.onrender.com
LNURL_AUTH_K1_TIMEOUT=3600

# 데이터베이스 (렌더에서 자동 설정)
DATABASE_URL=postgresql://...

# 기타 운영용 설정...
```

#### 빌드 및 시작 명령어 (공통)
- **빌드**: `./build.sh`
- **시작**: `uv run gunicorn satoshop.wsgi:application`

**⚠️ 중요**: 렌더에서는 `.env` 파일을 배포하지 마세요. 렌더의 환경변수 설정 메뉴를 사용하는 것이 보안상 안전합니다.

## 🔧 환경별 주요 차이점

| 설정 항목 | 로컬 개발 | 렌더 개발서버 | 렌더 운영서버 |
|-----------|-----------|-------------|-------------|
| 환경변수 설정 | `.env.local` 파일 | 렌더 대시보드 | 렌더 대시보드 |
| DEBUG | True | True | False |
| HTTPS | ngrok만 | True | True |
| 도메인 | localhost/ngrok | dev-app.onrender.com | app.onrender.com |
| 데이터베이스 | 로컬 PostgreSQL | 렌더 PostgreSQL | 렌더 PostgreSQL |
| S3 스토리지 | 선택사항 | 개발용 | 운영용 |

## 🐛 문제 해결

### 1. 라이트닝 지갑에서 "인보이스가 아님" 오류
- **원인**: 잘못된 도메인 설정 또는 HTTPS 접근 불가
- **해결**: `LNURL_AUTH_ROOT_DOMAIN` 설정 확인

### 2. ngrok 도메인 변경 시
- **원인**: ngrok 무료 버전은 재시작 시 도메인 변경
- **해결**: 새 도메인으로 환경변수 업데이트

### 3. 운영 환경에서 localhost 참조
- **원인**: 환경변수 설정 누락
- **해결**: 운영 서버에서 `LNURL_AUTH_ROOT_DOMAIN` 또는 `LNURL_DOMAIN` 설정 확인

### 4. 기존 LNURL_DOMAIN 환경변수 사용
- **호환성**: `LNURL_DOMAIN` 환경변수도 지원 (기존 설정과의 호환성)
- **우선순위**: `LNURL_AUTH_ROOT_DOMAIN` > `LNURL_DOMAIN` > 기본값

## 📝 체크리스트

### 배포 전 확인사항
- [ ] 환경변수 설정 완료
- [ ] 도메인 설정 정확성 확인
- [ ] HTTPS 접근 가능 여부 확인
- [ ] 라이트닝 지갑 테스트 완료
- [ ] 데이터베이스 연결 확인
- [ ] S3 스토리지 설정 확인 (운영 환경)

### 라이트닝 기능 테스트
- [ ] LNURL 생성 확인
- [ ] QR 코드 생성 확인
- [ ] 라이트닝 지갑 스캔 테스트
- [ ] 인증 완료 확인
- [ ] 로그인/회원가입 확인 