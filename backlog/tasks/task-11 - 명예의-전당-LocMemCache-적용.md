---
id: task-11
title: 명예의 전당 LocMemCache 적용
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 06:40'
updated_date: '2025-09-25 06:45'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Hall of Fame 목록과 필터 데이터를 LocMemCache로 캐싱해 반복 호출 시에도 빠르게 응답할 수 있도록 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Hall of Fame 목록·필터 API와 HTML뷰가 LocMemCache를 통해 재호출 시 캐시 데이터를 반환한다.
- [x] #2 HallOfFame 생성·수정·삭제 시 캐시 버전 또는 키가 무효화되어 최신 데이터가 노출된다.
- [x] #3 STATIC_CACHE_GUIDE.md에 캐시 키와 TTL, 무효화 조건이 정리된다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 기존 boards 캐시 헬퍼와 명예의 전당 뷰 로직을 파악해 캐시 키/TTL 설계를 확정한다.
2. cache_utils 및 signals에 명예의 전당 전용 캐시 헬퍼와 무효화 로직을 추가한다.
3. HallOfFame 관련 HTML/JSON 뷰에서 LocMemCache를 읽고 쓰도록 적용하고 필요한 문서를 업데이트한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 명예의 전당 목록/필터 전용 캐시 헬퍼와 시그널을 추가해 LocMemCache 버전 관리를 적용했습니다.
- HallOfFame 목록 뷰와 AJAX API가 동일한 캐시를 사용하도록 정리하고 파라미터 정규화 및 필터 캐시를 도입했습니다.
- STATIC_CACHE_GUIDE.md에 명예의 전당 캐시 키/TTL과 무효화 조건을 문서화했습니다.
- 테스트: python3 -m compileall boards
<!-- SECTION:NOTES:END -->
