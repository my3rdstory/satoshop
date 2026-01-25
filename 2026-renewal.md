# 2026 SatoShop 리뉴얼 지침 (엑스퍼트/봇/미니홈 제외)

## 1) 범위와 목표
- 범위: SatoShop 메인/스토어/상품/주문/메뉴/밋업/강의/게시판 등(엑스퍼트, satoshop_bot, minihome 제외)
- 목표: 테마 디렉터리 구조로 리뉴얼을 쉽게 하고, Bulma 기반으로 스타일링 전환
- 결과: 테마 파일만 교체해 전체 리뉴얼이 가능하도록 설계

## 2) 현재 구조 요약
- 베이스 템플릿 축
  - 플랫폼: `myshop/templates/myshop/base.html`
  - 스토어: `stores/templates/stores/store_base.html`
- 독립 템플릿(베이스 미사용)
  - 메뉴판/모바일 메뉴판 등: `menu/templates/menu/menu_board_desktop.html`, `menu/templates/menu/menu_board_mobile.html`, `menu/templates/menu/menu_detail_desktop.html`, `menu/templates/menu/menu_detail_mobile.html` 등
- CSS/JS 분포
  - 전역 정적: `static/` 중심, `STATICFILES_DIRS`는 `static`만 포함
  - 앱별 정적은 일부 앱에만 존재(`api`, `expert`, `game`, `minihome`)
- Tailwind 중심 + 다크모드 스크립트 유지
  - Tailwind CDN 사용 템플릿 다수
  - 테마 토글: `static/js/theme-toggle.js`
  - 테마 변수: `static/css/themes.css` (Bulma 변수 오버라이드 포함)

## 3) 테마 구조 제안 (빌드 단위 전환)
- 디렉터리 구조
```
themes/
  2026/
    templates/
      myshop/
      stores/
      products/
      orders/
      menu/
      meetup/
      lecture/
      boards/
      file/
      accounts/
    static/
      css/
      js/
      images/
```
- 설정 반영(우선순위는 테마가 먼저)
  - `TEMPLATES["DIRS"]`에 `themes/<theme>/templates`를 앞에 추가
  - `STATICFILES_DIRS`에 `themes/<theme>/static`을 앞에 추가
- 효과
  - 템플릿/정적 파일 경로를 바꾸지 않고도 테마 폴더의 동일 경로 파일이 우선 적용
  - 리뉴얼 시 테마 폴더만 교체하면 전체 변경 가능

## 4) Bulma 전환 전략
- 1차 전환 대상(공통 뼈대)
  - `myshop/templates/myshop/base.html`
  - `myshop/templates/myshop/nav_bar.html`
  - `myshop/templates/myshop/footer.html`
  - `stores/templates/stores/store_base.html`
  - `stores/templates/stores/store_nav_bar.html`
- 2차 전환 대상(페이지 별 마크업)
  - Tailwind 클래스 기반 모든 템플릿
  - 독립 템플릿(메뉴판 계열)은 별도 리뉴얼 트랙으로 분리
- 참고
  - `static/css/themes.css`에 Bulma 변수 오버라이드가 이미 존재하므로, Bulma 기반 다크모드 적용은 연속성 확보 가능

## 5) 리스크 및 주의점
- Tailwind 클래스가 전면적으로 박혀 있어 Bulma 전환은 마크업 대규모 수정이 필요
- 독립 템플릿(메뉴판 등)은 베이스 교체 영향이 없으므로 별도 전환 작업이 필요
- PWA 관련 경로는 `myshop/templates/myshop/components/pwa.html`과 `myshop/templatetags/static_versioned.py`에 고정되어 있어 테마별 manifest/icon 분리가 필요하면 추가 설계 필요

## 6) 실행 순서(권장)
1. 테마 디렉터리 구조 생성 및 설정 반영
2. 베이스 템플릿 Bulma화 (플랫폼/스토어)
3. 공통 컴포넌트 정리(nav/footer/공통 UI)
4. 페이지별 Bulma 전환(우선순위 높은 화면부터)
5. 독립 템플릿(메뉴판 등) 리뉴얼
6. PWA/정적 캐시 전략 재정리

## 7) 결정 필요 사항
- 테마 전환은 빌드 단위 전환으로 충분한가? (런타임 전환 필요 시 템플릿 태그/로더 재설계 필요)
- `game/` 앱도 Bulma 전환 범위에 포함할지 여부
- PWA manifest/icon을 테마별로 분리할지 여부

## 8) 체크리스트
- [ ] `themes/<theme>/templates`/`static` 구조 도입
- [ ] `TEMPLATES[DIRS]`, `STATICFILES_DIRS` 우선순위 반영
- [ ] 베이스 템플릿 Bulma화 완료
- [ ] 공통 UI 컴포넌트 Bulma화 완료
- [ ] 페이지별 마크업 Bulma 전환 완료
- [ ] 독립 템플릿 리뉴얼 완료
- [ ] PWA/정적 캐시 전략 문서화
