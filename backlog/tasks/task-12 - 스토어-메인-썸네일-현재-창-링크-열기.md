---
id: task-12
title: 스토어 메인 썸네일 현재 창 링크 열기
status: Done
assignee:
  - '@assistant'
created_date: '2025-09-25 06:49'
updated_date: '2025-09-25 06:54'
labels:
  - frontend
  - store
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토어 메인 화면에서 노출되는 상품/컬렉션 썸네일을 클릭하면 새 탭이 아닌 현재 창에서 상세 페이지로 이동하도록 수정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스토어 메인 화면의 썸네일 링크가 target 속성 없이 현재 창에서 이동한다.
- [x] #2 모바일/데스크톱 템플릿 모두 동일한 동작을 보장한다.
- [x] #3 회귀 테스트 또는 수동 확인 방법이 정리된다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 스토어 메인 데스크톱/모바일 템플릿에서 썸네일 링크 구조를 확인한다.
2. target 설정 및 새창 관련 스크립트를 제거하거나 수정하여 현재 창에서 열리도록 변경한다.
3. 데스크톱/모바일 화면에서 수동 확인 방법을 정리하고 AC를 점검한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 라이브 강의 카드(썸네일/제목/상세보기 버튼)에서 target="_blank" 속성을 제거해 스토어 메인에서도 현재 창에서 상세 페이지가 열리도록 통일했습니다.
- 다른 섹션(상품/밋업/디지털 파일)은 기존과 동일하며 링크 동작만 통합되었습니다.

테스트:
1. (수동) 스토어 상세 페이지 접속 → 라이브 강의 섹션에서 썸네일과 제목, 상세보기 버튼을 차례로 클릭해 동일 탭에서 상세 페이지가 열리는지 확인.
2. (수동) 스토어 소유자 뷰(is_public_view=False)로 진입해 동일 링크들이 현재 창에서 이동하는지 확인.
<!-- SECTION:NOTES:END -->
