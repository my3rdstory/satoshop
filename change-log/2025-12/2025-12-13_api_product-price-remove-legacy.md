# api · 상품 가격 레거시 필드 제거

## 요약
- 외부 앱 혼동을 줄이기 위해 상품 API에서 기존 호환 필드(`price*`, `discounted_price*`)를 제거했습니다.
- 앞으로 상품 가격은 `pricing_mode`, `display_*`, `pay_*_sats` 필드만 사용합니다.
- Swagger 스펙(`api/static/api/openapi-v1.json`)과 `README.md` 가이드를 새 필드 기준으로 정리했습니다.

