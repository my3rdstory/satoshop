---
id: task-14
title: 주문 CSV 연락처 텍스트 처리
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 07:59'
updated_date: '2025-09-25 08:02'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토어 주인장 주문관리 화면에서 다운로드하는 주문 CSV/엑셀 파일에서 연락처가 숫자로 인식되어 선행 0이 사라지거나 전화번호 포맷이 깨집니다. 연락처 칼럼을 텍스트로 고정해 엑셀에서 열어도 값이 변형되지 않도록 처리해야 합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 주문 전체 다운로드(export_orders_csv)에서 연락처 칼럼이 텍스트로 저장된다.
- [x] #2 상품별 주문 CSV(export_product_orders_csv)에서도 연락처 칼럼이 텍스트로 유지된다.
- [x] #3 엑셀/CSV로 내려받아도 선행 0이 유지되는지를 수동 확인 방법으로 안내한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 주문 전체 CSV/엑셀(export_orders_csv) 코드에서 연락처 컬럼을 문자열로 강제하도록 처리한다.
2. 상품별 CSV(export_product_orders_csv)에서도 연락처 텍스트 포맷을 적용한다.
3. 동일 값이 엑셀에서 변형되지 않는지 간단한 수동 확인 절차를 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- export_orders_csv에서 연락처 셀을 문자열(@) 서식으로 저장하고 CSV fallback에는 _format_text_for_csv를 추가해 엑셀에서 전화번호가 숫자로 바뀌지 않도록 처리했습니다.
- 상품 단위 CSV 다운로드(products_orders_csv_download.py)에도 동일한 텍스트 포맷터를 도입해 연락처/우편번호 칼럼 모두 텍스트로 내려가도록 정리했습니다.
- 테스트: UV_CACHE_DIR=.uv-cache uv run python manage.py check
- 수동 확인: 주문관리 > 주문 전체 다운로드 및 상품별 CSV 다운로드 후 엑셀에서 열어 연락처 선행 0이 유지되는지 확인한다.
<!-- SECTION:NOTES:END -->
