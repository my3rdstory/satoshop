# Expert 계약서 PDF 파이프라인을 xhtml2pdf로 전환 (시도 후 철회)

## 배경
- WeasyPrint는 Render 네이티브 환경에서 Cairo/Pango 설치가 필요해 배포마다 오류가 발생했습니다.
- 순수 파이썬으로 동작하는 렌더러가 필요해 xhtml2pdf(ReportLab 기반)로 교체했습니다.

## 주요 변경
1. **PDF 생성 로직**
   - `expert/contract_flow.py`에서 WeasyPrint 의존성을 제거하고 `xhtml2pdf.pisa`를 사용하도록 리팩터링했습니다.
   - CSS를 인라인으로 주입(`inline_styles`)하고, ReportLab 폰트 등록 로직(`resolve_contract_pdf_font`)을 재활용해 한글 폰트를 그대로 사용합니다.
2. **템플릿/스타일 정리**
   - `expert/templates/expert/contract_pdf.html`에 인라인 스타일 블록을 추가하고, 푸터 문구를 일반화했습니다.
   - `expert/static/expert/css/contract_pdf.css`를 xhtml2pdf가 지원하는 단순한 스타일로 재작성했습니다.
3. **의존성 갱신 (임시)**
   - `pyproject.toml`, `requirements.txt`에서 `weasyprint`를 제거하고 `xhtml2pdf`를 추가하려 했으나, `pycairo` 의존성 문제로 곧바로 롤백했습니다.
4. **문서화**
   - README에 새 파이프라인과 설치 안내를 반영했습니다.

## 영향
- `pycairo` 빌드 시 Cairo 시스템 라이브러리가 필요해 Render 네이티브에서 여전히 설치 오류가 발생했습니다.
- 이 접근은 즉시 철회되었으며, 대신 ReportLab 플로우기반 렌더러로 재구현했습니다.
