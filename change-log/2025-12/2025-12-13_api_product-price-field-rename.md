# api · 상품 가격 필드 명확화(표시/결제 분리)

## 요약
- 원화 연동 상품에서 `price`가 표시값(원화)로 내려가 외부 앱이 결제 금액(사토시)으로 오해하기 쉬워, “표시용”과 “결제용” 필드를 명확히 구분하는 새 필드명을 추가했습니다.
- `GET /api/v1/stores/{store_id}/products/` 응답에 `pricing_mode`, `display_currency`, `display_price`, `display_discounted_price`, `pay_price_sats`, `pay_discounted_price_sats`를 추가했습니다.
- 기존 호환을 위해 `price*`, `discounted_price*` 필드는 유지하되, 문서에서는 새 필드 사용을 권장합니다.

