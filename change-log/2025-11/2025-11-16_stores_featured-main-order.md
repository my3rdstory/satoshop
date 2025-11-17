# 스토어 메인 노출 우선순위 편집

- `stores.constants`와 `StoreFeaturedItem` 모델/마이그레이션을 추가해 상품·밋업·라이브 강의·디지털 파일의 대문 노출 순서를 저장할 수 있게 했습니다.
- `stores/featured_services.py`를 도입해 활성 항목 직렬화, 노출 순서 저장, 스토어 상세 화면 보조 로직을 캡슐화했습니다.
- `/stores/edit/<store_id>/featured-display/` 화면과 연결된 JS/CSS(`static/{css,js}/edit_featured_display.*`)를 구현해 클릭 순서+위/아래 컨트롤 방식으로 우선순위를 지정하고 즉시 상태를 확인할 수 있도록 구성했습니다.
- 스토어 대문(`store_detail`)은 저장된 우선순위를 우선 반영하고 남은 슬롯은 기존 최신순 로직으로 채우도록 변경했으며, README에 메인 노출 관리 기능을 추가로 문서화했습니다.
- 노출 순서 저장 시 기존 항목을 먼저 삭제한 뒤 새 순서로 재생성하도록 바꿔 `store_featured_unique_order` 제약 위반으로 인한 500 오류를 방지했습니다.
