# api · 4종 아이템 설명(description) 필드 추가

## 요약
- 외부 앱에서 상세/리스트 화면에 설명을 표시할 수 있도록, 4종 아이템 API 응답에 `description` 필드를 추가했습니다.
- 대상:
  - 상품 `GET /api/v1/stores/{store_id}/products/`
  - 밋업 `GET /api/v1/stores/{store_id}/meetups/`
  - 라이브 강의 `GET /api/v1/stores/{store_id}/live-lectures/`
  - 디지털 파일 `GET /api/v1/stores/{store_id}/digital-files/`
- Swagger 스펙(`api/static/api/openapi-v1.json`)과 `README.md`도 동기화했습니다.

