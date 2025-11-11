## 변경 개요
- 라이트닝 로그인·결제 UI를 통합하고 시크릿(프라이빗) 모드 감지/차단 로직을 추가했습니다.
- Expert 계약 경험(결제 위젯, 보관함, 위변조 검증, PDF 작업 메모 등)의 모바일/가독성을 개선했습니다.
- Blink 수수료 및 Expert 사용 통계를 Django Admin·프런트 모두에서 확인할 수 있도록 통계 모듈과 대시보드를 추가했습니다.

## 상세 내용
- `static/js/lightning-login.js`, `expert/templates/expert/login_lightning.html`, `accounts/templates/accounts/lightning_login.html`에 시크릿 모드 감지/경고, 지갑 열기 스킴 보정, 카드형 UI 통일을 적용했습니다.
- `expert/templates/expert/partials/lightning_payment_box.html`과 `expert/static/expert/js/direct_payment.js`에 인보이스 복사/지갑 열기 버튼을 추가해 결제 화면에서도 동일한 경험을 제공합니다.
- `static/css/mobile_menu.css`, `expert/templates/expert/contract_library.html`, `expert/static/expert/css/contract_flow.css`, `expert/static/expert/css/contract_integrity_check.css`로 모바일 햄버거·보관함·위변조 검증에서 다크모드 및 줄바꿈 문제가 해결됐습니다.
- `expert/contract_flow.py`는 작업 메모 Markdown을 단일 카드에 묶어 PDF에 깔끔히 출력합니다.
- `expert/stats.py`에서 Expert 전용 통계를 집계하고, `expert/admin.py`·`expert/models.py`·`expert/templates/admin/expert/*.html`에 Blink 수수료/사용 통계 어드민 메뉴를 추가했습니다.
- `expert/views.py`, `expert/templates/expert/direct_contract_start.html`, `expert/static/expert/css/direct_contract_start.css`로 프런트 랜딩 카드에 계약/사용자 지표를 노출합니다.
- `README.md`에 시크릿 모드 가이드와 새 통계 화면 안내를 추가하고, `todo.md`에는 완료 항목을 체크했습니다.
