---
id: task-18
title: 주문 어드민 스토어 드롭다운 정렬 보완
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 13:22'
updated_date: '2025-09-25 13:23'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
주문 어드민 드롭다운에서 스토어 이름이 비어 있는 항목이 상단에 노출되어 선택성이 떨어집니다. 이름이 없는 스토어는 목록 하단으로 이동시키고 나머지는 기존 정렬을 유지해야 합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 드롭다운에 표시되는 스토어 중 이름이 비어 있는 항목은 하단으로 정렬된다.
- [x] #2 django check를 통과하고 수동 확인 방법을 남긴다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 드롭다운에 공급되는 스토어 리스트를 이름 유무에 따라 상단/하단으로 재정렬한다.
2. django check를 실행하고 수동 확인 방법을 낱개로 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 주문 어드민 changelist 컨텍스트에서 스토어 목록을 이름 유무로 분리해 빈 이름은 리스트 하단에 오도록 재정렬했습니다.
- 테스트: UV_CACHE_DIR=.uv-cache uv run python manage.py check
- 수동 확인: 주문 어드민 > 주문들에서 드롭다운을 열어 이름이 없는 항목이 목록 맨 아래에 표시되는지 확인하세요.
<!-- SECTION:NOTES:END -->
