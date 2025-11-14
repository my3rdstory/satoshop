# Expert 계약서 PDF 파이프라인을 ReportLab 기반으로 재구축

## 배경
- WeasyPrint 및 xhtml2pdf 모두 Cairo 의존성 때문에 Render 네이티브 환경에서 빌드 오류가 발생했습니다.
- 순수 파이썬으로 배포 가능한 PDF 파이프라인이 필요했습니다.

## 주요 변경
1. **PDF 렌더 로직**
   - `expert/contract_flow.py`가 Markdown → ReportLab(Platypus) 흐름으로 바뀌었습니다.
   - Markdown을 ElementTree로 파싱해 제목, 본문, 목록, 표를 Flowable로 변환하고 `SimpleDocTemplate`으로 PDF를 생성합니다.
   - 기존 `resolve_contract_pdf_font()`를 활용해 등록된 TTF/OTF 폰트를 그대로 사용합니다.
2. **불필요 자산 제거**
   - 더 이상 HTML 템플릿과 CSS가 필요 없어 `expert/templates/expert/contract_pdf.html`, `expert/static/expert/css/contract_pdf.css`를 삭제했습니다.
3. **문서화**
   - README를 업데이트해 새로운 ReportLab 파이프라인과 설치 방법을 안내했습니다.

## 결과
- Render 네이티브 환경에서도 추가 시스템 패키지 없이 계약서를 PDF로 생성할 수 있습니다.
- 레이아웃은 단순하지만 제목, 본문, 목록, 표 등 핵심 요소는 안정적으로 렌더링됩니다.
