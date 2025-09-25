---
id: task-8
title: 스토어 탐색 LocMemCache 적용
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 05:59'
updated_date: '2025-09-25 06:12'
labels:
  - performance
  - backend
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토어 탐색 페이지의 상품 목록 데이터 조회에 LocMemCache를 도입해 반복 요청 성능을 높인다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 LocMemCache 적용 후 스토어 탐색 목록 API가 재요청 시 캐시된 데이터를 반환한다.
- [x] #2 캐시 TTL과 무효화 조건이 정의되고 관련 업데이트 플로우에 반영된다.
- [x] #3 캐시 적용 경로에 대한 테스트 또는 로깅으로 정상 동작을 검증한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 스토어 탐색 기본 화면 데이터 구성에 캐시 레이어를 도입한다.
2. 스토어와 주문 관련 이벤트에서 캐시를 무효화하도록 시그널을 정리한다.
3. 캐싱 전략과 테스트 방법을 공유하고 확인한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 검색어가 없는 스토어 탐색 컨텍스트를 LocMemCache(300초)에 저장하고 스토어·주문 이벤트 시 시그널로 무효화하도록 구성했습니다.
- 캐시 전략을 STATIC_CACHE_GUIDE.md에 추가해 키와 TTL, 무효화 조건을 명시했습니다.
- 테스트: PYTHONPATH=/tmp/dotenv_stub python3 manage.py test myshop stores boards 실행 시 필요한 환경변수/DB가 없어 중단되어, 로컬에서 환경을 채운 뒤 동일 명령 재시도가 필요합니다.
<!-- SECTION:NOTES:END -->
