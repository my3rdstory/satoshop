---
id: task-24
title: Blink 결제 로직 공통화 및 모듈화
status: To Do
assignee: []
created_date: '2025-09-29 05:59'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
현재 Blink 기반 결제는 meetup, file, menu, lecture 등 각 도메인 앱에서 개별적으로 인보이스 생성과 결제 확인 로직을 구현하고 있다. Blink 서비스 헬퍼만 공유하고 주문 생성·세션 처리·상태 업데이트는 중복되어 유지 보수 비용과 결제 정책 불일치 위험이 존재한다. 공통 결제 모듈을 도입해 인보이스 생성, 결제 상태 확인, 주문 트리거, 세션·데이터 스냅샷 저장 등을 일관되게 처리하도록 구조화해야 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 결제 플로우 공통화를 위한 서비스 또는 모듈 레이어를 설계하고, 인보이스 생성/상태 확인/취소 등 Blink 연동 로직이 단일 진입점을 갖도록 한다.
- [ ] #2 meetup, file, menu, lecture, orders 등의 앱에서 사용 중인 결제 호출 지점을 공통 모듈로 이관해 중복 코드를 제거하고, 도메인별 주문 생성 훅만 주입하는 방식으로 정리한다.
- [ ] #3 공통 모듈이 세션/주문 스냅샷/로그 수집 등 결제 상태 추적 정보를 일관되게 제공해 이후 서버 주도 결제 전환이나 재조정 작업과 연동 가능하도록 한다.
<!-- AC:END -->
