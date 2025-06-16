# 🚀 Satoshop 배포 가이드 (Render.com)

## 📋 목차
- [개요](#개요)
- [Git 브랜치 전략](#git-브랜치-전략)
- [환경 구성](#환경-구성)
- [초기 설정](#초기-설정)
- [배포 프로세스](#배포-프로세스)
- [Render.com 설정](#rendercom-설정)
- [환경 변수 관리](#환경-변수-관리)
- [트러블슈팅](#트러블슈팅)

## 개요

Satoshop은 개발(dev)과 운영(main) 환경을 분리하여 안전한 배포를 진행합니다.
- **개발 환경**: `dev` 브랜치 → Render.com dev 서비스
- **운영 환경**: `main` 브랜치 → Render.com production 서비스

## Git 브랜치 전략

### 브랜치 구조
```
main (운영)
├── dev (개발)
│   ├── feature/기능명 (선택사항)
│   └── hotfix/수정명 (긴급수정)
```

### 워크플로우
1. **로컬 개발**: `dev` 브랜치에서 작업
2. **개발 배포**: `dev` 브랜치로 푸시 → 자동 배포
3. **운영 배포**: `dev` → `main` PR 생성 → 리뷰 → 머지 → 자동 배포

## 환경 구성

| 환경 | 브랜치 | Render 서비스명 | 도메인 |
|------|--------|----------------|--------|
| 개발 | `dev` | satoshop-dev | satoshop-dev.onrender.com |
| 운영 | `main` | satoshop-prod | satoshop.onrender.com |

## 초기 설정

### 1. GitHub 저장소 설정

#### 단계 1: GitHub에서 빈 저장소 생성
1. GitHub에서 새 저장소 생성
2. **중요**: 다음 항목들을 체크하지 마세요
   - ❌ Add a README file
   - ❌ Add .gitignore
   - ❌ Choose a license
3. 완전히 빈 저장소로 생성

#### 단계 2: 로컬에서 원격 저장소 연결

```bash
# 원격 저장소 추가
git remote add origin https://github.com/username/satoshop.git

# 현재 master 브랜치를 dev로 푸시 (main은 비워둠)
git push -u origin master:dev

# 로컬 브랜치를 dev로 변경
git checkout -b dev
git branch -D master  # 기존 master 브랜치 삭제 (선택사항)

# 이후 dev 브랜치에서 작업
git push -u origin dev
```

#### 단계 3: 브랜치 상태 확인
```bash
# 원격 브랜치 확인
git branch -r
# 결과: origin/dev (main 브랜치는 아직 없음)

# 로컬 브랜치 확인
git branch
# 결과: * dev
```

> **중요**: main 브랜치는 의도적으로 비워둡니다. dev에서 충분한 테스트 후 첫 번째 PR로 main에 소스를 공개할 예정입니다.

### 2. GitHub 브랜치 보호 규칙 설정

> **참고**: main 브랜치가 생성된 후(첫 번째 PR 머지 후)에 설정하세요.

**main 브랜치 보호 설정:**
1. GitHub → Settings → Branches
2. "Add rule" 클릭
3. Branch name pattern: `main`
4. 다음 옵션 체크:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1명 이상)
   - ✅ Dismiss stale PR approvals when new commits are pushed
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators

### 3. 첫 번째 운영 배포 준비

dev 환경에서 충분한 테스트가 완료되면:

1. **GitHub에서 첫 번째 PR 생성**
   ```
   Base: main ← Compare: dev
   Title: "🚀 Initial Production Release"
   ```

2. **PR 설명에 포함할 내용**
   - 주요 기능 목록
   - 테스트 완료 항목
   - 알려진 이슈 (있다면)
   - 배포 후 확인사항

3. **PR 머지 후 main 브랜치 생성 완료**
   - 이때부터 운영 서버 자동 배포 시작
   - main 브랜치 보호 규칙 설정

## 배포 프로세스

### 일반적인 개발 프로세스

```bash
# 1. 최신 dev 브랜치로 업데이트
git checkout dev
git pull origin dev

# 2. 기능 개발 (선택사항: feature 브랜치 사용)
git checkout -b feature/새기능명
# 개발 작업...
git add .
git commit -m "feat: 새로운 기능 추가"

# 3. dev 브랜치로 머지
git checkout dev
git merge feature/새기능명
git push origin dev  # → 자동으로 dev 서버에 배포

# 4. dev 서버에서 테스트 완료 후 운영 배포
# GitHub에서 dev → main PR 생성
```

### 긴급 수정 (Hotfix)

> **참고**: main 브랜치가 생성된 후에만 가능합니다.

```bash
# 1. main에서 hotfix 브랜치 생성
git checkout main
git pull origin main
git checkout -b hotfix/긴급수정명

# 2. 수정 작업
git add .
git commit -m "fix: 긴급 버그 수정"

# 3. main으로 PR 생성 (리뷰 후 즉시 머지)
git push origin hotfix/긴급수정명

# 4. main → dev로도 머지하여 동기화
git checkout dev
git pull origin main  # main의 변경사항을 dev에 반영
```

### 첫 번째 운영 배포 프로세스

```bash
# 1. dev 환경에서 충분한 테스트 완료 확인
# 2. GitHub에서 첫 번째 PR 생성
#    Base: main ← Compare: dev
#    Title: "🚀 Initial Production Release"

# 3. PR 머지 후 main 브랜치 생성 완료
# 4. Render.com에서 운영 서비스 및 DB 생성
# 5. 운영 환경 배포 자동 시작
```

## Render.com 설정

### 1. 개발 환경 서비스 생성 (우선)

1. Render Dashboard → "New +" → "Web Service"
2. GitHub 저장소 연결
3. 설정값:
   - **Name**: `satoshop-dev`
   - **Branch**: `dev`
   - **Build Command**: `./build.sh`
   - **Start Command**: `uv run python manage.py runserver 0.0.0.0:$PORT`
   - **Auto-Deploy**: `Yes`

### 2. 운영 환경 서비스 생성 (나중에)

> **중요**: main 브랜치가 생성된 후에 설정하세요.

1. Render Dashboard → "New +" → "Web Service"
2. 동일한 GitHub 저장소 연결
3. 설정값:
   - **Name**: `satoshop-prod`
   - **Branch**: `main`
   - **Build Command**: `./build.sh`
   - **Start Command**: `uv run python manage.py runserver 0.0.0.0:$PORT`
   - **Auto-Deploy**: `Yes`

> **참고**: main 브랜치가 없는 동안은 운영 서비스를 생성할 수 없습니다. dev 환경에서 테스트 완료 후 첫 번째 PR을 머지한 다음 운영 서비스를 설정하세요.

### 3. 데이터베이스 설정

#### 개발 DB (즉시 생성)
1. Render Dashboard → "New +" → "PostgreSQL"
2. 설정값:
   - **Name**: `satoshop-dev-db`
   - **Database**: `satoshop_dev`
   - **User**: `satoshop_dev_user`
3. 생성 후 satoshop-dev 서비스에 연결

#### 운영 DB (나중에 생성)
> **참고**: 운영 서비스 생성 시점에 함께 생성

1. Render Dashboard → "New +" → "PostgreSQL"
2. 설정값:
   - **Name**: `satoshop-prod-db`
   - **Database**: `satoshop_prod`
   - **User**: `satoshop_prod_user`
3. 생성 후 satoshop-prod 서비스에 연결

> **보안**: 각 환경의 데이터베이스는 완전히 분리되어 있으며, 서로 다른 접근 권한을 가집니다.

## 환경 변수 관리

### 공통 환경 변수
```bash
PYTHON_VERSION=3.11
DJANGO_SETTINGS_MODULE=satoshop.settings
```

### 개발 환경 (satoshop-dev)
```bash
DEBUG=True
ENVIRONMENT=development
ALLOWED_HOSTS=satoshop-dev.onrender.com
DATABASE_URL=postgresql://... (dev DB)
SECRET_KEY=개발용_시크릿_키
```

### 운영 환경 (satoshop-prod)
```bash
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=satoshop.onrender.com,your-custom-domain.com
DATABASE_URL=postgresql://... (prod DB)
SECRET_KEY=운영용_시크릿_키
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

### 결제 관련 환경 변수
```bash
# Lightning Network 설정
BLINK_API_KEY=your_blink_api_key
BLINK_WALLET_ID=your_wallet_id

# 개발/운영별로 다른 값 사용 권장
```

## 배포 확인 체크리스트

### 개발 환경 배포 후
- [ ] 사이트 접속 확인
- [ ] 주요 기능 동작 확인
- [ ] 결제 기능 테스트 (테스트넷)
- [ ] 로그 확인

### 운영 환경 배포 후
- [ ] 사이트 접속 확인
- [ ] SSL 인증서 확인
- [ ] 주요 기능 동작 확인
- [ ] 결제 기능 테스트 (메인넷)
- [ ] 성능 모니터링
- [ ] 백업 확인

## 트러블슈팅

### 일반적인 문제들

**1. 빌드 실패**
```bash
# 로컬에서 빌드 테스트
./build.sh
uv run python manage.py collectstatic --noinput
```

**2. 환경 변수 문제**
- Render Dashboard에서 Environment 탭 확인
- 민감한 정보는 Secret Files 사용

**3. 데이터베이스 연결 실패**
- DATABASE_URL 확인
- 방화벽 설정 확인

**4. 정적 파일 문제**
```bash
# 정적 파일 수집 확인
uv run python manage.py collectstatic --noinput --clear
```

### 롤백 절차

**긴급 롤백이 필요한 경우:**
1. Render Dashboard → Deploys 탭
2. 이전 성공한 배포 선택
3. "Redeploy" 클릭

**또는 Git을 통한 롤백:**
```bash
# 이전 커밋으로 되돌리기
git revert HEAD
git push origin main  # 또는 dev
```

## 모니터링 및 로그

### Render 로그 확인
```bash
# Render Dashboard → Logs 탭에서 실시간 로그 확인
```

### 로컬에서 로그 확인
```bash
# Django 로그 설정 확인
uv run python manage.py check --deploy
```

## 단계별 배포 체크리스트

### Phase 1: 개발 환경 구축
- [ ] GitHub 빈 저장소 생성
- [ ] 로컬에서 dev 브랜치로 푸시
- [ ] Render.com 개발 서비스 생성
- [ ] 개발 DB 생성 및 연결
- [ ] 개발 환경 변수 설정
- [ ] 개발 서버 배포 확인

### Phase 2: 개발 및 테스트
- [ ] dev 브랜치에서 기능 개발
- [ ] 개발 서버에서 기능 테스트
- [ ] 결제 기능 테스트 (테스트넷)
- [ ] 성능 및 보안 검토
- [ ] 문서화 완료

### Phase 3: 운영 배포 준비
- [ ] 첫 번째 PR 생성 (dev → main)
- [ ] 코드 리뷰 완료
- [ ] PR 머지 (main 브랜치 생성)
- [ ] Render.com 운영 서비스 생성
- [ ] 운영 DB 생성 및 연결
- [ ] 운영 환경 변수 설정

### Phase 4: 운영 배포 완료
- [ ] 운영 서버 배포 확인
- [ ] SSL 인증서 확인
- [ ] 도메인 연결 (선택사항)
- [ ] main 브랜치 보호 규칙 설정
- [ ] 모니터링 설정
- [ ] 백업 설정

## 추가 권장사항

1. **정기 백업**: 데이터베이스 정기 백업 설정
2. **모니터링**: 업타임 모니터링 서비스 연동
3. **알림**: 배포 실패 시 Slack/이메일 알림 설정
4. **문서화**: 배포 시마다 CHANGELOG.md 업데이트
5. **보안**: 정기적인 의존성 업데이트 및 보안 검토

## 🚨 중요한 주의사항

1. **main 브랜치는 처음에 비어있습니다**
   - 의도적으로 소스 공개를 지연시키는 전략
   - dev에서 충분한 테스트 후 첫 PR로 공개

2. **환경 완전 분리**
   - 개발과 운영 환경은 완전히 독립적
   - 데이터베이스, 도메인, 환경변수 모두 분리

3. **자동 배포 주의**
   - dev 브랜치 푸시 시 자동 배포됨
   - main 브랜치 생성 후 운영 자동 배포 시작

---

## 📞 지원

배포 관련 문제가 발생하면:
1. 이 가이드의 트러블슈팅 섹션 확인
2. Render 로그 확인
3. GitHub Issues에 문제 등록

**마지막 업데이트**: 2024년 12월 