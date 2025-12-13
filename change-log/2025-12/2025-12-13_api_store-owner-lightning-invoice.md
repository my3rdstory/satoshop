# api · 라이트닝 인보이스 발행 문서 추가

## 요약
- 스토어 주인장이 외부 앱 결제용 BOLT11 인보이스를 만들 수 있도록 `POST /api/v1/stores/{store_id}/lightning-invoices/` 엔드포인트를 README 외부 API 섹션에 문서화했습니다.
- 요청 필드(`amount_sats`, 선택 `memo`, `expires_in_minutes`)와 응답 필드(`payment_request`, `payment_hash`, `invoice_uri`, `expires_at`)를 예시와 함께 정리해 연동 파라미터를 명확히 했습니다.
- 스토어 주인장 전용 API 키 요구와 만료 후 재발행 시 새 해시 발급 등 보안·운영 주의사항을 문서에 포함했습니다.
- Swagger UI가 사용하는 `api/static/api/openapi-v1.json`에 라이트닝 인보이스 발행 엔드포인트 스펙을 추가해 `/api/v1/docs/`에서 바로 확인할 수 있게 했습니다.
- 라이브 강의/밋업/디지털 파일 주문 생성 API 스펙을 추가(`POST /stores/{store_id}/live-lectures/{live_lecture_id}/orders/`, `/meetups/{meetup_id}/orders/`, `/digital-files/{file_id}/orders/`)해 외부 앱에서 주문 생성 흐름을 모두 문서화했습니다.
