# Expert 계약서 상단 헤더 제거

## 배경
- 최종 계약 PDF 첫 페이지에 제목/공유 ID/생성 시각과 구분선이 반복 출력되어 본문 앞부분이 이중 표시되는 문제가 있었습니다.

## 변경 사항
1. `expert/templates/expert/contract_pdf.html`에서 상단 `<header>` 블록을 삭제해 계약 본문만 렌더되도록 정리.
2. 대응하는 CSS(`expert/static/expert/css/contract_pdf.css`)에서 `contract-header`, `contract-title`, `contract-meta` 스타일 정의를 제거.

## 결과
- 계약 PDF에는 본문 내에 한 번만 제목과 메타 정보가 나타나고, 페이지 상단은 바로 계약 내용으로 이어집니다.
