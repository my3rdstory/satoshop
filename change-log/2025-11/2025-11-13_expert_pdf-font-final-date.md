## 개요
- 계약 PDF가 시스템 폰트에 의존하면서 한글이 깨지는 문제를 해결하기 위해 Noto Sans KR을 CSS 차원에서 직접 임베드하고 기본 폰트 스택을 재정비
- 계약 보관함 테이블에 "최종 계약일" 컬럼을 추가해 서명·최종 PDF 생성 시각을 초 단위까지 확인 가능하도록 개선

## 상세
1. `expert/static/expert/fonts/`에 Noto Sans KR 번들을 배치하고, `expert/static/expert/css/contract_pdf.css`에서 해당 경로를 `@font-face`로 불러 PDF에서도 동일한 폰트가 적용되도록 함(`EXPERT_FONT_DIR` 기본값도 동일 폴더를 바라보도록 조정).
2. `expert/models.py`에 `DirectContractDocument.get_finalized_at()` 헬퍼를 추가해 서명/최종 PDF 생성 타임스탬프 중 가장 최근 값을 계산하고, `expert/templates/expert/contract_library.html`에 새로운 컬럼을 렌더링해 `Y-m-d H:i:s` 포맷으로 노출.
