# 모바일 Nostr Connect 재진입 복구 안정화

## 요약
- Primal 등 외부 앱 전환 후 웹으로 돌아왔을 때 로그인 복구가 실패하던 문제를 줄이기 위해, NIP-46 pending 세션 저장소와 재연결 진입 시점을 보강했다.

## 상세 변경
- `static/js/nostr-login.js`
  - NIP-46 pending 세션 저장소를 `sessionStorage` 중심에서 `localStorage` 우선으로 변경
  - pending 세션 최대 유효 시간을 4분으로 조정(챌린지 만료 시간과 정합)
  - 로그인 페이지 재진입 시 복귀 마커 여부와 무관하게 pending 세션 자동 재연결 시도
  - pending 세션이 있으면 상태 폴링을 즉시 재개해 로그인 완료 복구를 빠르게 수행

## 운영 메모
- 모바일 웹뷰가 백그라운드 전환 중 메모리를 정리해도 pending 세션이 유지돼 복구 성공률이 올라간다.
