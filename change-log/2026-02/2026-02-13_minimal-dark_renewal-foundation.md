# 2026-02-13 minimal-dark 리뉴얼 기반 정비

## 변경 개요
- `SATOSHOP_THEME=minimal-dark` 실행 시 주문/결제/배송지/장바구니 및 주문관리, 스토어 상세/상품/밋업/라이브강의/파일 상세 화면, 마이페이지·스토어관리 메뉴의 테마 기반 정합성을 정비했습니다.
- 기존 라이트/다크 토글 아이콘 동작을 Font Awesome 의존성 없이 Feather 아이콘으로 처리되는 방식에 맞춰 정비했습니다.
- 모바일 메뉴(메인/스토어) 접근성/토글 동작을 보강하고 모바일 터치 동작에 맞춰 기본 터치 영역을 보정했습니다.
- `todo.md` 항목(주문결제/상세/마이페이지/스토어관리, 정적 자산 보강, README 반영)을 완료 처리했습니다.

## 작업 범위
- `themes/minimal-dark/templates/*` 주요 페이지 템플릿 정비
- `themes/minimal-dark/static/{css,js}` 정적 자산 정렬 및 보강
- `static/js/theme-toggle.js`의 Feather 아이콘 토글 정합성 강화
- 모바일 반응형 유틸리티(`theme-utils.css`)의 `md:`/`sm:` 반응형 유틸리티 오류 보정
- `myshop_base.js`, `store_base.js`의 모바일 메뉴 접근성(aria/키보드/스크롤 잠금) 보강

## 확인 항목
- 화면 점검: 장바구니, 배송정보, 결제준비, 주문관리, 상세/상세결제 계열, 마이페이지, 스토어 관리 메뉴 페이지
- 실행 명령: `SATOSHOP_THEME=minimal-dark uv run python manage.py runserver`
