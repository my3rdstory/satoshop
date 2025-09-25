---
id: task-16
title: 장고 어드민 속도 개선
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 08:23'
updated_date: '2025-09-25 08:27'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
관리자 화면 전반에서 필터/정렬 시 응답 속도가 느려지는 문제가 있어 주요 모델에 복합 인덱스를 추가하고 어드민 쿼리를 최적화해야 합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 주요 관리자 화면(주문, 인보이스, 스토어, 상품, 디지털 파일, 밋업) 필터/정렬 패턴을 반영한 인덱스가 모델에 추가된다.
- [x] #2 어드민 리스트의 per-row 집계 로직이 annotate 등으로 최적화된다.
- [x] #3 모델 마이그레이션과 어드민 코드 변경 후 django check를 통과하고 수동 확인 방법을 남긴다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 주요 어드민 화면(주문/인보이스/스토어/상품/디지털 파일/밋업)의 필터·정렬 패턴을 정리하고 필요한 인덱스를 모델에 추가한다.
2. 주문, 밋업, 디지털 파일 어드민에서 per-row 집계를 annotation 등으로 최적화한다.
3. 마이그레이션 생성 후 django check를 실행하고 수동 확인 방법을 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- orders/models.py에 주문/인보이스 어드민 필터 패턴을 반영한 복합 인덱스를 추가하고 주문 어드민 쿼리에 annotate(Count)를 적용해 아이템 수 계산을 최적화했습니다.
- products/stores/file/meetup 각 모델에 boolean·상태 기반 인덱스를 확장하고 관련 어드민(디지털 파일, 밋업)에서 per-row 집계 쿼리를 annotation으로 대체했습니다.
- 새로운 인덱스 마이그레이션을 생성하고, django check를 통과했습니다.
- 테스트: UV_CACHE_DIR=.uv-cache uv run python manage.py check
- 수동 확인: 장고 어드민에서 주문/상품/스토어/디지털 파일/밋업 리스트 필터를 적용해 응답 속도를 확인하고, 마이그레이션 적용 후 인덱스가 생성됐는지 DB에서 확인하세요.
<!-- SECTION:NOTES:END -->
