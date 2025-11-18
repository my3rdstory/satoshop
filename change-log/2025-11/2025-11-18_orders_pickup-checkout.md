# 주문 현장 수령 체크아웃

- 배송 정보 입력 화면에 `현장 수령` 체크박스를 추가하고, 토글 시 배송지 입력 섹션을 숨긴 뒤 주문 메모를 필수로 받도록 JS(`static/js/shipping-info.js`)와 템플릿을 연동했습니다.
- 주문 생성/복구 경로 전반에서 `delivery_status='pickup'`을 설정해 현장 수령 주문을 구분하고, 발송 상태 토글 및 관리자 컬러 라벨에서 해당 상태를 잠그고 강조하도록 했습니다.
- 스토어 주문 목록(`orders/templates/orders/product_orders.html`)과 CSV/엑셀 내보내기(`orders/products_orders_csv_download.py`)는 현장 수령 주문을 “현장 수령”으로 표기하고 우편번호/주소 열을 비워 출력합니다.
- 결제 진행 화면과 결제 트랜잭션 상세에서 배송 정보 대신 수령 안내를 노출하며, README에 현장 수령 체크아웃 기능을 문서화했습니다.
