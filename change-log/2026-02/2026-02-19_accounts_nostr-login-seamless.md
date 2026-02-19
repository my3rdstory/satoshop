# Nostr 로그인 데스크톱·모바일 심리스 전환

## 요약
- `Nostr로 로그인` 버튼 하나로 NIP-07과 NIP-46을 자동 분기하는 흐름을 적용했다.
- 브라우저 확장이 없을 때 Nostr Connect QR/딥링크 패널을 즉시 노출해 모바일·데스크톱 모두 로그인 가능하도록 개선했다.

## 상세 변경
- `accounts/templates/accounts/nostr_login.html`
  - Nostr Connect 패널(URI, QR, 복사, 앱 열기 버튼) 추가
  - 안내 문구를 자동 전환 흐름 기준으로 갱신
  - `qrious` 스크립트 로드 추가
- `static/js/nostr-login.js`
  - 로그인 시작 시 `NIP-07` 지원 여부 자동 감지
  - NIP-07 미지원 시 `NIP-46(Nostr Connect)`로 자동 전환
  - `nostr-tools` 브라우저 모듈(`pure`, `nip46`, `pool`) 동적 로드
  - QR 렌더링, URI 복사, 딥링크 열기, 연결/서명 타임아웃 처리 추가
- `static/css/nostr-login.css`
  - Nostr Connect 패널/QR/입력/버튼 스타일 추가
- `README.md`
  - 사용자 관리 섹션에 `NIP-07 + NIP-46` 자동 전환 로그인 설명 반영
- `todo.md`
  - 심리스 로그인 개선 작업 완료 항목 추가

## 운영 메모
- 기본 Nostr Connect 릴레이는 `wss://relay.nsec.app`, `wss://relay.damus.io`를 사용한다.
- 브라우저에서 `window.nostr`가 있으면 NIP-07 경로가 우선 실행된다.
