# SatoShop

비트코인 라이트닝 결제를 중심으로 스토어 운영, 디지털 판매, 오프라인 이벤트 접수, 미니홈 홍보 페이지, 외부 API 연동, Discord 운영 자동화까지 묶은 Django 기반 플랫폼입니다.

이 문서는 2026-03-31 기준 현재 코드베이스를 직접 분석해 다시 정리한 최신 README입니다.

## 한눈에 보기

- 전자상거래 코어: 스토어, 상품, 장바구니, 주문, 배송, Blink 라이트닝 결제
- 판매 확장 기능: 메뉴판, 밋업, 라이브 강의, 디지털 파일 판매
- 인증 체계: 일반 로그인, LNURL-auth 라이트닝 로그인, Nostr 로그인(NIP-07/NIP-46), 라이트닝 계정의 일반 로그인 전환
- 운영/콘텐츠: 공지, 밈 게시판, 명예의 전당, 후기, 문서 페이지, 환율/텔레그램 알림
- 프로모션/랜딩: 미니홈, BAH 홍보 요청, Discord 봇 알림 및 슬래시 명령어
- B2B 실험 영역: Expert 계약 초안, 결제 위젯, PDF/무결성 검증, 실시간 계약 채팅
- 외부 연동: 공개 API, Bearer API 키 인증, Nostr 서명 기반 API 인증, S3 호환 오브젝트 스토리지
- 배포/실행: Django 5.2, PostgreSQL, WhiteNoise, Channels, uv, Docker, Render

## 현재 시스템 맵

| 시스템 | 관련 앱 | 설명 |
| --- | --- | --- |
| 코어 스토어 | `stores`, `products`, `orders`, `ln_payment` | 스토어 생성, 상품 판매, 장바구니, 주문, 배송, 결제 상태 추적 |
| 판매 포맷 확장 | `menu`, `meetup`, `lecture`, `file`, `reviews` | 메뉴판, 밋업, 라이브 강의, 디지털 파일, 상품 후기 |
| 사용자/인증 | `accounts` | 회원가입, 일반 로그인, LNURL-auth, Nostr 로그인, 계정 연결 |
| 사이트 코어 | `myshop` | 메인 랜딩, 환율, 사이트 설정, 문서 페이지, PWA 진입점 |
| 미니홈/프로모션 | `minihome`, `stores` | 홍보용 랜딩, 도메인 매핑, BAH 홍보 요청 |
| 커뮤니티 | `boards` | 공지, 댓글, 밈 게시판, 명예의 전당 |
| 외부 API | `api` | 스토어/상품/밋업/강의/파일 조회, 주문 생성, 라이트닝 인보이스 발행 |
| 파일 저장소 | `storage` | S3 호환 스토리지 백엔드, 업로드 세션, 보안 프록시 서빙 |
| 운영 봇 | `satoshop_bot` | Discord 인터랙션, 웹뷰, 슬래시 명령 동기화 |
| Expert 영역 | `expert` | 계약 초안, 결제 위젯, PDF, 무결성 검증, WebSocket 채팅 |
| 부가 기능 | `game`, `minihome`, `boards` | 미니게임, 랜딩 운영, 커뮤니티 기능 |

## 아키텍처

### 1. 애플리케이션 계층

```text
브라우저 / 모바일 웹
  ├─ Django 템플릿 + Tailwind + 앱별 JS/CSS
  ├─ PWA 리소스(sw.js, manifest.json)
  └─ 일부 실시간 기능(Expert 채팅)은 WebSocket 사용

Django 애플리케이션
  ├─ 앱별 View / Form / Service / Model
  ├─ 세션 기반 웹 기능 + JSON API 혼합
  ├─ 결제 상태/재고 예약/주문 생성 서비스
  ├─ Nostr/LNURL 인증 로직
  └─ 관리자(Admin) 중심 운영 설정

데이터/인프라
  ├─ PostgreSQL
  ├─ S3 호환 오브젝트 스토리지
  ├─ WhiteNoise 정적 파일 서빙
  ├─ Channels(선택적으로 Redis 연계)
  └─ 외부 웹훅/크론/수동 명령 기반 운영 작업

외부 서비스
  ├─ Blink GraphQL API / Blink webhook
  ├─ Upbit API
  ├─ Gmail SMTP
  ├─ Telegram Bot API
  └─ Discord Interactions API
```

### 2. 요청 흐름 요약

#### 판매/결제 흐름

1. 판매자가 스토어를 만들고 Blink API 자격 정보를 저장합니다.
2. 구매자는 상품, 메뉴, 밋업, 강의, 디지털 파일 중 하나를 선택합니다.
3. `ln_payment` 서비스 계층이 결제 트랜잭션과 재고/좌석 예약을 생성합니다.
4. Blink 인보이스를 발행하고 QR 또는 payment request를 사용자에게 보여줍니다.
5. 결제 확인은 폴링과 Blink webhook을 함께 사용합니다.
6. 결제가 확인되면 주문 또는 참여 신청이 확정되고 운영 화면에서 추적 가능합니다.

#### 인증 흐름

- 웹 로그인: Django 기본 세션 인증
- 라이트닝 로그인: LNURL-auth 챌린지 생성, 서명 검증, 계정 연결
- Nostr 로그인: NIP-07 우선, 확장 미존재 시 NIP-46(Nostr Connect) 폴백
- 외부 API 인증: Bearer API 키 또는 Nostr 공개키 기반 서명 인증

#### 배경 작업 전략

현재 코드는 내장 스케줄러 중심이 아니라 아래 방식으로 운영됩니다.

- Django 관리 명령 수동 실행
- 외부 크론에서 관리 명령 호출
- 웹훅 호출
- 모델 저장 시 알림 후처리

즉, 예전 README에 있던 APScheduler 중심 설명은 현재 구조와 맞지 않습니다.

### 3. 실시간/비동기 요소

- `channels`가 설치되어 있고 ASGI 엔트리포인트가 구성되어 있습니다.
- 현재 WebSocket 사용 지점은 `expert` 계약 채팅입니다.
- 설정상 `CHANNEL_REDIS_URL` 또는 `REDIS_URL`을 통한 Redis 채널 레이어 분기가 있지만, 현재 잠금 의존성에는 `channels-redis`가 포함되어 있지 않아 기본 동작은 인메모리 레이어 기준입니다.

## 앱별 역할

### `accounts`

- 회원가입, 로그인, 로그아웃, 마이페이지
- LNURL-auth 라이트닝 로그인 및 지갑 연동
- Nostr 로그인 챌린지 생성/검증/복구 세션 처리
- 라이트닝 계정의 일반 로그인 전환
- 구매 내역 조회

### `stores`

- 스토어 생성 마법사와 관리 화면
- 스토어 테마, 이미지, 이메일, 배송, 완료 메시지, 대표 노출 순서 관리
- BAH 홍보 요청과 관리자 화면

### `products`

- 일반 상품 CRUD
- 상품 카테고리 관리 및 대량 매칭
- 옵션, 이미지, 완료 메시지, 품절/활성 상태 관리

### `orders`

- 장바구니
- 체크아웃
- 주문/주문 아이템/인보이스
- 배송 상태 변경, 송장 입력, CSV 추출
- 결제 트랜잭션 조회 및 주문 복구

### `ln_payment`

- Blink API 연동
- 5단계 결제 워크플로우 서비스
- 결제 단계 로그와 재고 soft-lock 예약
- Blink webhook 수신

### `menu`

- 메뉴판 전용 카테고리/옵션/이미지 관리
- 데스크톱/모바일 메뉴판 분기
- 메뉴 장바구니와 결제

### `meetup`

- 밋업 개설, 좌석/옵션 관리
- 무료/유료 접수 흐름
- 임시 예약 정리
- QR 기반 참석 확인

### `lecture`

- 라이브 강의 개설/신청/참가자 관리
- 강의별 결제 워크플로우
- 참가 내역 및 CSV 추출

### `file`

- 디지털 파일 판매
- 다운로드 제한/로그
- 파일별 결제 및 주문 관리

### `minihome`

- 브랜드/프로젝트 소개용 미니홈 랜딩
- 공개/미리보기/관리 화면
- 커스텀 도메인 및 목록 전용 도메인 지원

### `api`

- 외부 소비자를 위한 스토어 피드/API 문서
- Bearer 및 Nostr 인증
- 스토어 단위 주문 생성, 라이트닝 인보이스 발행/확정

### `satoshop_bot`

- Discord 인터랙션 엔드포인트
- 최근 등록/판매 상품 웹뷰
- 슬래시 명령 동기화 명령 제공

### `expert`

- 계약 초안/리뷰/공유 링크
- Expert 전용 Blink 결제 위젯
- PDF 생성 및 무결성 검증
- 계약 참여자 간 실시간 채팅

### `myshop`

- 메인 랜딩과 환율 API
- 사이트 전역 설정
- 문서 페이지, 오프라인 페이지
- PWA용 `manifest.json`, `sw.js`

### `boards`

- 공지사항, 댓글
- 밈 게시판
- 명예의 전당

### `storage`

- S3 호환 스토리지 백엔드
- 첨부 파일/임시 업로드/업로드 세션 관리
- 미디어 프록시 서빙과 핫링크 보호

## 기술 스택

### 백엔드

- Python 3.13
- Django 5.2.2
- PostgreSQL
- Channels
- Gunicorn
- WhiteNoise
- uv

### 프런트엔드

- Django Template
- Tailwind CSS
- 앱별 정적 JS/CSS
- PWA 리소스(`manifest.json`, `sw.js`)

### 결제/인증/연동

- Blink GraphQL API
- LNURL-auth
- Nostr(NIP-07, NIP-46)
- Gmail SMTP
- Telegram Bot API
- Discord Interactions API
- Upbit BTC/KRW 환율

### 파일/문서 처리

- boto3 / django-storages
- Pillow
- FPDF2
- PyPDF
- PyHanko

## 로컬 개발 빠른 시작

### 요구 사항

- Python 3.13 이상
- uv
- PostgreSQL 15 이상
- Docker / Docker Compose 선택 사항

### 1. 저장소 준비

```bash
git clone <저장소 URL>
cd satoshop-dev
uv sync
```

### 2. 로컬 PostgreSQL 실행

기본 개발용 `docker-compose.yml`은 PostgreSQL을 `127.0.0.1:5434`에 띄웁니다.

```bash
docker compose up -d postgres
```

### 3. 환경 변수 파일 생성

설정은 로컬에서 `.env.local`을 우선 로드하고, 없으면 `.env`를 봅니다.

최소 예시는 아래 기준으로 시작하면 됩니다.

```env
SECRET_KEY=로컬용_임의값
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=satoshop-main
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=127.0.0.1
DB_PORT=5434
```

Blink, S3, 이메일, Telegram, Discord는 해당 기능을 쓸 때만 추가하면 됩니다.

### 4. 데이터베이스 반영

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

### 5. 개발 서버 실행

이 프로젝트는 `runserver` 기본 포트를 `8011`로 오버라이드했습니다.

```bash
uv run python manage.py runserver
```

실행 후 기본 진입점:

- 홈: `http://127.0.0.1:8011/`
- 관리자: `http://127.0.0.1:8011/admin/`
- API 문서: `http://127.0.0.1:8011/api/v1/docs/`
- Expert: `http://127.0.0.1:8011/expert/`
- Minihome 목록: `http://127.0.0.1:8011/minihome/`

## 환경 변수 가이드

### 필수

| 변수 | 설명 |
| --- | --- |
| `SECRET_KEY` | Django 시크릿 키 |
| `DEBUG` | 개발 여부 |
| `DB_NAME` `DB_USER` `DB_PASSWORD` `DB_HOST` `DB_PORT` | PostgreSQL 연결 |
| `ALLOWED_HOSTS` | 배포 호스트 허용 목록 |

### 스토어 결제 기능

| 변수 | 설명 |
| --- | --- |
| `BLINK_API_KEY` | 기본 Blink API 키 |
| `BLINK_WALLET_ID` | 기본 Blink 월렛 ID |

스토어별 개별 Blink 자격 정보는 관리 화면에서 별도로 저장할 수 있습니다.

### Expert 기능

| 변수 | 설명 |
| --- | --- |
| `EXPERT_BLINK_API_KEY` | Expert 전용 Blink API 키 |
| `EXPERT_BLINK_WALLET_ID` | Expert 전용 Blink 월렛 ID |
| `EXPERT_BLINK_MEMO_PREFIX` | Expert 결제 메모 prefix |
| `EXPERT_SIGNER_CERT_PATH` | 서명 인증서 파일 경로 |
| `EXPERT_SIGNER_CERT_BASE64` | 인증서 base64 |
| `EXPERT_SIGNER_CERT_PASSWORD` | 인증서 비밀번호 |

### 파일 저장소

| 변수 | 설명 |
| --- | --- |
| `S3_ACCESS_KEY_ID` | 스토리지 접근 키 |
| `S3_SECRET_ACCESS_KEY` | 스토리지 시크릿 |
| `S3_BUCKET_NAME` | 버킷 이름 |
| `S3_ENDPOINT_URL` | S3 호환 엔드포인트 |
| `S3_REGION_NAME` | 리전 |
| `S3_USE_SSL` | SSL 사용 여부 |
| `S3_FILE_OVERWRITE` | 동일 이름 덮어쓰기 허용 여부 |
| `S3_CUSTOM_DOMAIN` | 커스텀 미디어 도메인 |

이 값들이 모두 있으면 `storage.backends.S3Storage`를 사용하고, 없으면 로컬 파일 저장소로 동작합니다.

### 인증/네트워크/도메인

| 변수 | 설명 |
| --- | --- |
| `LNURL_AUTH_ROOT_DOMAIN` | LNURL-auth 기준 도메인 |
| `LNURL_DOMAIN` | 구버전 호환용 도메인 변수 |
| `CHANNEL_REDIS_URL` 또는 `REDIS_URL` | Redis 채널 레이어 확장 시 사용할 값. 현재는 `channels-redis` 추가 설치가 필요 |
| `MINIHOME_LIST_DOMAIN` | 미니홈 목록 전용 도메인 |
| `NGROK_DOMAIN` | 개발 시 외부 접속 호스트 허용 |
| `CSRF_TRUSTED_ORIGINS` | 신뢰할 Origin 목록 |

운영 기본 캐시는 Gunicorn 워커 간 LNURL/Nostr 인증 상태를 공유하기 위해 파일 기반(`.django_cache`)으로 동작합니다. 여러 인스턴스로 확장할 경우에는 Redis 같은 외부 공유 캐시로 전환해야 합니다.

### 운영 알림/메일

| 변수 | 설명 |
| --- | --- |
| `EMAIL_HOST_USER` | Gmail SMTP 계정 |
| `EMAIL_HOST_PASSWORD` | Gmail SMTP 비밀번호 또는 앱 비밀번호 |
| `DEFAULT_FROM_EMAIL` | 기본 발신 주소 |
| `WEBHOOK_TOKEN` | 환율 갱신 웹훅 보호 토큰 |
| `HOTLINK_PROTECTION_ENABLED` | 핫링크 보호 사용 여부 |
| `HOTLINK_ALLOWED_DOMAINS` | 미디어 접근 허용 도메인 |

### 배포/런타임

| 변수 | 설명 |
| --- | --- |
| `RUN_MIGRATIONS` | 컨테이너 시작 시 마이그레이션 실행 |
| `RUN_COLLECTSTATIC` | 컨테이너 시작 시 collectstatic 실행 |
| `RUN_SYSTEM_CHECK` | 컨테이너 시작 시 `check --deploy` 실행 |
| `PORT` | Gunicorn 바인딩 포트 |
| `GUNICORN_WORKERS` | Gunicorn 워커 수 |
| `GUNICORN_TIMEOUT` | Gunicorn 타임아웃 |

## 설치 후 바로 활용하는 방법

### 1. 관리자 초기 설정

1. `/admin/`에 접속합니다.
2. `myshop.SiteSettings`에서 사이트 제목, 홈 문구, Telegram, 문서 페이지 등을 정리합니다.
3. 필요한 경우 공지, 명예의 전당, 밈 게시판 운영 데이터를 등록합니다.

### 2. 판매자 온보딩

1. 회원가입 후 로그인합니다.
2. `/stores/create/`에서 스토어를 생성합니다.
3. 스토어 관리 화면에서 기본 정보, 테마, 배송, 이메일을 설정합니다.
4. Blink API 키와 월렛 ID를 연결합니다.
5. 상품 또는 메뉴/밋업/강의/디지털 파일 중 필요한 판매 포맷을 추가합니다.

### 3. 구매 흐름 확인

1. 공개 스토어 페이지 또는 상품 상세 페이지에 접속합니다.
2. 장바구니 또는 직접 결제 흐름을 진행합니다.
3. Blink 인보이스가 생성되면 QR 또는 payment request로 결제합니다.
4. 주문/참가/다운로드 완료 페이지에서 결과를 확인합니다.

### 4. Minihome 활용

1. Admin에서 `minihome` 항목을 생성합니다.
2. 슬러그와 주인장을 지정합니다.
3. `/minihome/<slug>/mng/`에서 섹션을 편집합니다.
4. 공개 후 `/minihome/<slug>/` 또는 연결한 도메인에서 랜딩을 확인합니다.

### 5. 외부 API 활용

1. Admin에서 API 키를 생성합니다.
2. 필요 시 IP 허용 목록과 Origin 허용 목록을 설정합니다.
3. `/api/v1/docs/`를 확인합니다.
4. Bearer 인증 또는 Nostr 서명 인증으로 스토어/상품/주문 API를 사용합니다.

### 6. Discord 봇 활용

1. Admin에서 DiscordBot 설정을 등록합니다.
2. 인터랙션 엔드포인트를 `/satoshop-bot/discord/interactions/`로 연결합니다.
3. 아래 명령으로 슬래시 명령어를 동기화합니다.

```bash
uv run python manage.py sync_discord_commands --all-guilds
```

## 인증 체계 정리

### 웹 사용자 인증

- Django 세션 로그인
- 라이트닝 LNURL-auth 로그인
- Nostr 로그인
- 라이트닝 계정의 일반 로그인 전환

### 외부 API 인증

#### Bearer API 키

`Authorization: Bearer <raw_api_key>`

#### Nostr 서명 인증

1. `GET /api/v1/nostr/challenge/?pubkey=<hex_or_npub>` 호출
2. 응답의 challenge를 개인키로 서명
3. 아래 헤더와 함께 보호 API 호출

- `X-Nostr-Pubkey`
- `X-Nostr-Challenge-Id`
- `X-Nostr-Signature`

## 운영 명령 모음

### 기본

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py collectstatic --noinput
uv run python manage.py check
```

### 환율/웹훅

```bash
uv run python manage.py update_exchange_rate --force
```

- 업비트 기반 BTC/KRW 환율을 수동 갱신합니다.
- 코드상 환율 자동화는 외부 크론 또는 웹훅 호출 기반입니다.

### 밋업/결제 정리

```bash
uv run python manage.py cleanup_expired_reservations --dry-run
uv run python manage.py expire_invoices --dry-run
```

### 스토리지 유지보수

```bash
uv run python manage.py cleanup_temp_uploads
uv run python manage.py test_hotlink_protection
```

### Discord 명령 동기화

```bash
uv run python manage.py sync_discord_commands --all-guilds
uv run python manage.py sync_discord_commands --global-only
```

## 배포 구조

### 현재 코드 기준 배포 진입점

- `render.yaml`: Render 서비스 정의
- `Dockerfile`: uv 기반 Python 3.13 컨테이너 이미지
- `scripts/docker-entrypoint.sh`: 컨테이너 시작 시 migrate/collectstatic/check 처리

### 컨테이너 기동 방식

기본 실행 명령은 아래와 같습니다.

```bash
uv run gunicorn satoshop.wsgi:application --bind 0.0.0.0:$PORT
```

### 폰트 주의사항

Expert PDF/문서 기능은 한글 폰트를 전제로 합니다.

- 로컬/배포 공통으로 `expert/static/expert/fonts` 경로를 사용합니다.
- Docker 이미지는 `fonts-noto-cjk`를 설치합니다.
- 추가 서명/인감 인증서가 필요하면 `EXPERT_SIGNER_CERT_*` 환경 변수를 사용합니다.

## 프로젝트 구조

```text
satoshop/        Django 설정, URL, ASGI/WSGI
accounts/        로그인, 라이트닝/Nostr 인증, 마이페이지
stores/          스토어 생성/관리, BAH 홍보 요청
products/        일반 상품/카테고리/옵션
orders/          장바구니, 주문, 배송, 인보이스
ln_payment/      Blink 결제 서비스, 결제 단계 로그, webhook
menu/            메뉴판/품절/주문
meetup/          밋업 개설, 참가, 체크인
lecture/         라이브 강의 개설/참가
file/            디지털 파일 판매/다운로드
reviews/         상품 후기
minihome/        홍보용 랜딩/도메인 매핑
api/             외부 연동 API
satoshop_bot/    Discord 연동
expert/          계약/결제/PDF/실시간 채팅
boards/          공지/밈/명예의 전당
storage/         오브젝트 스토리지 백엔드/첨부 관리
myshop/          홈, 환율, 사이트 설정, 공통 뷰
static/          공용 정적 파일
templates/       공용 템플릿
scripts/         배포/운영 스크립트
change-log/      작업 단위 변경 이력
todo.md          현재 작업 기록
```

## 참고 메모

- `docker-compose.yml`은 로컬 개발용 PostgreSQL 구동을 위한 파일입니다.
- 운영 미디어 저장은 S3 호환 스토리지를 전제로 설계되어 있습니다.
- Expert 채팅 외에는 WebSocket 의존도가 높지 않습니다.
- 홈 화면 수치와 환율 정보는 `myshop` 코어에서 집계합니다.
- 정적 파일은 개발 환경에서는 no-cache, 운영 환경에서는 manifest 기반 해시 캐싱으로 처리합니다.

## 수동 검증 체크리스트

자동 테스트는 여기서 실행하지 않았습니다. README를 반영한 뒤 아래 순서로 대장께서 확인하면 됩니다.

1. `uv sync`
2. `docker compose up -d postgres`
3. `.env.local` 작성
4. `uv run python manage.py migrate`
5. `uv run python manage.py runserver`
6. `/`, `/admin/`, `/api/v1/docs/`, `/accounts/login/`, `/expert/`, `/minihome/` 접근 확인
7. Blink/S3를 설정했다면 스토어 생성 후 상품 등록과 인보이스 생성 확인
