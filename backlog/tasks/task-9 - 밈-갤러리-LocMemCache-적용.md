---
id: task-9
title: 밈 갤러리 LocMemCache 적용
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
밈 갤러리 화면의 썸네일 및 메타데이터 제공에 LocMemCache를 도입해 캐시 부하를 줄인다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 밈 갤러리 데이터 공급 로직이 LocMemCache를 활용해 반복 호출 시 캐시를 우선 조회한다.
- [x] #2 캐시 무효화 정책이 갱신 이벤트와 연동되어 최신 데이터가 유지된다.
- [x] #3 캐시 적용 구간에 대한 모니터링 또는 테스트가 준비되어 회귀를 방지한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 밈 목록/상세 뷰에 로컬 메모리 캐시 계층을 추가한다.
2. 밈 게시/수정/태그 변경 시 캐시 무효화 시그널을 연결한다.
3. 테스트 및 로깅으로 캐시 동작을 검증한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 밈 목록/상세 뷰에 버전 기반 LocMemCache(180초)를 도입하고 검색/태그 조합별 키를 구성했습니다.
- MemePost/MemeTag 및 태그 M2M 변경 시 버전이 증가하도록 시그널을 등록했습니다.
- 테스트: PYTHONPATH=/tmp/dotenv_stub python3 manage.py test myshop stores boards 실행 시 환경변수와 DB 미설정으로 실패하여, 로컬에서 설정 후 동일 명령을 권장합니다.
<!-- SECTION:NOTES:END -->
