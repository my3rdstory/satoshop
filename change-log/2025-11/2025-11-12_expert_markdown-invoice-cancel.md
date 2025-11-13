## 개요
- Expert 계약 초안에서 MarkdownRenderer를 직접 로드해 다단 목록 등 고급 마크다운이 실시간 미리보기로 동일하게 렌더링되도록 수정
- 계약 검토/초대 단계 라이트닝 결제 위젯의 인보이스 취소·만료 처리를 전용 JS 컨트롤러로 이관해 위젯 영역만 즉시 갱신하고 세션 인보이스 상태를 초기화하도록 개선

## 상세
1. `expert/templates/expert/contract_draft.html`에 `css/js/markdown-renderer`를 추가해 EasyMDE 입력 프리뷰와 최종 계약서 본문 간 표현 차이를 제거
2. `expert/templates/expert/partials/lightning_payment_box.html`의 HTMX 의존성을 제거하고 `data-payment-action` 버튼으로 통일
3. `expert/static/expert/js/direct_payment.js`에 결제 위젯 액션 전용 fetch 흐름을 구현해 인보이스 생성/취소 후에도 동일 DOM을 유지하며, 만료·취소 시 세션 상태를 즉시 갱신
4. 운영 문서(`README.md`)에 새 마크다운 미리보기/인보이스 취소 UX를 기록하고, `todo.md`에 작업 이력을 반영
