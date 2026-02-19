# 모바일 Nostr Connect 콜백 복귀 및 세션 복원 개선

## 요약
- 모바일에서 외부 Nostr 앱(예: Primal) 승인 후 웹으로 돌아왔을 때 로그인 흐름이 끊기던 문제를 개선했다.
- Nostr Connect URI에 `callback` 파라미터를 추가하고, 브라우저 복귀 시 이전 연결 세션을 자동 복원해 재시도하도록 구현했다.

## 상세 변경
- `static/js/nostr-login.js`
  - Nostr Connect URI 생성 시 `callback=<현재 로그인 페이지 URL>`를 자동 부착
  - `sessionStorage`에 NIP-46 pending 세션(비밀키/URI/생성시각)을 임시 저장
  - `visibilitychange`, `pageshow` 이벤트에서 pending 세션 자동 재연결
  - `nostr_connect_return=1` 복귀 마커 처리 및 성공/만료 시 정리
  - 앱 전환 이후 동일 URI/세션으로 handshake를 이어서 수행하도록 흐름 재구성

## 운영 메모
- pending 세션 만료 시간은 10분이며 만료 시 자동 폐기된다.
- 서명 완료 후 pending 세션과 복귀 마커는 즉시 정리된다.
