## 개요
- Expert 현황 4번째 카드가 최근 30일 지표 대신 라이트닝 로그인 누적 계정만 안내하도록 UX를 단순화
- 4개의 Expert 현황 카드가 페이지 로드마다 각기 다른 애니메이션(속도, 딜레이, 궤적, 색상)으로 움직이도록 랜덤화를 적용

## 상세
1. `expert/templates/expert/direct_contract_start.html`에서 4번째 카드 보조 문구를 "라이트닝 로그인 완료 기준 누적"으로 교체해 기간 한정 지표 표기를 제거
2. `expert/static/expert/css/direct_contract_start.css`에 CSS 변수 기반 애니메이션 파라미터를 도입하고 `lightningPulse` 키프레임이 개별 카드별 변수를 참조하도록 수정
3. `expert/static/expert/js/direct_contract_start.js`에서 각 `.stat-card`에 대해 duration/delay/direction/translate/scale/opacity/색상 값을 난수로 지정하여 매번 다른 애니메이션을 생성
4. `todo.md`에 관련 작업 내역을 추가해 진행 기록을 남김
