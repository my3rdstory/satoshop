# Project Context

## Purpose
SatoShop은 다중 상점(스토어) 운영자를 위한 비트코인 라이트닝 네트워크 기반 전자상거래 플랫폼이다. 상점주는 Blink API와 연동해 초저비용 BTC 결제를 제공하고, 메뉴·상품·파일·강의·모임 등 다양한 디지털/실물 상품을 판매할 수 있다. 실시간 환율·텔레그램 알림·서명 기반 계약 등 부가 워크플로도 포함되어 비개발자도 빠르게 상점을 개설할 수 있도록 돕는다.

## Tech Stack
- **Backend**: Python 3.13+, Django 5.2, Django Channels(WebSocket 및 실시간), Django APScheduler(주기 작업), Gunicorn(WSGI), WhiteNoise(정적 서빙)
- **Data & Storage**: PostgreSQL(주 데이터베이스), Django ORM, Django-Storages+boto3를 통한 S3 호환 오브젝트 스토리지, ReportLab/Pillow(문서·이미지 처리)
- **Frontend**: Django Templates, HTML5, Vanilla JS(ES6+), Tailwind CSS(기본 text-sm), Font Awesome, EasyMDE(마크다운 에디터)
- **Tooling**: uv(패키지+런처), docker-compose(Postgres 로컬), openspec(변경 관리), cryptography/qrcode/bleach/markdown 등 보조 라이브러리
- **Infrastructure**: Render.com(앱/DB 호스팅), Docker(선택적 로컬), APScheduler/cron으로 주기 작업 실행

## Project Conventions

### Code Style
- Python 전반은 PEP 8, 4칸 들여쓰기, `PascalCase` 클래스·`snake_case` 함수/변수 네이밍을 따른다.
- Django 템플릿은 Tailwind 유틸리티 클래스를 기본으로 사용하고 기본 폰트 크기는 `text-sm`이다.
- 각 템플릿(view)에서 쓰는 JS·CSS는 동일한 파일명을 가진 정적 자산을 `static/<app>/<css|js>/`에 생성한다.
- 토스트/알림 라이브러리는 사용하지 않고, 다크모드 토글을 모든 화면에 제공한다.
- 비밀 값은 `.env` 계열 파일을 통해 주입하며 레포에 커밋하지 않는다.

### Architecture Patterns
- 전형적인 멀티 앱 Django 구조로, `accounts`, `stores`, `products`, `orders`, `ln_payment`, `file`, `lecture`, `meetup`, `menu`, `reviews`, `myshop` 등 도메인별 앱이 명확히 책임을 나눈다.
- Blink 라이트닝 결제, 환율 업데이트, 텔레그램 알림 등 외부 연동은 서비스/헬퍼 모듈(`ln_payment/blink_service.py`, `myshop/services.py`, `storage/utils.py`)로 캡슐화한다.
- 정적 자산은 글로벌 `static/`과 앱별 템플릿에서 로드하며, WhiteNoise와 Tailwind Utility 기반 디자인을 전제한다.
- 주기 처리·자동화는 Django APScheduler 및 `myshop.management.commands`의 커맨드로 관리한다.
- 데이터 모델은 사용자→스토어→상품/주문 구조를 중심으로 하고, 서명/계약/환율 같은 부가 모델은 별도 앱에 위치한다.

### Testing Strategy
- 대장은 수동 테스트를 수행하므로 자동 테스트 실행 대신 재현 절차를 문서화한다.
- 필요한 경우 `uv run python manage.py test` 또는 앱 단위(`uv run python manage.py test products`) 명령으로 실행한다.
- 환율/텔레그램/결제 등 외부 API 연동은 샌드박스 키로 스테이징 검증 후 실제 키를 별도 환경 변수로 주입한다.
- 수동 체크리스트는 `README.md`의 “수동 테스트 가이드” 섹션을 참고하고, 새 기능은 동일한 형식으로 테스트 플로우를 갱신한다.

### Git Workflow
- 모든 개발은 `dev` 브랜치를 기반으로 진행하며, 기능별 브랜치를 생성해 작업 후 `dev`에 병합한다.
- 프로덕션 반영은 `dev`에서 충분히 검증한 뒤 `main`으로 PR을 열고 코드 리뷰 후 머지한다.
- 커밋 메시지는 한국어 한 줄 요약을 사용하고, 관련 이슈/작업 단위를 명확히 구분한다.
- 대규모 작업을 시작할 때는 루트의 `todo.md`에 진행 중인 항목을 기록·업데이트한다.

## Domain Context
- **스토어 운영**: 사용자마다 고유 스토어를 생성해 테마/연락처/이미지/활성화 상태를 설정한다.
- **상품·메뉴·콘텐츠 판매**: 실물 상품, 레스토랑 메뉴, 디지털 파일, 라이브 강의, 밋업 티켓 등 여러 앱을 통해 다양한 판매 워크플로를 제공한다.
- **주문/인보이스**: 주문, 장바구니, 인보이스, 수동 주문 복구, 계약 흐름(서명, PDF 보관) 등을 관리한다.
- **결제**: Blink API 기반 라이트닝 인보이스 생성·조회, QR 코드, 실시간 결제 상태 추적, 환율 변환(Upbit) 및 요약 알림(텔레그램)을 제공한다.
- **관리 자동화**: 환율 스케줄링, 이메일/텔레그램 알림, 계약 서명 흐름, Dark mode UI, 카테고리 일괄 매핑 등 다채로운 관리 도구를 포함한다.

## Important Constraints
- Django 관리 명령이나 서버 실행은 항상 `uv run python manage.py ...` 형식으로 호출한다.
- 템플릿을 신설할 때 동일 이름의 JS/CSS 자산을 `static/`에 만들고, Tailwind 및 다크모드 대응을 빠뜨리지 않는다.
- 토스트 메시지·3rd-party 팝업 UI 금지, 접근성·모바일 대응 유지.
- 라이트닝 인증 없이도 테스트 가능한 경로(모의 결제/샌드박스)를 유지해야 한다.
- 민감 정보(SECRET_KEY, Blink/Upbit/Telegram 토큰, S3 자격)는 `.env`에서만 관리하고 커밋 금지.
- 작업 전후 `todo.md`를 확인·업데이트하며, 요청 범위를 넘는 코드 변경은 피한다.

## External Dependencies
- **Blink API**: 라이트닝 네트워크 인보이스 생성/조회.
- **Upbit API**: BTC/KRW 환율 조회 및 요약 데이터 취득.
- **S3 호환 오브젝트 스토리지**: 상품/스토어/서명 이미지 저장 (django-storages+boto3).
- **Telegram Bot API**: 환율 및 운영 알림 전송.
- **PostgreSQL 15+**: Render.com 관리형 DB 또는 로컬 Docker 인스턴스.
- **Docker/Render Cron**: 환율 업데이트, APScheduler 잡 등 백그라운드 작업 실행 환경.
