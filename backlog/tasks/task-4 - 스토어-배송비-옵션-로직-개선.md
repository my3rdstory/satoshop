---
id: task-4
title: 스토어 배송비 옵션 로직 개선
status: Done
assignee:
  - '@codex'
created_date: '2025-09-24 10:25'
updated_date: '2025-09-24 11:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토어 공통 배송비 설정을 무료/유료 선택 및 조건 무료 한도, 상품별 강제 무료 옵션까지 지원하도록 로직을 확장한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스토어 관리 화면에서 배송비 옵션을 무료/유료로 설정할 수 있다.
- [x] #2 무료로 설정된 스토어는 모든 상품과 주문에서 배송비가 0 사토시로 노출되고 적용된다.
- [x] #3 유료 선택 시 스토어 관리에서 입력한 기본 배송비(원화 기준)가 사토시로 환산되어 상품 소개 및 최종 결제에 반영된다.
- [x] #4 유료 선택 시 조건부 무료 한도를 원화로 입력할 수 있고, 환산 금액 이상 주문에는 배송비가 0 사토시로 적용된다.
- [x] #5 상품 등록/수정 폼은 스토어의 기본 배송비 옵션을 기본값으로 사용한다.
- [x] #6 유료 배송비 설정이라도 개별 상품의 "무조건 배송비 무료" 옵션을 활성화하면 해당 상품의 배송비가 0 사토시로 계산된다.
- [x] #7 주문 생성 및 결제 금액 계산 로직이 새로운 배송비 정책을 일관되게 반영한다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Product 모델에 스토어 공통 배송비를 무시할 수 있는 force_free_shipping 필드를 추가하고 마이그레이션을 생성한다.
2. 상품 등록/수정 뷰와 템플릿에서 스토어 배송 정책 요약과 무조건 무료 옵션을 노출하고, 상품 상세/목록/폼에서 배송비 표시 로직을 스토어 기본값과 연동한다.
3. 장바구니 및 주문 금액 계산 시 강제 무료 상품만 담긴 경우 배송비를 0으로 처리하도록 로직을 보강하고, 관련 테스트를 추가한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Product 모델에 force_free_shipping 필드와 마이그레이션을 추가하고, 배송비 관련 프로퍼티들이 스토어 기본 배송비를 무시하도록 보완했습니다.
- 상품 등록/수정 폼과 상세·목록 화면, 체크아웃 템플릿 및 관련 JS를 갱신해 무조건 무료 배송 옵션과 안내 메시지를 노출합니다.
- 장바구니/주문 계산 로직이 상품별 무료 배송 여부를 전달하도록 변경하고 calculate_store_totals 및 상품 프로퍼티에 대한 단위 테스트를 작성했습니다.
- 로컬 sandbox에는 python-dotenv 패키지가 없어 Django 명령을 실행하지 못해 테스트를 수행하지 못했습니다; 종속성을 설치한 후 `python3 manage.py test orders.tests.ShippingOverrideTests` 등을 실행해주세요.
<!-- SECTION:NOTES:END -->
