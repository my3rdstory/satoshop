# api · 밋업/라이브 강의/디지털 파일 가격 필드 통일

## 요약
- 상품 API와 동일하게, 밋업/라이브 강의/디지털 파일 API 응답도 “가격 모드/표시 가격/결제 가격(사토시)”를 명확히 분리한 필드 체계로 통일했습니다.
- 대상 엔드포인트:
  - `GET /api/v1/stores/{store_id}/meetups/`
  - `GET /api/v1/stores/{store_id}/live-lectures/`
  - `GET /api/v1/stores/{store_id}/digital-files/`
- 적용 필드:
  - `pricing_mode`
  - `display_currency`, `display_price`, `display_discounted_price`
  - `pay_price_sats`, `pay_discounted_price_sats`
- Swagger 스펙(`api/static/api/openapi-v1.json`)과 `README.md` 안내를 갱신했습니다.

