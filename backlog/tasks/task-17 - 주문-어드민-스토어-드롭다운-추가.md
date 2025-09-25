---
id: task-17
title: 주문 어드민 스토어 드롭다운 추가
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 13:08'
updated_date: '2025-09-25 13:09'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
장고 어드민 주문 목록에서 스토어 필터를 빠르게 선택할 수 있는 전용 드롭다운이 없어 필터 사용성이 떨어집니다. 액션 영역 옆에 스토어 선택 풀다운을 추가해 즉시 필터링이 가능하도록 개선합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 주문 어드민 리스트 상단에 스토어 선택 드롭다운이 노출된다.
- [x] #2 드롭다운으로 스토어를 선택하면 기존 리스트 필터와 동일하게 목록이 즉시 필터링된다.
- [x] #3 django check를 통과하고 수동 확인 방법을 남긴다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 주문 어드민 changelist 템플릿을 오버라이드해 스토어 드롭다운을 배치한다.
2. 드롭다운 선택 시 기존 필터 파라미터를 유지하며 필터링이 적용되도록 처리한다.
3. django check 실행 및 수동 확인 방법을 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 주문 어드민에 전용 changelist 템플릿을 추가하고 actions 인근에 스토어 선택 드롭다운을 배치했습니다.
- 드롭다운 선택 시 기존 GET 파라미터를 유지한 채 `store__id__exact` 필터를 적용하여 즉시 필터링되도록 했습니다.
- 테스트: UV_CACHE_DIR=.uv-cache uv run python manage.py check
- 수동 확인: 관리자 > 주문 관리 > 주문들 화면에서 드롭다운으로 스토어를 선택해 필터링이 되는지 확인하고, 다른 검색/필터와 병행 시에도 파라미터가 유지되는지 확인.
<!-- SECTION:NOTES:END -->
