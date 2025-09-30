---
id: task-25
title: 주문 생성 시각 KST 표시 보정
status: Done
assignee:
  - '@codex'
created_date: '2025-09-29 08:49'
updated_date: '2025-09-29 08:53'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub issue #133에서 보고된 주문 생성 시간이 이메일·마이페이지·어드민에서 UTC로 노출되는 문제를 해결합니다. 모든 출력 경로에서 Asia/Seoul 기준 시간이 보이도록 보정합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TXT/이메일 주문서에 노출되는 주문/결제/생성 시간이 KST와 일치한다.
- [x] #2 주문 관련 CSV/엑셀 내보내기와 관리 화면에서 주문 생성 시간이 KST 기준으로 표시된다.
- [x] #3 시간 문자열 생성 시 timezone.localtime을 사용하도록 회귀 테스트(수동 확인 지침 포함)를 남긴다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 주문 관련 포맷터·CSV·어드민에서 UTC 기준으로 출력되는 부분을 점검한다.
2. timezone.localtime을 사용해 주문/결제/생성 시간을 KST로 출력하도록 코드와 헬퍼를 보정한다.
3. 주요 화면(이메일, CSV/엑셀, 어드민, 마이페이지)에서 수동 확인 시나리오를 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 주문 포맷터와 CSV/엑셀/어드민 내보내기에서 생성·결제 시각을 timezone.localtime으로 변환하도록 일괄 보정했습니다.
- 주문서 이메일(txt/html), 주문 내보내기 스크립트, 메뉴·밋업·강의 관련 관리자 도구의 시간 표시도 동일하게 로컬 타임존을 적용했습니다.
- 리뷰 본문/미리보기에는 긴 URL이 모바일에서 줄바꿈되도록 break-words 클래스를 추가했습니다.
- 수동 확인: 1) 주문 생성 후 주문서 이메일/다운로드 TXT에서 시간이 KST로 표시되는지 확인, 2) 스토어/상품 주문 CSV와 밋업/강의/메뉴 관련 관리자 다운로드에서 타임스탬프가 KST인지 검증.
<!-- SECTION:NOTES:END -->
