# API 키 Nostr 인증 모드 추가

## 요약
- Django Admin의 API 키 추가/수정 화면에 `Nostr 인증 사용` 체크박스와 공개키 입력 필드를 추가했다.
- API 키별 인증 모드를 `기존 Bearer` 또는 `Nostr 서명`으로 분기하도록 확장했다.
- Nostr 인증 전용 챌린지 발급 엔드포인트를 추가하고, API 요청 시 Nostr 서명 검증을 수행하도록 구현했다.

## 상세 변경
- `api.models.ApiKey`
  - `auth_method` 필드 추가 (`api_key`/`nostr`)
  - `nostr_pubkey` 필드 추가
  - Nostr 모드 판별 프로퍼티(`uses_nostr_auth`) 추가
- `api.forms.ApiKeyAdminForm` 신규
  - Nostr 체크 여부와 공개키(`npub`/hex) 입력 검증
- `api.nostr_auth` 신규
  - 공개키 정규화, 1회성 챌린지 발급, BIP340 Schnorr 서명 검증 로직 분리
- `api.authentication.authenticate_request`
  - Bearer 인증과 Nostr 헤더 인증(`X-Nostr-*`) 이중 지원
  - Nostr 모드 키는 Bearer 인증을 거부하도록 처리
- `api.views`
  - `GET /api/v1/nostr/challenge/?pubkey=<hex_or_npub>` 추가
- `api.urls`
  - `v1/nostr/challenge/` 라우팅 추가
- 문서
  - `README.md` 외부 API 인증 섹션에 Nostr 인증 절차 추가
  - `api/static/api/openapi-v1.json`에 Nostr 챌린지 경로/보안 헤더 스키마 반영

## 운영/검증 메모
- 챌린지는 캐시 기반 1회성 토큰이며 5분 뒤 만료된다.
- Nostr 인증 요청은 아래 헤더 3개를 모두 전달해야 한다.
  - `X-Nostr-Pubkey`
  - `X-Nostr-Challenge-Id`
  - `X-Nostr-Signature`
