# 모바일 Nostr Connect clientPubkey 오류 수정

## 요약
- 모바일 배포 환경에서 Nostr 로그인 시 `clientPubkey is required` 오류가 발생하던 문제를 수정했다.

## 상세 변경
- `static/js/nostr-login.js`
  - `createNostrConnectURI` 호출을 최신 NIP-46 시그니처(객체 인자)로 교체했다.
  - `BunkerSigner.fromURI` 호출 인자를 최신 시그니처(`fromURI(secretKey, uri, { pool, ... })`)에 맞게 수정했다.
  - `fromURI` 자체를 타임아웃 래핑해 연결 대기 실패를 명시적으로 처리하도록 정리했다.

## 원인
- NIP-46 API를 구형 인자 순서로 호출해 연결 URI 생성/파싱 시 필수 필드인 `clientPubkey`가 누락된 형태로 처리됐다.
