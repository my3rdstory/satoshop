# 사토샵 최근 아이템 목록 스토어명 표시 개선

## 변경 내용
- 디스코드 슬래시 명령어 `사토샵_최근등록상품`, `사토샵_최근판매상품`의 선택 목록 설명에서 스토어 식별자를 `store_id` 대신 `store_name`으로 표시하도록 변경했습니다.
- 웹뷰(`/satoshop-bot/webview/recent-registered/`, `/satoshop-bot/webview/recent-sold/`)의 아이템 보조 텍스트에서도 스토어명을 우선 표시하도록 변경했습니다.
- URL 역참조 및 상세 링크 생성에는 기존 `store_id`를 그대로 유지해 라우팅 동작은 변경하지 않았습니다.

## 수정 파일
- `satoshop_bot/item_services.py`
- `satoshop_bot/views.py`
- `satoshop_bot/templates/satoshop_bot/recent_items_webview.html`
