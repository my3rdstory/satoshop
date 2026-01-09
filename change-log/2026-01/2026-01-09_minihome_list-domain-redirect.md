## 배경
- 기존 `/minihome/` 경로를 목록 전용 도메인으로 옮기고, 기존 경로는 새 도메인으로 안내할 필요가 있었음.

## 변경 사항
- 목록 전용 도메인이 설정된 경우 `/minihome/` 경로 접근 시 목록 도메인 루트로 리다이렉트.
- `/minihome/<slug>/` 접근 시 목록 도메인의 `/<slug>/`로 리다이렉트.

## 영향
- 기존 경로 접근 시 자동으로 목록 전용 도메인으로 이동됨.

## 대장 수동 테스트 가이드
1. `MINIHOME_LIST_DOMAIN` 설정 후 `https://store.btcmap.kr/minihome/` 접속.
2. `https://mini.btcmap.kr/`로 리다이렉트되는지 확인.
3. `https://store.btcmap.kr/minihome/<slug>/` 접속 시 `https://mini.btcmap.kr/<slug>/`로 이동되는지 확인.
