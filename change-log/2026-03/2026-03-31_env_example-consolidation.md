# 환경 변수 예시 파일 정리

## 요약
- 현재 코드와 운영 스크립트가 실제로 참조하는 환경 변수를 기준으로 예시 파일을 다시 정리했다.
- `.env.local.example`을 로컬 전체 기능 기준의 완전판으로 확장했다.
- `.env.production.example`도 같은 변수 집합을 기준으로 운영용 값 예시로 맞췄고, 중복 성격의 `env.example`은 제거했다.

## 상세 변경
- `.env.local.example`
  - 로컬 Docker DB 포트(`5434`) 기준으로 수정
  - 결제, Blink webhook, 암호화 키, S3, 메일, 환율 웹훅, Redis 확장, Expert 서명, Render 런타임 관련 변수까지 주석과 함께 정리
- `.env.production.example`
  - 현재 코드 기준 필수/선택 변수를 로컬 예시와 동일한 구조로 맞춤
  - Render/Docker 운영 시 사용하는 런타임 변수와 외부 환율 크론용 변수까지 추가
- `env.example`
  - `.env.local.example` 및 `.env.production.example`과 역할이 중복되어 제거

## 운영 메모
- 앱 런타임 기준 환경 변수와 외부 스크립트용 환경 변수(`WEBHOOK_URLS` 등)를 한 파일에서 모두 확인할 수 있게 정리했다.
- `BLINK_WEBHOOK_SECRET`, `BLINK_ENCRYPTION_KEY`, `WEBHOOK_TOKEN`처럼 기존 예시 파일에 없던 운영 핵심 변수도 이번에 포함했다.
