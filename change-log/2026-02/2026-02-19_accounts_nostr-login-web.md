# 웹 로그인에 Nostr 인증(NIP-07) 추가

## 요약
- `/accounts/login/` 화면에 `Nostr로 로그인` 버튼을 추가했다.
- `NIP-07` 기반 Nostr 서명 이벤트 검증으로 웹 세션 로그인을 처리하는 백엔드 흐름을 구현했다.
- 최초 Nostr 로그인 시 공개키 기준으로 계정을 자동 생성하고, 이후 동일 공개키로 로그인하도록 계정 매핑 모델을 추가했다.

## 상세 변경
- `accounts.models`
  - `NostrUser` 모델 추가
  - 사용자와 Nostr 공개키(64자리 hex)를 1:1로 매핑하고 최근 로그인 시각을 기록
- `accounts.migrations`
  - `0013_nostruser.py` 추가
- `accounts.nostr_service` 신규
  - 챌린지 발급(캐시 5분 TTL)
  - 서명 이벤트(`kind=22242`) 유효성 검증
  - 이벤트 해시/슈노르 서명 검증
  - 공개키 계정 자동 생성/로그인 계정 조회
- `accounts.views`
  - `nostr_login_view` 추가
  - `create_nostr_login_challenge_view` 추가
  - `verify_nostr_login_view` 추가
- `accounts.urls`
  - `GET /accounts/nostr-login/`
  - `GET /accounts/nostr-auth-challenge/`
  - `POST /accounts/nostr-auth-verify/`
- 템플릿/정적 파일
  - `accounts/templates/accounts/login.html`에 Nostr 로그인 버튼 추가
  - `accounts/templates/accounts/nostr_login.html` 신규
  - `static/css/nostr-login.css` 신규
  - `static/js/nostr-login.js` 신규
- 문서
  - `README.md` 사용자 관리 섹션에 Nostr 웹로그인 안내 추가
  - `todo.md`에 이번 작업 완료 항목 반영

## 운영/검증 메모
- Nostr 로그인은 브라우저 `NIP-07` 확장을 전제로 동작한다.
- 챌린지는 1회성 캐시 키로 관리하며 검증 성공 시 즉시 폐기된다.
