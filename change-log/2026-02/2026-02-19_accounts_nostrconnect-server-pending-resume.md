# Nostr Connect 콜백 복귀 실패 대응 서버 pending 세션 추가

## 요약
- 모바일에서 외부 앱(Primal 등) 승인 후 다른 브라우저 컨텍스트로 복귀해도 로그인 흐름을 이어갈 수 있도록 서버 pending 세션(token) 복구 방식을 추가했다.

## 상세 변경
- `accounts/nostr_service.py`
  - Nostr 로그인 pending 세션 캐시 저장/조회/정리 함수 추가
- `accounts/views.py`
  - `POST /accounts/nostr-auth-pending/create/` 추가
  - `GET /accounts/nostr-auth-pending/fetch/?token=...` 추가
  - `POST /accounts/nostr-auth-pending/clear/` 추가
  - pending 세션 생성/조회/정리 로그 추가
- `accounts/urls.py`
  - pending 세션 관련 라우트 추가
- `accounts/templates/accounts/nostr_login.html`
  - pending 세션 API URL을 data-attribute로 전달
- `static/js/nostr-login.js`
  - Nostr Connect 시작 시 resume token 생성 후 callback URL에 `nostr_connect_resume` 포함
  - pending 세션을 서버/로컬 모두 저장
  - 페이지 재진입 시 URL 토큰으로 서버 pending 세션 복원 후 자동 재연결
  - 로그인 완료 시 서버 pending 세션 정리

## 운영 메모
- 모바일 PWA가 백그라운드 전환으로 스토리지를 잃어도 URL resume token으로 세션 복원이 가능하다.
