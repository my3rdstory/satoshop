# Nostr 로그인 데스크톱 폴백 및 타임아웃 호환성 보강

## 요약
- 데스크톱에서 NIP-07 로그인 실패 시 NIP-46으로 자동 전환되도록 폴백 경로를 추가했다.
- `withTimeout`이 Promise 이외의 동기 반환값도 처리하도록 보강해 `then is not a function` 계열 오류를 방지했다.

## 상세 변경
- `static/js/nostr-login.js`
  - NIP-07 경로 실패 시 경고 로그 후 NIP-46 경로로 자동 재시도하도록 수정
  - `withTimeout(valueOrPromise, ...)`에서 `Promise.resolve(...)`를 사용해 동기/비동기 반환 모두 지원

## 운영 메모
- 확장이 설치돼 있어도 권한 거부·잠금 등으로 NIP-07이 실패하면 동일 버튼 흐름에서 NIP-46 로그인으로 이어진다.
