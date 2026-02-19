# Primal 연동 Nostr Connect 로그인 호환성 보강

## 요약
- 모바일에서 `nostrconnect://` 연결 후 로그인 완료가 되지 않던 문제를 줄이기 위해 NIP-46 호환성을 강화했다.

## 상세 변경
- `static/js/nostr-login.js`
  - `createNostrConnectURI` 인자에 `pubkey`/`clientPubkey`, `perms`/`permissions`를 함께 전달해 라이브러리/앱 해석 차이를 흡수했다.
  - 릴레이 인자도 `relays`/`relayUrls`를 함께 전달하도록 보강했다.
  - `BunkerSigner.fromURI` 초기화를 구/신 시그니처 두 방식으로 순차 시도하도록 `createBunkerSignerFromURI` 헬퍼를 추가했다.

## 운영 메모
- 동일 버전이라도 배포 번들/런타임 환경에 따라 NIP-46 메서드 시그니처 차이가 발생할 수 있어 다중 시그니처 시도를 기본 전략으로 유지한다.
