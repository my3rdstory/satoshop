# SatoShop - 비트코인 라이트닝 네트워크 전자상거래 플랫폼

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green.svg)](https://www.djangoproject.com/)
[![Lightning Network](https://img.shields.io/badge/Lightning-Network-orange.svg)](https://lightning.network/)

## 📋 목차

- [프로젝트 소개](#-프로젝트-소개)
- [주요 기능](#-주요-기능)
- [시스템 아키텍처](#-시스템-아키텍처)
- [기술 스택](#-기술-스택)
- [설치 및 설정](#-설치-및-설정)
- [환경 변수 설정](#-환경-변수-설정)
- [배포](#-배포)
- [관리자 기능](#-관리자-기능)
- [프로젝트 구조](#-프로젝트-구조)
- [주의사항](#-주의사항)
- [라이선스](#-라이선스)
- [연락처](#-연락처)

## 🚀 프로젝트 소개

SatoShop은 비트코인 라이트닝 네트워크를 활용한 전자상거래 플랫폼입니다. 사용자는 개인 스토어를 개설하고 상품을 판매할 수 있으며, 구매자는 라이트닝 네트워크를 통해 빠르고 저렴한 비트코인 결제를 할 수 있습니다.

### ⚠️ 개발자 고지사항

**이 프로젝트는 비개발자가 AI 코딩 도구(바이브 코딩)를 활용하여 제작되었습니다.**

- 코드의 구조와 품질이 전문 개발자 수준에 미치지 못할 수 있습니다.
- 보안 취약점이나 성능 이슈가 존재할 가능성이 있습니다.
- 오픈소스 프로젝트 관리 경험이 부족하여 실수가 있을 수 있습니다.
- 코드 리뷰와 개선 제안을 환영합니다.
- 특히 라이트닝 인보이스 생성 후 결제 프로세스의 안정성을 높이는데 도움이 필요합니다.
- 깃허브로 다른 커트리뷰터와 협업해 본 경험이 없기 때문에 공동 작업에 서툴 수 있습니다.
- 혼자 개발할 때에도 로컬에서 dev 브랜치로 작업한 후 dev에 푸시하고, 이를 main에 반영할 때에는 PR을 올리고 머지하는 방식으로 진행했습니다.
- 협업을 할 때에도 이 방식으로 진행하는 것을 권장드립니다.

**프로덕션 환경에서 사용하기 전에 반드시 전문가의 코드 검토를 받으시기 바랍니다.**

## ✨ 주요 기능

### 🏪 스토어 관리
- **개인 스토어 개설**: 사용자별 고유한 스토어 생성
- **스토어 커스터마이징**: 테마 색상, 그라디언트 배경, 설명, 연락처 설정
- **스토어 이미지 관리**: S3 호환 오브젝트 스토리지 연동
- **API 설정 관리**: Blink API 키 및 월렛 ID 암호화 저장
- **스토어 활성화/비활성화**: 스토어 운영 상태 관리

### 🍽️ 메뉴 관리
- **메뉴 시스템**: 레스토랑, 카페 등을 위한 전문 메뉴 관리 기능
- **카테고리 관리**: 드래그 앤 드롭으로 카테고리 순서 변경
- **메뉴 이미지**: 각 메뉴 항목별 이미지 업로드
- **가격 옵션**: 원화/사토시 가격 표시 및 할인가 설정
- **메뉴판 뷰**: 데스크톱/모바일 최적화된 메뉴판 표시
- **실시간 품절 관리**: 메뉴 아이템 실시간 품절 처리

### 🛍️ 상품 관리
- **상품 등록/수정/삭제**: 마크다운 지원 상품 설명
- **이미지 업로드**: 다중 이미지 업로드 및 순서 관리
- **가격 설정**: 사토시 또는 원화 단위 가격 표시 (실시간 환율 변환)
- **할인 기능**: 할인가 설정 및 할인율 자동 계산
- **카테고리 관리**: 스토어별 상품 카테고리 생성·정렬 및 기본 "카테고리 없음" 자동 매핑
- **카테고리 일괄 매칭 툴**: 카테고리 관리 화면에서 상품을 대량으로 선택하여 원하는 카테고리에 즉시 배치
- **상품 옵션**: 다양한 옵션 및 추가 가격 설정 (최대 20개 옵션, 각 옵션당 최대 20개 선택지)
- **완료 메시지**: 구매 완료 시 고객에게 표시할 맞춤 메시지 설정

### 💰 결제 시스템
- **라이트닝 네트워크 결제**: Blink API 연동
- **QR 코드 생성**: 모바일 지갑 연동
- **실시간 결제 확인**: 자동 결제 상태 추적
- **인보이스 관리**: 결제 내역 및 상태 관리
- **수동 주문 복구 도구**: 스토어 주인장이 결제 트랜잭션 상세 화면에서 배송 정보와 장바구니를 확인 후 주문으로 저장
- **환율 자동 업데이트**: 업비트 API를 통한 BTC/KRW 환율 자동 갱신
- **환율 요약 이메일**: 1시간마다 최근 5개 환율 데이터를 모아서 요약 내용을 텔레그램으로 전송

### 🏠 메인 랜딩 페이지
- **히어로 섹션**: 라이트닝 네트워크 기반 상점의 핵심 가치를 전달하고, 사용자 상태에 맞춘 CTA 버튼으로 빠른 온보딩 유도
- **실시간 지표 패널**: Django 어드민 데이터를 기반으로 전체/활성 스토어 수, 상품·밋업·디지털 파일·라이브 강의·메뉴 총합을 실시간 표시하며, 업비트 BTC/KRW 환율과 동기화 시각까지 함께 안내
- **기능/프로세스 하이라이트**: 노코드 스토어 빌더, 실시간 환율 동기화 등 주요 기능과 3단계 온보딩 절차를 섹션별로 정리
- **사용 사례 & 후기**: 굿즈샵, 디지털 콘텐츠, 오프라인 결제 등 다양한 활용 시나리오와 사용자 추천사를 통해 후킹 강화
- **FAQ 및 최종 CTA**: 자주 묻는 질문 아코디언과 데모 링크를 포함해 가입 전 궁금증을 해소하고 행동 유도

### 🛒 주문 관리
- **장바구니 기능**: 단일 스토어 상품 주문 (스토어별 분리 구매)
- **주문 추적**: 주문 상태별 관리
- **배송 정보**: 배송지 및 배송비 관리
- **주문 내역**: 구매자/판매자별 주문 조회

### 📄 디지털 파일 판매
- **디지털 파일 판매**: 이미지, 문서, 영상 등 디지털 콘텐츠 판매 기능
- **파일 업로드**: S3 호환 스토리지 연동
- **다운로드 관리**: 구매자별 다운로드 횟수 및 기간 제한
- **미리보기 이미지**: 파일 미리보기 이미지 자동 리사이징 (16:9)

### 🎓 라이브 강의
- **라이브 강의 개설**: 온라인 라이브 강의 생성 및 관리
- **참가 신청**: 라이트닝 결제를 통한 참가 신청
- **정원 관리**: 최대 참가 인원 설정 및 자동 마감
- **참가자 관리**: 참가자 목록 확인 및 CSV 다운로드
- **5단계 결제 플로우**: 상품·밋업과 동일한 라이트닝 결제 단계 적용

### 🤝 밋업
- **밋업 개설**: 오프라인 밋업 생성 및 관리
- **참가 신청**: 라이트닝 결제를 통한 참가 신청
- **옵션 기능**: 참가 유형, 식사 등 다양한 옵션 추가
- **참석 확인**: QR 코드 스캔을 통한 간편한 참석 확인 (밋업 체커)

### 👤 사용자 관리
- **회원가입/로그인**: Django 기본 인증 시스템
- **프로필 관리**: 사용자 정보 수정
- **권한 관리**: 스토어 소유자 권한 분리

### 🎨 UI/UX 개선사항
- **다크/라이트 모드**: 자동 테마 감지 및 수동 전환
- **반응형 디자인**: 모바일 우선 설계
- **해시 기반 정적 파일 캐싱**: 브라우저 캐시 최적화
- **마크다운 렌더링**: 상품 설명 및 스토어 정보 마크다운 지원
- **모바일 스토어 메뉴**: 결제 정보 확인 등 운영 링크를 모바일 내비게이션에도 동일하게 제공
- **유용한 링크 드롭다운**: 명예의 전당과 밈갤러리를 "유용한 링크" 하위 메뉴로 정리해 내비게이션을 간결하게 유지

### 📣 커뮤니티 홍보 지원
- **BAH 홍보요청 페이지**: 글로벌 내비게이션에서 `BAH 홍보요청`을 선택해 비트코인 결제 매장을 등록·수정할 수 있습니다. 라이트닝 인증을 완료하면 매장 정보와 최대 4장의 사진을 업로드할 수 있으며, 제출 후에는 신라스토어 스티커 신청 링크와 입력 내용 수정 버튼이 제공됩니다.
- **Wallet of Satoshi 가이드**: 라이트닝 인증이 처음인 셀러를 위해 월오사 설치·인증 절차를 설명하는 가이드 페이지(`/stores/bah/wallet-of-satoshi-guide/`)를 함께 제공합니다. Django Admin의 **BAH 링크 설정** 메뉴에서 “라이트닝 로그인 가이드”와 “월오사 사용법” 링크를 원하는 문서로 교체할 수 있습니다.
- **BAH 관리자 콘솔**: Django Admin에서 BAH 관리자를 지정하면 `/stores/bah/promotion-request/admin` 대시보드에서 1:1 신청 목록과 상세 내용을 열람하고, 라이트닝 로그인 신청자의 홍보 패키지 발송 상태(발송예정 ↔ 발송)를 토글할 수 있습니다. 신청 페이지에는 Bitcoin Accepted Here(BAH) 안내와 BAH 관리자 전용 “목록 관리하기” 버튼이 노출됩니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│   (Templates)   │    │   (Django)      │    │   Services      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • HTML/CSS/JS   │◄──►│ • Django Views  │◄──►│ • Blink API     │
│ • Tailwind CSS  │    │ • REST APIs     │    │ • PostgreSQL    │
│ • QR Code Gen   │    │ • Authentication│    │ • S3 Storage    │
│ • AJAX Calls    │    │ • Session Mgmt  │    │ • Upbit API     │
│ • Theme Toggle  │    │ • Scheduler     │    │ • APScheduler   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 데이터베이스 구조

```
Users ──┐
        ├── Stores ──┬── Products ──┬── ProductImages
        │            │              └── ProductOptions
        │            └── StoreImages
        │
        └── Orders ──┬── OrderItems
                     └── Invoices

SiteSettings ──┬── ExchangeRate (환율 데이터)
               └── DjangoJob (스케줄러 작업)
```

## 🛠️ 기술 스택

### Backend
- **Python 3.13+**: 메인 프로그래밍 언어
- **Django 5.2+**: 웹 프레임워크
- **PostgreSQL**: 메인 데이터베이스
- **uv**: Python 패키지 관리자
- **Django APScheduler**: 정기 작업 스케줄러

### Frontend
- **HTML5/CSS3**: 마크업 및 스타일링
- **JavaScript (ES6+)**: 클라이언트 사이드 로직
- **Tailwind CSS**: 유틸리티 우선 CSS 프레임워크
- **Font Awesome**: 아이콘
- **EasyMDE**: 마크다운 에디터

### 외부 서비스
- **Blink API**: 라이트닝 네트워크 결제
- **S3 호환 스토리지**: 이미지 파일 저장
- **Upbit API**: BTC/KRW 환율 조회

### 배포 및 인프라
- **Render.com**: 메인 배포 플랫폼 (프로덕션 환경)
- **Gunicorn**: WSGI 서버
- **WhiteNoise**: 정적 파일 서빙
- **PostgreSQL**: Render.com 제공 관리형 데이터베이스
- **Docker**: 로컬 개발 환경용 (선택사항)

### 개발 도구
- **Cryptography**: API 키 암호화
- **qrcode**: QR 코드 생성 (Python)
- **Pillow**: 이미지 처리
- **Bleach**: HTML 새니타이징
- **Markdown**: 마크다운 렌더링

## 🔧 설치 및 설정

### 시스템 요구사항

- Python 3.13 이상
- PostgreSQL 15 이상
- uv (Python 패키지 관리자)
- Git

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/satoshop.git
cd satoshop

# 개발 브랜치로 전환 (로컬 개발용)
git checkout dev
```

### 2. Python 환경 설정

```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate     # Windows

# 의존성 설치
uv pip install -r requirements.txt
```

### 3. 데이터베이스 설정

#### Docker를 사용한 PostgreSQL 설정 (개발용)

```bash
# Docker Compose로 PostgreSQL 실행
docker-compose up -d postgres

# 데이터베이스 연결 확인
docker-compose logs postgres
```

#### 직접 PostgreSQL 설치

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql
brew services start postgresql

# 데이터베이스 및 사용자 생성
sudo -u postgres psql
CREATE DATABASE satoshop_main;
CREATE USER satoshop_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE satoshop_main TO satoshop_user;
\q
```

### 4. 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env

# .env 파일 편집 (아래 환경 변수 설정 참조)
nano .env
```

### 5. 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
uv run python manage.py makemigrations

# 마이그레이션 실행
uv run python manage.py migrate

# 슈퍼유저 생성
uv run python manage.py createsuperuser
```

### 6. 정적 파일 수집

```bash
uv run python manage.py collectstatic
```

### 7. 환율 데이터 초기화 (선택사항)

```bash
# 초기 환율 데이터 가져오기
uv run python manage.py update_exchange_rate --force
```

### 8. 개발 서버 실행

```bash
uv run python manage.py runserver
```

서버가 실행되면 `http://localhost:8011`에서 애플리케이션에 접근할 수 있습니다. (기본 실행 포트는 8011로 자동 설정됩니다.)

## 🔐 환경 변수 설정

`.env` 파일에 다음 환경 변수들을 설정해야 합니다:

### Django 기본 설정

```env
# Django 보안 키 (필수)
SECRET_KEY=your-very-long-and-random-secret-key-here

# 디버그 모드 (개발: True, 운영: False)
DEBUG=False

# 허용된 호스트 (쉼표로 구분)
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

### 데이터베이스 설정

```env
# PostgreSQL 연결 정보
DB_NAME=satoshop_main
DB_USER=satoshop_user
DB_PASSWORD=your-secure-database-password
DB_HOST=localhost
DB_PORT=5432
```

### S3 오브젝트 스토리지 설정

```env
# S3 호환 스토리지 (이미지 업로드용)
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=your-bucket-name
S3_ENDPOINT_URL=https://your-s3-endpoint.com
S3_REGION_NAME=kr-standard
S3_USE_SSL=True
S3_FILE_OVERWRITE=False
S3_CUSTOM_DOMAIN=your-cdn-domain.com

# 핫링크 보호 설정 (이미지 외부 사용 방지)
HOTLINK_PROTECTION_ENABLED=True
HOTLINK_ALLOWED_DOMAINS=trusted-partner.com,cdn.example.com
```

### 알림 설정

#### 텔레그램 환율 알림
```env
# 텔레그램 봇 설정 (실시간 환율 알림용)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

#### Gmail 이메일 설정
```env
# Gmail SMTP 설정 (환율 요약 이메일용)
EMAIL_HOST_USER=satoshopkr@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=satoshopkr@gmail.com
```

> **설정 방법**:
> - **텔레그램**: 관리자 패널 → 사이트 설정에서 봇 토큰과 채팅 ID 입력
> - **Gmail**: 2단계 인증 활성화 후 앱 비밀번호 생성하여 환경 변수에 설정
> - **알림 수신**: 사이트 설정에서 이메일 주소 설정

### 관리자 계정 설정 (배포용)

```env
# 자동 생성될 관리자 계정
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your-secure-admin-password
```

### Blink API 설정

각 스토어별로 개별 설정되므로 환경 변수가 아닌 스토어 설정에서 관리됩니다.

### Lightning 결제 워크플로우

새로운 5단계 결제 플로우는 `ln_payment` 앱을 중심으로 동작하며, Blink API 상태에 맞추어 트랜잭션을 기록합니다.

1. **결제 준비** – 장바구니와 재고를 검증하고 `PaymentTransaction` + `OrderItemReservation`을 생성합니다.
2. **인보이스 생성** – Blink GraphQL을 호출해 인보이스를 발행하고 QR/문자열을 반환합니다.
3. **결제 확인** – `lnInvoicePaymentStatus`를 폴링하여 사용자의 결제 여부를 확인합니다.
4. **입금 확인** – Blink webhook(`receive.lightning`) 또는 `transactionsByPaymentHash` 조회 결과로 스토어 지갑 입금을 기록합니다.
5. **주문 저장** – 결제가 확인되면 기존 주문 생성 로직을 통해 주문/이메일/마이페이지 정보를 완성합니다.

#### 백엔드 연동 포인트
- `ln_payment/services.py`의 `LightningPaymentProcessor`가 상태 머신, soft-lock, Blink API 호출을 담당합니다.
- 새 webhook 엔드포인트: `POST /ln-payment/webhook/blink/` (Svix 서명 사용 시 `BLINK_WEBHOOK_SECRET` 환경 변수 필요).
- `transactionsByPaymentHash`를 활용한 백업 조회를 통해 webhook 누락 시에도 입금 정보를 수집합니다.
- 밋업 결제는 `meetup/views_paid.py`의 워크플로우 엔드포인트를 통해 동일한 상태 머신을 재사용하며, `PaymentTransaction.meetup_order`로 참가 예약을 추적합니다.
- 디지털 파일 결제는 `file/views.py`의 워크플로우 엔드포인트를 통해 동일 로직을 재사용하며, `PaymentTransaction.file_order`로 다운로드 권한 부여 상태를 추적합니다.

#### 프런트엔드 흐름
- `orders/templates/orders/checkout.html`은 사용자가 결제 절차를 시작하도록 CTA만 강조하고 `ln_payment:payment_process`로 이동시킵니다.
- `ln_payment/templates/ln_payment/payment_process.html`에서 5단계 진행 UI와 인보이스, 단계 로그, 스토어 연락처 안내를 제공합니다.
- `static/ln_payment/js/payment_workflow.js`는 인보이스 재생성·취소·타이머·상태 폴링을 처리합니다.
- `static/ln_payment/js/payment_process.js`와 `static/ln_payment/css/payment_process.css`는 접근성/스크롤 보조, 상태 배너, 다크 모드 스타일을 담당합니다.
- 결제 실패 시 상태 배너와 스토어 연락처 안내로 재시도/문의 경로를 제공합니다.
- 재고 부족 안내 시 상태 배너와 CTA 전환으로 상품 상세 화면에서 재고를 다시 확인하도록 유도합니다.
- 모바일 화면에서는 `lightning:` 스킴을 사용하는 “지갑 열기” 버튼을 노출해 지갑 앱으로 즉시 이동할 수 있습니다.
- 진행 로그는 단계 이름·시간과 함께 사용자 친화 문구로 갱신되어 결제 흐름을 직관적으로 파악할 수 있습니다.
- Django Admin에는 주문을 수동으로 저장한 결제 트랜잭션만 모아서 확인하는 전용 메뉴가 추가되었습니다.
- 라이브 강의 결제 트랜잭션을 수동으로 복구할 때는 이미 확정된 주문을 자동 병합하고 중복 주문을 취소해 `unique_active_live_lecture_order_per_user` 제약 오류를 방지하며, 병합 결과는 단계 로그와 메타데이터에 기록됩니다.
- 밋업 결제 화면(`meetup/templates/meetup/meetup_checkout.html`) 역시 동일한 5단계 UI와 `static/js/meetup_payment_workflow.js`, `static/css/meetup_checkout.css`를 사용해 참가 예약부터 확정까지 흐름을 안내합니다.
- 디지털 파일 결제 화면(`file/templates/file/file_checkout.html`)도 5단계 UI와 `static/js/file_payment_workflow.js`, `static/css/file_checkout.css`를 사용해 인보이스 발행부터 다운로드 권한 확정까지 안내합니다.

#### 운영 시 유의 사항
- Blink Dashboard에서 webhook 엔드포인트를 `/ln-payment/webhook/blink/`로 등록하고, 시그니처 검증을 위해 `BLINK_WEBHOOK_SECRET`을 설정하세요.
- WebSocket을 사용하지 않는 환경에서도 폴링 기반으로 동작하지만, 필요 시 `svix` 패키지를 설치하면 서명 검증이 강화됩니다.
- soft-lock 만료 처리는 결제 시작 시 자동으로 정리됩니다. 장기간 미사용 데이터를 주기적으로 확인하려면 관리 명령을 추가로 구성하세요.
- 결제 완료 후 추가 상태 조회가 반복되어도 트랜잭션 단계가 3단계(사용자 결제 확인)로 되돌아가지 않습니다.

환경 변수 예시:
```env
# Blink webhook signature 검증
BLINK_WEBHOOK_SECRET=whsec_xxxxxxxxxx
```

## 🚀 배포

### 배포 환경 구성

SatoShop은 **개발(dev)과 운영(main) 환경을 분리**하여 안전한 배포를 진행합니다.

- **개발 환경**: `dev` 브랜치 → 개발 서버 (테스트용)
- **운영 환경**: `main` 브랜치 → 운영 서버 (실제 서비스)

### Git 브랜치 전략

```
main (운영) ← PR ← dev (개발) ← 로컬 작업
```

1. **로컬 개발**: `dev` 브랜치에서 작업
2. **개발 배포**: `dev` 브랜치 푸시 → 자동 배포
3. **운영 배포**: dev에서 테스트 완료 후 `dev` → `main` PR

#### 환경별 환경 변수 설정

**개발 환경 (satoshop-dev)**
```env
DEBUG=True
ENVIRONMENT=development
```

**운영 환경 (satoshop-prod)**
```env
DEBUG=False
ENVIRONMENT=production
SECURE_SSL_REDIRECT=True
```

#### Cron Job 설정

**외부 서버 활용 환율 자동 업데이트**
- "New Cron Job" 생성
- 명령어: `uv run python manage.py update_exchange_rate`
- 스케줄: `*/10 * * * *` (10분마다)

**텔레그램 알림 테스트**
- 텔레그램 봇 설정 후 연결 테스트 필요
- 명령어: `uv run python manage.py test_telegram_bot`
- 환율 업데이트 시 자동으로 텔레그램 알림 전송


## 🔧 관리자 기능

### 사이트 설정 관리

관리자 패널(`/admin/`)에서 다음 기능들을 관리할 수 있습니다:

#### 기본 설정
- **사이트 제목 및 설명**: 메타 태그 및 홈페이지 표시
- **히어로 섹션**: 홈페이지 메인 섹션 제목/부제목
- **유튜브 비디오**: 홈페이지 배경 비디오 설정

#### 환율 관리
- **자동 업데이트 간격**: 업비트 API 호출 주기 설정 (기본 5분)
- **수동 환율 업데이트**: 관리자 패널에서 즉시 환율 업데이트
- **환율 변화 추적**: 환율 변동 내역 및 통계 확인

#### 기능 제어
- **회원가입 허용/차단**: 새 사용자 등록 제어
- **스토어 생성 허용/차단**: 새 스토어 개설 제어

#### 테스트 주문 기본값
- **수퍼어드민 결제 테스트 기본 배송 정보**: 관리자 설정에서 주문자 이름, 연락처, 주소, 배송 메모를 미리 입력해두면 수퍼어드민 계정으로 상품 결제 플로우를 점검할 때 배송 정보 입력 폼이 자동으로 채워져 빠르게 테스트할 수 있습니다.

#### 환율 알림 설정
- **텔레그램 실시간 알림**: 환율 업데이트 시 텔레그램으로 즉시 알림
- **Gmail 요약 이메일**: 1시간마다 최근 환율 변동 요약 이메일 전송

##### 텔레그램 환율 알림 설정:
- **텔레그램 봇 토큰**: BotFather에서 생성한 봇 API 토큰
- **텔레그램 채팅 ID**: 알림을 받을 개인 또는 그룹 채팅 ID
- **즉시 알림 활성화**: 환율 업데이트 시 실시간 텔레그램 알림

**텔레그램 봇 설정 방법:**
1. **봇 생성**: 텔레그램에서 @BotFather에게 `/newbot` 명령어로 봇 생성
2. **봇 토큰 복사**: BotFather가 제공하는 API 토큰을 사이트 설정에 입력
3. **채팅 ID 확인**: 
   - 개인: @userinfobot에게 메시지 보내서 ID 확인
   - 그룹: 봇을 그룹에 추가 후 `/start` 명령어로 그룹 ID 확인
4. **테스트**: `uv run python manage.py test_telegram_bot` 명령어로 연결 확인

##### Gmail 환율 요약 이메일 설정:
- **Gmail 계정**: 환경 변수에 Gmail 계정 설정
- **앱 비밀번호**: 2단계 인증 후 생성한 앱 전용 비밀번호 사용
- **수신 이메일**: 사이트 설정에서 알림 받을 이메일 주소 설정

#### Expert 계약 이메일 & 채팅
- **서명 자산 S3 저장**: `DirectContractDocument`의 자필 서명 이미지는 S3 호환 오브젝트 스토리지(`expert/contracts/signatures/…`)에 업로드되어야 하며, 프로덕션에서는 `EXPERT_SIGNATURE_MEDIA_FALLBACK=False`로 설정해 로컬 저장을 차단하세요.
- **실시간 채팅**: `/expert/contracts/<UUID>/` 페이지에서 웹소켓 기반 실시간 채팅을 제공합니다. 프로덕션 환경에서는 `CHANNEL_REDIS_URL` 환경 변수를 Redis 연결 문자열로 설정해 주십시오. (미설정 시 개발 편의용 In-Memory 채널 레이어가 사용됩니다.)
- **채팅 PDF 아카이브**: 계약 채팅 로그는 ReportLab 기반 PDF로 아카이브되며, 관리자 패널에서 `채팅 로그 PDF 생성` 액션으로 수동 생성할 수 있습니다.
- **한글 PDF 폰트**: 기본적으로 ReportLab `HYSMyeongJo-Medium` CID 폰트를 자동 등록해 계약서·채팅 PDF 모두에서 한글이 깨지지 않습니다. 레포의 `expert/fonts/` 폴더(비어 있음)에 `NanumGothic-Regular.ttf` 등 원하는 TTF/OTF를 추가하면 해당 폰트가 최우선으로 사용됩니다.
- **자동 이메일 발송**: 계약 확정 시 첨부 파일과 함께 Gmail을 통해 이메일이 전송됩니다. 관리자 패널 → 사이트 설정 → *Expert 계약 이메일 설정*에서 Gmail 주소와 앱 비밀번호, 발신자 이름을 입력하세요.
  - **Gmail 설정 안내**: ① Google 계정에서 2단계 인증 활성화 → ② “앱 비밀번호” 메뉴에서 16자리 비밀번호 생성 → ③ 어드민에 공백 포함 없이 입력 (예: `abcd efgh ijkl mnop`).
- **새 의존성 설치**: `uv sync`를 실행하여 `channels`와 `reportlab` 패키지를 설치한 뒤 `uv run python manage.py migrate`를 실행해 새 마이그레이션을 적용하세요.

#### Expert 거래 계약서 템플릿
- **마크다운 계약서 관리**: Django 어드민 → Expert → *거래 계약서* 메뉴에서 마크다운(MD) 형식의 계약서를 버전별로 등록할 수 있습니다. 레포지토리의 `expert/contracts/good_faith_private_contract.md` 파일은 신의성실 기반 1:1 거래 계약서 샘플입니다.

#### Expert 계약 결제 정책
- **결제 정책 설정**: Django 어드민 → Expert → *직접 계약 결제 정책*에서 의뢰자/수행자 각각이 부담해야 할 사토시 금액을 입력하고 활성화하세요. 비활성화 시 결제 위젯은 자동으로 패스됩니다.
- **Blink 자격 정보**: `.env` 파일에 `EXPERT_BLINK_API_KEY`, `EXPERT_BLINK_WALLET_ID`(미설정 시 `BLINK_*` 값을 자동 사용), `EXPERT_BLINK_MEMO_PREFIX`를 지정하면 리뷰/초대 화면에서 동일한 월렛으로 인보이스가 발행됩니다.
- **결제 위젯 흐름**: `/expert/contracts/direct/review/<token>/`과 `/expert/contracts/direct/link/<slug>/`의 서명 박스 옆에 라이트닝 결제 카드가 노출되며, 정책에 등록된 금액만큼 결제 완료되어야 `계약서 주소 생성`/`계약 체결` 버튼이 활성화됩니다.
- **만료 & 취소 처리**: 결제 시작 시 60초짜리 인보이스 QR/문자열과 카운트다운이 표시되며, 만료되거나 취소되면 HTMX로 해당 영역만 갱신하고 다시 시작할 수 있습니다. 모바일 접속자는 `lightning:` 링크로 즉시 지갑을 열 수 있습니다.
- **상태 안내**: Blink API polling(1초 간격) 결과에 따라 "결제 확인 중", "완료", "만료" 등 상태 문구가 즉시 업데이트되며, 오류 발생 시 사유를 카드 내부에서 안내합니다.
- **최종본 템플릿 반영**: `good_faith_private_contract.md`에는 실제 체결 시 바로 사용 가능한 최종 조항이 Markdown 문법으로 정리되어 있어 별도 서식 조정 없이도 PDF에 동일한 구조가 반영됩니다.
- **PDF 출력 품질**: ReportLab Platypus 기반 템플릿으로 계약 제목/헤더/강조/인용이 그대로 스타일링되며, 인용문은 표 형태의 박스로 표현됩니다. 긴 문장은 자동 줄바꿈되고, 의뢰자 라이트닝 주소는 숨긴 채 수행자 주소만 노출합니다. 또한 `중개자(시스템)` 서명 해시를 포함해 세 당사자 해시가 모두 동일한 페이지에 출력됩니다.
- **단일 노출 선택**: 계약서를 “노출”로 체크하면 다른 계약서는 자동으로 해제되어, 드래프트 화면에서는 항상 하나의 계약서만 노출됩니다.
- **드래프트 입력 화면**: `/expert/contracts/direct/draft/` 화면에서 계약 조건을 모두 입력하고 즉시 공유 가능한 링크를 생성합니다. 표준 계약서가 등록되지 않은 경우에는 경고 문구가 표시됩니다.
- **수행 내역 & 첨부 관리**: 계약 초안 화면에서 EasyMDE 기반 Markdown 메모 필드로 수행 내역을 최대 1만 자까지 기록하고, PDF를 오브젝트 스토리지(S3)로 직접 업로드하는 첨부 섹션을 제공합니다. 업로드 목록은 즉시 확인하고 제거할 수 있습니다.


## 📁 프로젝트 구조

```
satoshop/
├── 📁 satoshop/              # Django 프로젝트 설정
│   ├── settings.py           # 메인 설정 파일
│   ├── urls.py              # URL 라우팅
│   └── wsgi.py              # WSGI 설정
├── 📁 accounts/             # 사용자 인증 앱
│   ├── models.py            # 사용자 모델 확장
│   ├── views.py             # 로그인/회원가입 뷰
│   └── templates/           # 인증 관련 템플릿
├── 📁 stores/               # 스토어 관리 앱
│   ├── models.py            # 스토어, 스토어이미지 모델
│   ├── views.py             # 스토어 CRUD 뷰
│   ├── decorators.py        # 스토어 권한 데코레이터
│   └── templates/           # 스토어 관련 템플릿
├── 📁 products/             # 상품 관리 앱
│   ├── models.py            # 상품, 상품이미지, 옵션 모델
│   ├── views.py             # 상품 CRUD 뷰
│   ├── admin.py             # 관리자 인터페이스
│   └── templates/           # 상품 관련 템플릿
├── 📁 orders/               # 주문 관리 앱
│   ├── models.py            # 주문, 주문아이템, 인보이스 모델
│   ├── views.py             # 주문 처리 뷰
│   └── templates/           # 주문 관련 템플릿
├── 📁 file/                 # 디지털 파일 판매 앱
│   ├── models.py            # 디지털 파일, 파일 주문 모델
│   ├── views.py             # 파일 판매 관련 뷰
│   └── templates/           # 파일 관련 템플릿
├── 📁 lecture/              # 라이브 강의 앱
│   ├── models.py            # 라이브 강의, 강의 주문 모델
│   ├── views.py             # 강의 관련 뷰
│   └── templates/           # 강의 관련 템플릿
├── 📁 meetup/               # 밋업 앱
│   ├── models.py            # 밋업, 밋업 주문 모델
│   ├── views.py             # 밋업 관련 뷰
│   └── templates/           # 밋업 관련 템플릿
├── 📁 ln_payment/           # 라이트닝 결제 앱
│   ├── blink_service.py     # Blink API 서비스
│   ├── views.py             # 결제 처리 뷰
│   └── templates/           # 결제 관련 템플릿
├── 📁 storage/              # 범용 파일 첨부 및 S3 관리 앱
│   ├── backends.py          # S3 스토리지 백엔드
│   ├── utils.py             # S3 파일 처리 유틸리티
│   └── models.py            # 첨부파일, 임시 업로드 모델
├── 📁 myshop/               # 메인 앱 (홈페이지)
│   ├── models.py            # 사이트 설정, 환율 모델
│   ├── views.py             # 홈페이지 뷰
│   ├── admin.py             # 사이트 설정 관리
│   ├── services.py          # 업비트 API 서비스
│   ├── management/commands/ # 관리 명령어
│   └── templates/           # 메인 템플릿
├── 📁 static/               # 정적 파일
│   ├── css/                 # 스타일시트
│   │   ├── components.css   # 컴포넌트 스타일
│   │   ├── themes.css       # 테마 시스템
│   │   └── pages/           # 페이지별 스타일
│   ├── js/                  # JavaScript 파일
│   │   ├── theme-toggle.js  # 테마 전환
│   │   ├── currency-exchange.js # 환율 변환
│   │   └── product-form.js  # 상품 폼 관리
│   └── admin/               # 관리자 정적 파일
├── 📁 templates/            # 전역 템플릿
├── 📄 requirements.txt      # Python 의존성
├── 📄 pyproject.toml        # 프로젝트 메타데이터
├── 📄 uv.lock              # 의존성 잠금 파일
├── 📄 docker-compose.yml    # Docker 설정
├── 📄 build.sh             # 빌드 스크립트
├── 📄 env.example          # 환경 변수 예제
├── 📄 STATIC_CACHE_GUIDE.md # 정적 파일 캐시 가이드
├── 📄 RENDER_CRON_SETUP.md # Render.com Cron 설정 가이드
├── 📄 DEPLOYMENT_GUIDE.md  # 배포 가이드 (개발/운영 환경 분리)
└── 📄 manage.py            # Django 관리 스크립트
```

### 주요 모델 관계

```python
# 사용자 → 스토어 (1:1)
User ──→ Store

# 스토어 → 상품 (1:N)
Store ──→ Product ──→ ProductImage (1:N)
                 └──→ ProductOption (1:N)

# 스토어 → 디지털 파일 (1:N)
Store ──→ DigitalFile ──→ FileOrder (1:N)

# 스토어 → 라이브 강의 (1:N)
Store ──→ LiveLecture ──→ LiveLectureOrder (1:N)

# 스토어 → 밋업 (1:N)
Store ──→ Meetup ──→ MeetupOrder (1:N)

# 사용자 → 주문 (1:N)
User ──→ Order ──→ OrderItem (1:N)
            └────→ Invoice (1:N)

# 스토어 → 인보이스 (1:N)
Store ──→ Invoice

# 사이트 설정 → 환율 (1:N)
SiteSettings ──→ ExchangeRate
```

## ✅ 수동 테스트 가이드

1. **네비게이션 진입 확인**: 상단 내비게이션과 모바일 메뉴에서 `BAH 홍보요청` 링크가 노출되는지 확인하고 `/stores/bah/promotion-request/`로 이동해 안내 화면과 월오사 가이드 카드가 표시되는지 확인합니다.
2. **라이트닝 인증 전 상태**: 로그아웃 상태에서 `홍보요청 내용 입력하기` 버튼을 누르면 로그인 버튼이 노출되고 저장 버튼이 숨겨져 있는지 확인합니다.
3. **라이트닝 인증 후 제출**: 라이트닝 지갑을 연동한 계정으로 로그인해 폼을 작성하고 이미지를 업로드한 뒤 저장합니다. 저장 완료 후 성공 배너가 나타나고 신라스토어 링크가 노출되는지 확인합니다.
4. **수정 플로우**: 동일 계정으로 페이지를 다시 열어 기존 값이 폼에 채워져 있는지, 이미지 삭제 체크박스가 동작하는지, 수정 저장 시 성공 배너가 `수정되었습니다`로 갱신되는지 확인합니다.
5. **BAH 관리자 전용 화면**: Django Admin에서 지정한 BAH 관리자 계정으로 `/stores/bah/promotion-request/admin`에 접속해 신청 목록이 표시되는지, 발송 상태 토글 버튼으로 `발송예정 ↔ 발송` 전환이 가능한지 확인합니다.
6. **월오사 가이드 페이지**: `/stores/bah/wallet-of-satoshi-guide/`에서 각 섹션을 펼칠 수 있는지, 추가 자료 링크가 정상 동작하는지 확인합니다.
7. **Expert 서명 S3 업로드(생성자)**: 라이트닝 인증 계정으로 `/expert/contracts/direct/draft/` → `/expert/contracts/direct/review/<token>/` 흐름을 진행해 자필 서명 제출 후 S3 버킷(`expert/contracts/signatures/…`)에 파일이 생성되고, 계약 상세 화면에서 서명이 노출되는지 확인합니다.
8. **Expert 서명 S3 업로드(상대방)**: 초대 링크(`/expert/contracts/direct/link/<slug>/`)를 열어 상대방 서명을 완료하고, 공유 페이지 및 이메일에서 서명 이미지가 `get_signature_url()` 기반 링크로 노출되는지 검증합니다.

## ⚠️ 주의사항

### 보안 관련

1. **환경 변수 보안**
   - `.env` 파일을 절대 Git에 커밋하지 마세요
   - 프로덕션에서는 강력한 `SECRET_KEY` 사용
   - 데이터베이스 비밀번호를 안전하게 관리

2. **Blink API 키 보안**
   - API 키는 암호화되어 데이터베이스에 저장됩니다

3. **이미지 핫링크 보호**
   - 외부 사이트에서 이미지 직접 사용을 방지하는 Referer 헤더 검증 기능
   - 환경변수로 활성화/비활성화 및 허용 도메인 설정 가능

4. **HTTPS 사용**
   - 프로덕션에서는 반드시 HTTPS 사용
   - SSL 인증서 설정 필수

### 성능 관련

1. **데이터베이스 최적화**
   - 인덱스가 적절히 설정되어 있는지 확인
   - 대용량 데이터 처리 시 페이지네이션 사용

2. **이미지 최적화**
   - 업로드 이미지 크기 제한 (현재 10MB)
   - CDN 사용 권장

3. **캐싱**
   - 정적 파일 해시 기반 캐싱 활용
   - 환율 데이터 캐싱으로 API 호출 최소화

### 라이트닝 네트워크 관련

1. **블링크 API 사용**
   - 블링크 API를 사용하여 개발
   - 개발/운영 환경별로 다른 API 키 사용 권장
   - 테스트를 위해서는 블링크 계정 및 API 정보 필요

2. **결제 확인**
   - 결제 상태 확인 로직의 안정성 검증
   - 네트워크 오류 시 재시도 로직 구현

3. **지갑 호환성**
   - 다양한 라이트닝 지갑과의 호환성 테스트
   - QR 코드 형식 표준 준수

### 배포 관련

1. **환경 분리**
   - 개발(dev)과 운영(main) 환경 완전 분리
   - 각 환경별 독립적인 데이터베이스 사용
   - 환경별 다른 도메인 및 설정 적용

### 데이터 마이그레이션

1. **상품 카테고리 스키마 반영**
   - 상품 카테고리 기능 도입(2025-10) 이후 코드 업데이트 시 `uv run python manage.py migrate` 명령을 반드시 실행하세요.
   - 마이그레이션은 스토어별 기본 카테고리(“카테고리 없음”)를 생성하고 기존 상품을 자동으로 해당 카테고리에 매핑합니다.

### 수동 테스트 체크리스트 (상품 카테고리)

1. `uv run python manage.py migrate` 실행 후 관리자 계정으로 로그인합니다.
2. 스토어 관리 메뉴에서 **카테고리 관리** 화면으로 이동해 새 카테고리 생성, 이름 수정, 삭제, 순서 변경(위/아래 버튼)을 각각 확인합니다.
3. `/products/<store_id>/list/` 페이지에서 카테고리 로그인을 확인하고, 새로 생성한 카테고리로 상품을 등록·수정하여 섹션 배치가 즉시 반영되는지 검증합니다.
4. 공개 보기와 관리자 보기 모두에서 카테고리 네비게이션(상단 필터)과 섹션별 상품 카드가 정상적으로 노출되는지 확인합니다.

### 수동 테스트 체크리스트 (라이브 강의 수동 복구)

1. 동일 사용자·강의 조합으로 하나의 `LiveLectureOrder`를 `confirmed` 상태로 두고, 다른 주문은 `pending` 상태로 유지합니다. (관리자에서 상태를 조정하거나 테스트 결제 플로우를 통해 생성)
2. `PaymentTransaction` 상세 화면에서 `pending` 주문과 연결된 라이브 강의 결제 건을 열고 `참가 확정하기`를 클릭합니다.
3. 화면이 오류 없이 완료되고 `PaymentStageLog`의 `ORDER_FINALIZE` 단계에 `merged_existing_order: true`와 `cancelled_duplicate_order_id` 정보가 기록되는지 확인합니다.
4. Django Admin의 `LiveLectureOrder` 목록을 확인해 `pending`이던 주문이 `cancelled`로 전환되고, 기존 확정 주문에 최신 결제 정보가 병합됐는지 검증합니다.

2. **브랜치 관리**
   - main 브랜치는 운영 배포용으로만 사용
   - dev 브랜치에서 모든 개발 및 테스트 진행
   - PR을 통한 코드 리뷰 후 운영 배포

3. **자동 배포**
   - 브랜치별 자동 배포 설정
   - 배포 실패 시 롤백 절차 준비

### 환율 관리

1. **업비트 API 의존성**
   - 업비트 API 장애 시 환율 업데이트 불가
   - 백업 환율 소스 고려 필요

2. **환율 업데이트 주기**
   - 너무 짧은 주기는 API 제한에 걸릴 수 있음
   - 기본 10분 주기 권장

## ⚡ 개발자에게 기부하기

이 프로젝트가 도움이 되셨다면, 개발자에게 기부를 통해 지원해주세요.

**라이트닝 네트워크 주소**: `nextmoney@walletofsatoshi.com`

여러분의 소중한 후원은 프로젝트의 지속적인 개발과 개선에 큰 도움이 됩니다. 감사합니다! 🙏


## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

```
MIT License

Copyright (c) 2024 SatoShop

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 📞 연락처

- **프로젝트 관리자**: [GitHub 프로필](https://github.com/my3rdstory)
- **엑스 계정**: [엑스 프로필](https://x.com/_orangepillkr)

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들의 도움을 받았습니다:

- [Django](https://www.djangoproject.com/) - 웹 프레임워크
- [Tailwind CSS](https://tailwindcss.com/) - CSS 프레임워크
- [Font Awesome](https://fontawesome.com/) - 아이콘
- [qrcode](https://github.com/lincolnloop/python-qrcode) - QR 코드 생성
- [Blink](https://www.blink.sv/) - 라이트닝 네트워크 API
- [EasyMDE](https://github.com/Ionaru/easy-markdown-editor) - 마크다운 에디터
- [Django APScheduler](https://github.com/jcass77/django-apscheduler) - 작업 스케줄러

---

**⚡ 비트코인 라이트닝 네트워크로 더 빠르고 저렴한 전자상거래를 경험해보세요!**
