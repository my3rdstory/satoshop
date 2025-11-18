# Repository Guidelines

## 에이전트/협업 지침
- 호칭·언어: 저를 “대장”이라 부르고, 모든 대화는 한글로.
- 작업 방식: 플랜모드로 계획을 꼼꼼하게 세운 다음 그 계획에 맞게 todo 목록을 만들고, 하나씩 체계적으로 자동 실행. 
- `rm`/`mv`로 삭제·이동은 사전 승인 필수, 그 외 bash/편집은 자동 처리 가능.
- 내가 요청한 범위를 훨씬 벗어나는 부분은 수정하거나 삭제하지 말고, 요청한 내용에 충실하게 집중해서 작업할 것.
- 마이그레이션이 필요한 경우 마이그레이션 관련 명령어는 직접 자동으로 진행해도 된다.
- 명령: 장고 명령은 항상 `uv run` 사용. 개발 서버는 대장이 수동 관리(재시작 필요 시 알림).
- 템플릿 가이드: 템플릿명과 동일한 `css/js`를 `static`에 생성, 토스트 미사용, 다크모드 대응.
- 문서화: 중요한 개선사항은 `README.md`에 체계적으로 업데이트. 
- 테스트는 내가 수동으로 할 것이니 직접 자동으로 하지 말고, 테스트하는 방법만 제시할 것
- 큰 규모의 작업이 요청되면 루트의 `todo.md` 파일에 현재 진행 중인 작업을 할일 목록으로 기록하고, 각 항목을 순차적으로 처리한다.
- 작업을 시작하기 전에 최신 `todo.md`를 확인하고 필요한 경우 업데이트한다.
- 작업 후에는 간단한 커밋 메시지를 정리해서 알려주어야 한다. 바로 복사해서 붙여 넣을 수 있도록 한글로만 맨 끝에 별도 표시 없이 커밋 메시지 만들어줘라.예들 들어, "커밋 메시지 제안: " 등과 같이 앞 부분은 없애고 바로 커밋 메시지를 한글로 알려줘라. 이후 자동으로 해당 커밋 메시지를 적용한 커밋을 실행한다.
  - ✅ 커밋 메시지를 전달했다면 별도 지시가 없어도 동일한 메시지로 즉시 `git commit`을 완료해야 한다. (커밋 메시지 통보 → 자동 커밋 순서 준수)

## 템플릿 제작 가이드
- 템플릿을 만들면 템플릿에 사용하는 js, css 파일을 템플릿 이름과 동일한 파일로 만들어 static 폴더에 저장
- css 패키지는 tailwind 사용. 기본 글꼴 크기는 text-sm 사용
- 토스트 메시지는 사용하지 말 것
- 반드시 다크모드 대응할 것

## 프로젝트 구조

| 경로 | 설명 |
| --- | --- |
| `satoshop/` | Django 프로젝트 설정, 전역 URL, 미들웨어, WSGI/ASGI 엔트리포인트가 위치합니다. |
| `manage.py` | Django 관리 명령 실행 진입점입니다. |
| `accounts/` | 사용자 계정/인증 뷰, LNURL 연동 로직, 템플릿이 포함된 앱입니다. |
| `products/` | 상품, 옵션, 카테고리 모델과 관련 서비스/템플릿을 담습니다. |
| `stores/` | 스토어(셀러) 관리 앱으로, 스토어 모델/폼/템플릿과 관리자 뷰를 제공합니다. |
| `orders/` | 장바구니, 주문, 인보이스 모델과 결제 후 처리 뷰·서비스가 모여 있습니다. |
| `ln_payment/` | Blink 기반 라이트닝 결제 API 연동 서비스와 뷰를 제공합니다. |
| `myshop/` | 공용 페이지, 캐시 유틸리티, 템플릿 태그 등 사이트 전반 기능을 담은 코어 앱입니다. |
| `reviews/`, `menu/`, `meetup/`, `game/` | 각각 후기, 메뉴, 오프라인 모임, 미니 게임 등 부가 기능 앱입니다. |
| `templates/`, `static/`, `staticfiles/` | 글로벌 템플릿과 정적 자산이 위치합니다 (`collectstatic` 결과는 `staticfiles/`). |
| `scripts/` | 배포/운영 자동화 스크립트와 크론 작업 도구가 있습니다. |
| `requirements.txt`, `pyproject.toml`, `uv.lock` | 파이썬 의존성과 개발 도구 구성이 정의됩니다. |

## 빌드·테스트·개발 명령
- 의존성 설치: `uv sync`
- DB 기동(개발): `docker compose up -d postgres`
- 마이그레이션: `uv run python manage.py migrate`
- 개발 서버: `uv run python manage.py runserver`(대장이 수동 관리하므로 재시작 필요 시에만 알려주세요)
- 슈퍼유저: `uv run python manage.py createsuperuser`
- 테스트(전체/앱): `uv run python manage.py test` / `uv run python manage.py test pages`
- 배포 스크립트: `./build.sh`(Render에서 호출)

## 코딩 스타일·네이밍
- Python: PEP 8, 4칸 들여쓰기. 클래스 `PascalCase`, 함수/변수 `snake_case`.
- Django: 모델 단수형, 앱별 템플릿은 각 앱 또는 `templates/` 활용.
- 프런트엔드: ES6+. 섹션 폴더는 `snake_case`(또는 `kebab-case`) 예: `hero_section/`.
- 템플릿에 정적파일을 넣지 말고 각 앱 `static/{css,js}/`에 배치. 다크모드 대응 필수.

## 보안·설정
- 비밀정보 커밋 금지. `local.env` 사용(`website/settings.py`에서 로드).
- 주요 환경: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`(또는 개별 DB 변수), `ADMIN_*`(빌드 시 사용).
- 운영 배포 시 `ALLOWED_HOSTS`를 정확히 설정.

## 변경 이력 기록
- 지시한 내역을 아래와 같은 형식으로 변경 이력을 기록한다. 
- 폴더 : 루트/change-log/ 내 YYYY-MM 하위 폴더를 만들고, 해당 월의 변경 이력 파일을 그 폴더에 저장한다.
- 단위: “작업(이슈/PR/스펙항목)” 단위 1파일
- 파일명: YYYY-MM-DD_<scope>_<short-title>.md
예) 2025-11-08_checkout-addrs_normalize.md
- scope는 앱/도메인 레벨(예: auth, checkout, analytics).
- “짧은 제목”은 나중에 릴리스 노트에 그대로 쓰일 만큼 간결하게.
