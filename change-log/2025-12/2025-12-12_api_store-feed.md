# api · 스토어 공개 피드 API

## 요약
- 장고 어드민에 해시 저장 방식의 API 키 모델을 추가하고 Bearer 스킴으로 인증하도록 구성했습니다.
- `/api/v1/stores/`에서 활성 스토어와 주인장 연락처, 활성 상품·밋업·라이브 강의·디지털 파일 목록을 JSON으로 제공하도록 엔드포인트를 추가했습니다.
- README에 인증/경로/응답 예시와 운영·보안 권장사항을 정리했습니다.
- IP 허용 목록·Origin 허용 목록을 어드민에서 관리하도록 추가해 IP/CORS 기반 접근 제어를 설정할 수 있습니다.
- `/api/v1/`로 호출 시 사용 가능한 엔드포인트 목록을 JSON으로 안내하도록 인덱스 응답을 추가했습니다.
- `/api/v1/stores/{store_id}/owner/`에서 스토어별 주인장 정보만 조회하는 엔드포인트를 추가하고 Explorer에 파라미터 입력 UI를 붙였습니다.
- `/api/v1/docs/`에서 Swagger UI로 OpenAPI 스펙을 확인하고 Try it 기능을 사용할 수 있게 했습니다.
- Explorer/RapiDoc 경로를 제거하고 Swagger UI만 남겼습니다.
- 스토어별 활성 아이템을 종류별로 조회하는 엔드포인트를 추가했습니다: `/stores/{store_id}/products|meetups|live-lectures|digital-files/`.
- 장바구니 없이 주문을 생성하는 `POST /stores/{store_id}/orders/` API를 추가해 외부 앱에서 바로 주문을 남길 수 있도록 했습니다.
- API 키에 `channel_slug`를 설정하면 주문의 `channel` 필드에 자동 태깅되어 채널별 집계가 가능하도록 했습니다.
