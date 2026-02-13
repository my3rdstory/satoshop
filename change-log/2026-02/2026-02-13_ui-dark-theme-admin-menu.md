# 다크모드 고정 및 스토어 관리 허브 통합

- `themes/minimal-dark`의 공통 레이아웃에서 런타임 테마 토글 로직을 제거하고 다크모드만 사용하도록 정렬했습니다.
  - `themes/minimal-dark/templates/myshop/base.html`
  - `themes/minimal-dark/templates/stores/store_base.html`
  - `themes/minimal-dark/static/js/myshop_base.js`
  - `themes/minimal-dark/templates/myshop/nav_bar.html`
  - `themes/minimal-dark/templates/myshop/mobile_menu.html`
  - `themes/minimal-dark/templates/stores/store_nav_bar.html`
  - `themes/minimal-dark/templates/stores/store_mobile_menu.html`
- 스토어 주인장 관리자 메뉴를 한 파일로 통합해 카테고리형 허브로 재배치했습니다.
  - `themes/minimal-dark/templates/stores/store_menu_component.html`
- 모바일에서는 관리 하위 메뉴를 개별 분산 링크에서 허브 진입 링크로 축소해 진입 경로를 일원화했습니다.
  - `themes/minimal-dark/templates/stores/store_mobile_menu.html`
- 사용자 안내 및 변경 이력 문서도 동기화했습니다.
  - `README.md`
  - `todo.md`
