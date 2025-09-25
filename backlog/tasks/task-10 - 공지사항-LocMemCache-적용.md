---
id: task-10
title: 공지사항 LocMemCache 적용
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
공지사항 목록과 상세 조회에 LocMemCache를 적용해 조회 성능과 안정성을 향상시킨다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 LocMemCache가 공지사항 데이터 조회 경로에 적용되어 반복 요청 시 캐시에서 응답한다.
- [x] #2 공지사항 생성·수정·삭제 시 캐시가 적절히 무효화되어 최신 상태를 유지한다.
- [x] #3 캐시 적용 이후 관련 테스트 또는 QA 시나리오가 수행되어 회귀가 없음이 확인된다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 공지 목록/상세 조회에서 LocMemCache를 활용하도록 뷰를 보강한다.
2. 공지 및 댓글 CRUD에 맞춰 캐시 무효화 시그널을 구현한다.
3. 문서와 테스트로 캐시 전략과 회귀 여부를 확인한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 공지 목록/상세에 LocMemCache(300초)를 적용하고 검색어별 키 및 조회수 예외 처리를 포함한 버전 기반 무효화 전략을 구성했습니다.
- Notice/NoticeComment 변경 시 캐시 버전을 갱신하고 조회수 증가만 발생한 저장은 건너뛰도록 시그널을 작성했습니다.
- 테스트: PYTHONPATH=/tmp/dotenv_stub python3 manage.py test myshop stores boards 명령이 환경설정 부재로 중단되어, 로컬에서 SECRET_KEY/DB 등을 세팅한 뒤 재실행해야 합니다.
<!-- SECTION:NOTES:END -->
