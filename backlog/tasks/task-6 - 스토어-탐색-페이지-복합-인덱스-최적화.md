---
id: task-6
title: 스토어 탐색 페이지 복합 인덱스 최적화
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 05:27'
updated_date: '2025-09-25 05:32'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토어 탐색 뷰에서 최근 주문 및 콘텐츠 데이터를 불러올 때 정렬 칼럼에 대한 복합 인덱스가 없어 추가 정렬 비용이 발생합니다. 활성 스토어 추천 영역의 조회 속도를 높이기 위해 관련 모델에 필요한 복합 인덱스를 추가합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Order 모델에 status+created_at 조합 인덱스가 추가되어 있어야 한다
- [x] #2 FileOrder 모델에 status+confirmed_at 조합 인덱스가 추가되어 있어야 한다
- [x] #3 MeetupOrder와 LiveLectureOrder 모델에 store 기준 최신 조회를 위한 복합 인덱스가 추가되어 있어야 한다
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 관련 모델(Order, FileOrder, MeetupOrder, LiveLectureOrder)에 필요한 복합 인덱스 정의 추가
2. makemigrations로 인덱스 마이그레이션 생성 및 변경 사항 검토
3. migrate 및 Django 검사/테스트로 문제 없는지 확인
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- orders, file, meetup, lecture 모델에 복합 인덱스 메타 정의를 추가하고 이름을 고정했습니다.
- 각각의 앱에 대해 인덱스 추가용 마이그레이션을 생성했습니다.
- system check는 통과했고, migrate는 로컬 DB 연결(OperationalError) 문제로 수행하지 못했습니다.
<!-- SECTION:NOTES:END -->
