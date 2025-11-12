# Expert 어드민 메타 뷰 & 내비 개선

## 배경
- 단계 로그의 `meta` JSON이 텍스트 블록으로만 노출되어 결제/서명 정보를 빠르게 파악하기 어려웠음.
- 사용하지 않는 `Contract`/`ContractEmailLog` 어드민 메뉴가 계속 노출되어 Expert 어드민 탐색 시 혼란을 줌.
- 상단 내비게이션에서 로그아웃/메인 상점 이동 경로가 부족해 빠른 컨텍스트 전환이 어려웠음.

## 변경 사항
- `DirectContractStageLog` 어드민 상세 화면에 메타 정보를 키-값 폼 형태로 출력하도록 구성하고, 결제 세부 항목은 별도 라벨로 묶어 가독성을 개선함.
- `Contract`와 `ContractEmailLog` 모델을 어드민에서 제거해 `/admin/expert/contract*/` 경로 접근을 차단함.
- Expert 내비게이션에 `로그아웃`(개요 화면으로 리다이렉션)과 `Go! 사토샵` 버튼을 추가해 요청한 버튼 배치를 완성함.

## 검증
- Django Admin → Expert → `직접 계약 단계 로그` 임의 레코드 진입 시 메타 정보가 폼 형태로 정리되고 결제 정보가 별도 행으로 노출되는지 확인.
- `/admin/expert/contract/`와 `/admin/expert/contractemaillog/` 접속 시 404가 뜨는지 또는 메뉴가 보이지 않는지 확인.
- Expert 상단바에서 `로그아웃` 클릭 후 `/expert/contracts/create/` 개요 화면으로 이동하는지, `Go! 사토샵`이 루트 도메인으로 이동하는지 확인.
