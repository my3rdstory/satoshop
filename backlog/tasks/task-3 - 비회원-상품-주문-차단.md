---
id: task-3
title: 비회원 상품 주문 차단
status: Done
assignee:
  - '@codex'
created_date: '2025-09-24 06:50'
updated_date: '2025-09-24 10:13'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
비회원 장바구니 세션 유지 문제로 인해 주문 안정성이 떨어집니다.
로그인 사용자만 상품을 담고 주문할 수 있도록 정책을 변경합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 로그인하지 않은 사용자가 상품 장바구니 추가를 시도하면 로그인 안내가 노출된다.
- [x] #2 로그인한 사용자는 기존 흐름대로 장바구니 추가와 주문이 가능하다.
- [x] #3 모바일과 데스크톱 공통 UI에서 비회원 제한 메시지를 확인할 수 있다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 서버 add_to_cart 및 주문 관련 엔드포인트에 로그인 검사를 추가한다.
2. 비회원이 상품 상세/장바구니 UI에서 버튼을 누르면 로그인 유도 메시지를 표시한다.
3. 기존 로그인 사용자 플로우를 검증하고 필요한 테스트를 보완한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- 비회원 장바구니/주문 접근을 모두 로그인 전용으로 전환했습니다.
- 상품 상세 및 장바구니 UI에 로그인 안내와 버튼을 추가했습니다.
- 게스트 차단 및 로그인 사용자 성공 시나리오 테스트를 작성했습니다.
- pytest는 python 실행 환경 부재로 로컬 확인하지 못했습니다.
<!-- SECTION:NOTES:END -->
