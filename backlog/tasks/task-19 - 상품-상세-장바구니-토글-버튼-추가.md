---
id: task-19
title: 상품 상세 장바구니 토글 버튼 추가
status: Done
assignee:
  - '@codex'
created_date: '2025-09-26 07:33'
updated_date: '2025-09-26 09:40'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
상품 상세 화면에서 장바구니 진입을 쉽게 하기 위해 화면 오른쪽 중앙에 폴더 모양의 플로팅 버튼을 추가하고, 버튼 클릭 시 장바구니 패널이 토글되도록 구현합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 상품 상세 화면 우측 중앙에 폴더 모양의 플로팅 버튼이 노출된다.
- [x] #2 폴더 버튼을 클릭하면 장바구니 영역이 열리고, 다시 클릭하면 닫힌다.
- [x] #3 장바구니 패널 토글 동작이 데스크톱과 모바일 뷰에서 모두 정상 동작한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 상품 상세 템플릿에 폴더 모양 장바구니 토글 버튼을 추가하고 cart 컴포넌트와 연결합니다.
2. products.css에 버튼 위치와 상태 스타일을 정의해 데스크톱/모바일 모두 적절히 노출되도록 조정합니다.
3. cart.js에서 장바구니 열고 닫힘에 맞춰 버튼 아이콘과 접근성 속성을 갱신하도록 토글 로직을 확장합니다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 상품 상세 페이지 우측 하단에 플로팅 장바구니 토글 버튼을 추가해 사이드바와 연결했습니다.
- cart.js에서 버튼 상태를 관리해 aria 레이블을 갱신하고 is-open 클래스로 스타일 전환을 제어합니다.
- 기본 상태에서는 카트 아이콘만 노출하고, 장바구니를 열면 카트 아이콘 옆에 닫기(X) 아이콘이 함께 노출되도록 이중 아이콘 구성을 적용했습니다.
- CSS로 모바일(34px)과 데스크톱(44px) 크기를 구분하고, 열림 상태에서 버튼이 패널과 겹치지 않도록 위치를 조정했습니다.
- 자동화 테스트는 실행하지 못했으므로 브라우저에서 데스크톱/모바일 토글 동작을 확인해야 합니다.
<!-- SECTION:NOTES:END -->
