# Expert 계약 템플릿/PDF 정리

- `expert/contracts/good_faith_private_contract.md`를 최종본 Markdown 양식으로 재작성해 시스템 안내, 역할 정의, 서명 절차를 한글 목차 구조로 정리했습니다.
- README의 Expert 계약서 섹션을 업데이트해 최종 템플릿과 PDF 출력 품질 개선 내용을 명시했습니다.
- ReportLab PDF 렌더러가 긴 문장을 자동 줄바꿈하도록 텍스트 폭 계산 로직을 추가하고, 의뢰자 라이트닝 주소 노출을 제거했습니다.
- PDF 하단 서명 블록을 `중개자(시스템)` 명칭으로 통일하고, PDF 생성 이전에 중개자 해시를 계산해 누락 없이 삽입되도록 했습니다.
