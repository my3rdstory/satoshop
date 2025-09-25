---
id: task-15
title: 명예의 전당 정렬 및 페이지네이션 제거
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 08:07'
updated_date: '2025-09-25 08:09'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
명예의 전당 리스트에서 월이 최근 등록순으로 내려오다 보니 1월~12월 순서가 뒤섞여 있습니다. 또한 페이지네이션이 있어 모든 월을 한눈에 볼 수 없습니다. 월을 1월부터 12월까지 오름차순으로 정렬하고, 페이지네이션을 제거해 한 화면에서 모두 볼 수 있게 해주세요.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 명예의 전당 리스트가 월 오름차순(1월~12월)으로 노출된다.
- [x] #2 해당 리스트에서 페이지네이션이 제거되어 모든 항목을 한 화면에서 확인할 수 있다.
- [x] #3 관련 캐시/템플릿 로직이 정렬/페이지네이션 변경과 충돌하지 않음을 확인한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 명예의 전당 리스트 정렬 및 페이지네이션 구조를 파악한다.
2. 쿼리/캐시 로직에서 월 오름차순 정렬이 보장되도록 수정한다.
3. 리스트 뷰와 템플릿에서 페이지네이션을 제거하고 연관 로직을 합리화한다.
4. 캐시/화면 동작을 확인하고 수동 확인 방법을 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- HallOfFame 목록 캐시 키에 버전(v2)을 추가하고 정렬을 -year, month, -created_at 순으로 바꿔 월이 1→12 순으로 노출되도록 했습니다.
- ListView에서 페이지네이션을 제거하고 템플릿의 페이징 UI를 삭제했습니다.
- 테스트: UV_CACHE_DIR=.uv-cache uv run python manage.py check
- 수동 확인: 명예의 전당 페이지에서 연도 필터별로 월이 1월부터 12월까지 오름차순으로 노출되는지, 페이지 이동 UI 없이 전체가 한 화면에 표시되는지 확인.
<!-- SECTION:NOTES:END -->
