# api · 라이트닝 결제 확인 후 주문 생성 엔드포인트 추가

## 요약
- 외부 앱에서 라이트닝 결제(BOLT11) 완료 후, 결제 상태를 검증하고 주문을 자동 생성할 수 있도록 `POST /api/v1/stores/{store_id}/lightning-invoices/confirm-order/` 엔드포인트를 추가했습니다.
- `payment_hash`가 `paid`일 때만 주문을 생성하며, 동일 `payment_hash`로 이미 주문이 있으면 200으로 기존 주문을 반환해 중복 생성을 방지합니다.
- Swagger 스펙(`api/static/api/openapi-v1.json`)과 `README.md` 외부 API 섹션에 새 엔드포인트를 반영했습니다.

