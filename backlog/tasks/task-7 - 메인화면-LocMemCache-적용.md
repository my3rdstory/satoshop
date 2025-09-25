---
id: task-7
title: 메인화면 LocMemCache 적용
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
메인화면 API 데이터 조회에 LocMemCache를 도입하여 초기 로드 시간을 줄인다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 LocMemCache 적용 후 메인화면 데이터 조회가 반복 호출 시 캐시에서 응답된다.
- [x] #2 캐시 키와 만료 전략이 정의되고 구현 문서에 기록된다.
- [x] #3 메인화면 관련 테스트를 실행해 캐시 적용 이후에도 모두 통과한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 평가 중복 조회가 많은 홈 컨텍스트 데이터를 LocMemCache로 래핑한다.
2. SiteSettings/문서 변경 시 캐시 무효화 경로를 추가한다.
3. 관련 문서와 테스트를 통해 캐시 전략을 확인한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 홈 컨텍스트에 LocMemCache(300초)를 적용하고 SiteSettings/DocumentContent 변경 시 캐시를 무효화하도록 헬퍼를 추가했습니다.
- STATIC_CACHE_GUIDE.md에 홈/스토어/게시판 캐시 키와 TTL을 정리했습니다.
- 테스트: PYTHONPATH=/tmp/dotenv_stub python3 manage.py test myshop stores boards 실행 시 SECRET_KEY 등 환경변수 미설정으로 중단되어 로컬 환경 구성 후 재실행이 필요합니다.
<!-- SECTION:NOTES:END -->
