# 모바일 Nostr 로그인 서버 폴링 완료 흐름 적용

## 요약
- Primal 등 모바일 앱 연동 시 로그인 완료가 불안정하던 문제를 줄이기 위해, Nostr 로그인 완료 상태를 서버에서 폴링해 세션 로그인을 복구하는 흐름을 추가했다.
- NIP-46 경로에서 `getPublicKey` 의존을 제거하고, 서명 이벤트의 `pubkey`를 기준으로 검증하도록 변경했다.

## 상세 변경
- `accounts/nostr_service.py`
  - 챌린지 생성 시 공개키 입력을 선택값으로 허용
  - 공개키 고정 챌린지인 경우에만 일치 검증 수행
  - 로그인 완료 결과 캐시 저장/소비 헬퍼(`store_nostr_login_result`, `pop_nostr_login_result`) 추가
- `accounts/views.py`
  - `verify_nostr_login_view`에서 검증 성공 시 로그인 결과를 캐시에 저장
  - `GET /accounts/check-nostr-auth/?challenge_id=...` 엔드포인트 추가
  - 상태 엔드포인트에서 결과 캐시를 소비해 실제 세션 로그인 처리
- `accounts/urls.py`
  - `check-nostr-auth/` 라우팅 추가
- `accounts/templates/accounts/nostr_login.html`
  - 상태 폴링 URL(`data-status-url`) 전달 추가
- `static/js/nostr-login.js`
  - 챌린지 상태 폴링 로직 추가(2초 간격)
  - NIP-46 경로에서 `getPublicKey` 호출 제거
  - 서명 이벤트에서 `pubkey`를 추출해 검증 API에 전달
  - pending 세션에 챌린지 정보를 저장/복구하고 복귀 후 폴링을 자동 재개

## 운영 메모
- 모바일 앱 전환 후에도 동일 챌린지에 대한 완료 상태를 폴링해 로그인 세션을 복구할 수 있다.
- 챌린지/완료 캐시 TTL은 기존 정책(5분)을 따른다.
