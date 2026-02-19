# NIP-46 시크릿 생성 호환성 오류 수정

## 요약
- 모바일 PWA Nostr 로그인 시 `BunkerSigner.generateSecret is not a function` 오류가 발생하던 문제를 수정했다.

## 상세 변경
- `static/js/nostr-login.js`
  - `BunkerSigner.generateSecret()`가 없는 `nostr-tools` 버전에서도 동작하도록 시크릿 생성 폴백(`generateNostrConnectSecret`)을 추가했다.
  - `BunkerSigner.fromURI` 존재 여부를 검증하고, 미지원 환경에서는 원인 메시지를 명시적으로 반환하도록 보강했다.

## 운영 메모
- NIP-46 모듈 버전 차이로 정적 메서드가 누락된 경우에도 랜덤 시크릿 생성으로 로그인 흐름이 유지된다.
