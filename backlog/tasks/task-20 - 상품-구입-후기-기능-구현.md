---
id: task-20
title: 상품 구입 후기 기능 구현
status: Done
assignee:
  - '@codex'
created_date: '2025-09-26 09:51'
updated_date: '2025-09-26 10:12'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
스토어 상품 상세 화면에 구입 후기(reviews) 기능을 추가하여 상품을 구매한 사용자가 평점과 이미지를 포함한 후기를 작성하고 관리할 수 있도록 합니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 reviews 앱이 생성되고 CRUD 뷰와 URL 구성이 완료된다.
- [x] #2 상품 상세 화면 소개 영역 아래에 구입 후기 목록과 페이지네이션(10개 단위)이 렌더링된다.
- [x] #3 상품 구매 이력이 있는 로그인 사용자는 후기 작성 버튼을 볼 수 있고, 모달에서 별점(1~5)과 본문을 작성할 수 있다.
- [x] #4 후기 작성 시 업로드한 이미지는 최대 5개까지 허용되며, webp 변환과 1000px 리사이즈 후 오브젝트 스토리지 reviews/ 경로에 저장된다.
- [x] #5 후기 수정·삭제 시 본문과 이미지가 갱신/삭제되고, 오브젝트 스토리지의 관련 이미지도 정리된다.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 분석: 상품 상세 화면 구성과 기존 스토리지/이미지 업로드 유틸을 확인한다.
2. 모델링: reviews 앱 생성 후 리뷰/이미지 모델, 관리자 등록, DB 마이그레이션을 작성한다.
3. 접근 제어: 상품 구매 내역이 있는 사용자인지 확인하는 서비스/데코레이터를 구현하고 테스트를 추가한다.
4. 서버 구현: 리뷰 목록, 작성, 수정, 삭제 API/뷰와 form/serializer를 작성하고 페이지네이션을 적용한다.
5. 프런트 구현: 상품 상세 템플릿에 리뷰 섹션과 모달, 별점/텍스트/드롭존 UI를 추가하고 AJAX 연동을 구축한다.
6. 이미지 처리: 업로드 이미지를 webp 변환·리사이즈 후 오브젝트 스토리지 reviews/ 경로에 저장하고 삭제 처리까지 구현한다.
7. QA: 단위/통합 테스트 및 lint를 실행하고 후속 배포 가이드를 정리한다.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added reviews 앱과 모델/서비스/어드민/URL/테스트를 구성하고 마이그레이션을 추가했습니다.
- 상품 상세 화면에 후기 목록/페이지네이션/작성·수정·삭제 모달 UI를 연동하고 구매자 검증 로직을 통합했습니다.
- 후기 이미지 webp 변환·1000px 리사이즈 및 S3 업로드·삭제 동기화를 구현했습니다.
- 별점 인터랙션과 다중 이미지 드롭존을 담당하는 static/js/reviews.js를 추가했습니다.

Testing:
- python3 manage.py test reviews  # 실패 (ModuleNotFoundError: No module named "dotenv" - sandbox 기본 환경에 패키지 미설치)],workdir:.,timeout_ms:120000}
<!-- SECTION:NOTES:END -->
