# Expert 계약 링크 복사 신뢰성 개선

## 배경
- 초대 화면의 “링크 복사” 버튼이 로컬 개발(HTTP) 환경 등 보안 컨텍스트가 아닌 곳에서 작동하지 않는다는 제보가 있었습니다.

## 변경 사항
- `expert/static/expert/js/contract_signature.js`에 `navigator.clipboard` 사용이 불가능할 때 `document.execCommand('copy')` 기반 폴백과 최종 수단으로 `window.prompt` 안내를 추가했습니다.
- 초대 템플릿에서 `contract_signature.js`를 항상 로드하도록 수정해, 폼이 없는(예: owner=1) 상황에서도 링크 복사 버튼이 동작하도록 했습니다.
- 복사 성공/실패에 따라 버튼 상태와 안내 문구를 변경해 피드백을 명확히 했습니다.

## 검증
- HTTPS 환경과 로컬 HTTP 환경에서 각각 “링크 복사” 버튼을 눌러 클립보드에 URL이 정상 복사되는지 확인합니다. 실패 시 버튼에 “복사 실패” 메시지가 잠시 노출되어야 합니다.
