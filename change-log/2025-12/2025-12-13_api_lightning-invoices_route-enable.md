# api · 라이트닝 인보이스 발행 라우팅 활성화

## 요약
- `POST /api/v1/stores/{store_id}/lightning-invoices/`가 Swagger 스펙에만 있고 실제 Django URLconf에는 없어 404가 발생하던 문제를 수정했습니다.
- `api/urls.py`에 라우트를 추가하고, `api/views.py`에 인보이스 발행 뷰를 구현해 로컬에서도 엔드포인트가 응답하도록 했습니다.
- 스토어 Blink 자격 정보가 없거나 외부 호출이 실패할 때 400/502로 JSON 에러를 반환해, HTML 404/500 페이지가 길게 노출되는 상황을 줄였습니다.

