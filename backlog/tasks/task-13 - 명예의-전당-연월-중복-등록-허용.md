---
id: task-13
title: 명예의 전당 연월 중복 등록 허용
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 07:06'
updated_date: '2025-09-25 07:08'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Hall of Fame 업로드가 연도와 월 조합당 하나의 이미지만 허용되어 운영팀이 동일 연·월에 여러 이미지를 게시하지 못하고 있습니다. 연·월을 태그처럼 사용해 중복 등록을 허용하고, 관련 백엔드/프론트 제약을 정리해 동일 조합으로도 문제없이 업로드할 수 있도록 해주세요.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 HallOfFame 모델에서 year/month 조합의 DB 고유 제약이 제거되고 마이그레이션이 적용된다.
- [x] #2 생성 뷰와 관련 API에서 연/월 중복을 차단하지 않아 동일 조합으로도 업로드가 성공한다.
- [x] #3 Hall of Fame 업로드 화면에서 연/월 중복 선택 시 차단 메시지가 뜨지 않고 정상적으로 제출된다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. HallOfFame 모델의 year/month 고유 제약을 제거하고 마이그레이션을 생성한다.
2. 생성 뷰 및 중복 확인 API 로직을 중복 허용 방식으로 수정하고 불필요한 검사를 정리한다.
3. 업로드 화면 스크립트에서 중복 차단 경고를 제거해 동일 연·월로도 제출이 가능하도록 확인한다.
4. 마이그레이션 적용/수동 확인 절차를 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- HallOfFame 모델에서 year/month 고유 제약을 제거하고 0013 마이그레이션을 추가했습니다.
- 생성 뷰의 중복 차단 분기를 없애고 check API는 기존 등록 수(count)를 함께 돌려주도록 보완했습니다.
- 업로드 화면 스크립트의 중복 검사 fetch를 제거해 동일 연·월도 선택 후 바로 업로드할 수 있습니다.
- 테스트: UV_CACHE_DIR=.uv-cache uv run python manage.py check
- 마이그레이션 적용: UV_CACHE_DIR=.uv-cache uv run python manage.py migrate
- 수동 확인: 업로드 페이지에서 같은 연·월로 이미지를 두 번 등록하고 목록/필터에서 모두 표시되는지 확인.
<!-- SECTION:NOTES:END -->
