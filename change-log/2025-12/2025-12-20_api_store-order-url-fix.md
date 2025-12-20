## 배경
- API URL 경고로 인해 `store_create_order` 경로가 올바르게 파싱되지 않는 문제가 확인됨.

## 변경 사항
- `api/urls.py`의 `v1/stores/<str:store_id}/orders/` 패턴에서 누락된 `>`를 보정.

## 영향
- 스토어 주문 생성 API 라우트가 정상 등록되어 Django URL 경고가 해소됨.

## 대장 수동 테스트 가이드
1. 서버 재기동 후 `uv run python manage.py show_urls | rg "store_create_order"`로 URL 패턴을 확인.
2. `/api/v1/stores/<store_id>/orders/` 요청이 정상적으로 라우팅되는지 확인.
