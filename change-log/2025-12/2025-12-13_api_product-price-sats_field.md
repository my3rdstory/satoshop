# api · 상품 가격 사토시 필드 추가

## 요약
- 원화 연동 상품(`price_display=krw`)은 API 응답의 `price`가 원화로 내려가 외부 앱이 이를 사토시로 오해할 수 있어, 결제/정산용 사토시 금액을 별도 필드로 제공하도록 개선했습니다.
- `GET /api/v1/stores/{store_id}/products/` 응답에 `price_sats`, `discounted_price_sats`, `price_mode`를 추가했습니다.
- Swagger 스펙(`api/static/api/openapi-v1.json`)과 `README.md` 외부 API 섹션에 사용 가이드를 반영했습니다.

