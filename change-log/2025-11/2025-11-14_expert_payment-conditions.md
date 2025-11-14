## 개요
- Expert 계약 초안/검토/초대/PDF 전반에 `지불 조건 → 기타` 선택지를 추가해 세부 조건을 수행 내역에 직접 서술하는 흐름을 지원
- 기타 선택 시 UI 안내 문구와 PDF 테이블 모두 “상세 내역 참조”로 고정 표기되어 조건 입력란이 비워진 것처럼 보이지 않도록 처리
- Django 어드민 PDF 검증 도구에 분할/일괄/기타 3종 샘플 Payload 버튼을 제공해 조건별 테이블 변화를 즉시 확인 가능

## 상세
1. `expert/forms.py`, `expert/views.py`, `expert/static/expert/js/contract_draft.js`, `expert/templates/expert/contract_draft.html`을 업데이트해 “기타” 지불 조건을 선택하면 지급 세부 입력 대신 안내 카드를 노출하고, 미사용 필드를 비운 뒤 미리보기/요약 카드에 동일 문구가 표시되도록 구성.
2. `expert/templates/expert/contract_review.html`, `expert/templates/expert/contract_invite.html`, `expert/contract_flow.py`를 수정해 최종 검토/초대 화면과 PDF 모두에서 지급 예정일/조건을 “상세 내역 참조”로 출력.
3. `expert/pdf_preview.py`, `expert/admin.py`, `expert/templates/admin/expert/pdf_preview.html`을 확장해 분할/일괄/기타 샘플 Payload JSON을 버튼으로 제공하고, README에 관련 사용법과 신규 지불 조건 옵션을 문서화.
