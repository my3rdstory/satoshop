# 2026 SatoShop 리뉴얼 지침 (엑스퍼트/봇/미니홈 제외)

## 최우선 규칙 (필독)
- 이번 리뉴얼 범위에서는 **DB 스키마/모델/마이그레이션 변경을 절대 금지**한다.
- DB는 **읽기/쓰기(테스트 데이터)**까지만 허용하며, 스키마 변경을 유도하는 코드는 절대 금지한다.
- 로컬 테마 미리보기는 **반드시 환경변수로만 실행**한다. 예: `SATOSHOP_THEME=minimal-dark uv run python manage.py runserver`

## 리뉴얼 운영 규칙 (AGENTS.md 발췌)
- 호칭/언어: 항상 사용자를 “대장”으로 부르고, 모든 산출물은 한글로 작성한다.
- 작업 방식: 플랜을 세우고 todo를 관리하며, 요청 범위를 벗어난 수정은 하지 않는다.
- 삭제/이동 금지: `rm`/`mv` 사용은 사전 승인 없이는 금지한다.
- 장고 명령: 항상 `uv run`을 사용한다. 개발 서버 재시작은 대장에게 알린다.
- 템플릿 가이드: 템플릿명과 동일한 `css/js`를 `static`에 생성, 토스트 미사용, 다크모드 대응.
- 문서화: 중요한 개선사항은 `README.md`에 업데이트하고 변경 이력은 `/change-log/YYYY-MM/`에 기록한다.
- 테스트: 자동 실행하지 않으며, 테스트 방법만 안내한다.
- 커밋: 커밋 메시지를 한 줄 한국어로 제공 후 즉시 커밋한다.

## 1) 범위와 목표
- 범위: SatoShop 메인/스토어/상품/주문/메뉴/밋업/강의/게시판 등(엑스퍼트, satoshop_bot, minihome 제외)
- 제외: `expert/`, `coupon/`, `minihome/` 앱은 별도 동작하므로 이번 리뉴얼에서 제외한다.
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
  minimal-dark/
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

## 4) 스타일 레퍼런스 (demoss-t1 기반)
- 레퍼런스: `https://demoss-t1.lovable.app/`
- 톤앤매너: 고대비 다크, 그레이스케일 위주, 장식 최소, 정보 밀도 낮게
- 컬러 토큰(HSL 기준)
  - background: `0 0% 4%` / foreground: `0 0% 98%`
  - card/popover: `0 0% 6%`
  - secondary/muted/accent: `0 0% 12%`
  - border/input: `0 0% 14%`
  - muted-foreground: `0 0% 42%`
  - destructive: `0 62% 50%`
- 타이포/리듬
  - 베이스: 14px(0.875rem), line-height 1.25, 자간 -0.01em
  - 헤딩: light(300) 중심, h1 36/40 → md 48/48, h2 24/32 → md 30/36, h3 18/28
  - 한국어 대응 폰트는 SUIT Variable 또는 Pretendard 권장(영문은 Grotesk 계열)
- 형태/레이아웃
  - radius 0 (각진 모서리), 그림자 최소, 1px 보더로 구획
  - 컨테이너 최대 폭 1400px, 좌우 패딩 24px(1.5rem)
  - 필터/태그류는 uppercase + letter-spacing 0.1em
- 컴포넌트 감성
  - 내비 링크는 muted → hover 시 foreground로 상승
  - 카드/리스트는 보더로 구분하고 hover 시 보더만 밝게

## 5) Bulma 로컬 구성 (CDN 미사용)
- Bulma 파일은 테마 정적 경로에 보관
  - `themes/minimal-dark/static/css/bulma.min.css` (현재 `static/css/bulma.min.css` 기준)
- 테마 템플릿에서는 반드시 정적 경로로 로드
  - `{% load static %}` 후 `<link rel="stylesheet" href="{% static 'css/bulma.min.css' %}">`
- 커스텀 스타일은 Bulma 로드 이후 별도 파일로 분리
  - 예: `themes/minimal-dark/static/css/theme.css`
- 외부 CDN 링크는 사용하지 않는다

## 6) Bulma 전환 전략
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

## 7) 리스크 및 주의점
- Tailwind 클래스가 전면적으로 박혀 있어 Bulma 전환은 마크업 대규모 수정이 필요
- 독립 템플릿(메뉴판 등)은 베이스 교체 영향이 없으므로 별도 전환 작업이 필요
- PWA 관련 경로는 `myshop/templates/myshop/components/pwa.html`과 `myshop/templatetags/static_versioned.py`에 고정되어 있어 테마별 manifest/icon 분리가 필요하면 추가 설계 필요

## 8) 실행 순서(권장)
1. 테마 디렉터리 구조 생성 및 설정 반영
2. 베이스 템플릿 Bulma화 (플랫폼/스토어)
3. 공통 컴포넌트 정리(nav/footer/공통 UI)
4. 페이지별 Bulma 전환(우선순위 높은 화면부터)
5. 독립 템플릿(메뉴판 등) 리뉴얼
6. PWA/정적 캐시 전략 재정리

## 9) 결정 필요 사항
- 테마 전환은 빌드 단위 전환으로 충분한가? (런타임 전환 필요 시 템플릿 태그/로더 재설계 필요)
- `game/` 앱도 Bulma 전환 범위에 포함할지 여부
- PWA manifest/icon을 테마별로 분리할지 여부

## 10) 체크리스트
- [ ] `themes/<theme>/templates`/`static` 구조 도입
- [ ] `TEMPLATES[DIRS]`, `STATICFILES_DIRS` 우선순위 반영
- [ ] 베이스 템플릿 Bulma화 완료
- [ ] 공통 UI 컴포넌트 Bulma화 완료
- [ ] 페이지별 마크업 Bulma 전환 완료
- [ ] 독립 템플릿 리뉴얼 완료
- [ ] PWA/정적 캐시 전략 문서화
