# Expert PDF 검증 어드민 도구

## 배경
- Render 네이티브 환경에서 계약서를 빠르게 검증하려면 실제 계약을 새로 생성해야 해 번거로웠음.
- 어드민 내에서 샘플 Payload/본문을 조합해 즉시 PDF를 내려받을 수 있는 전용 도구가 필요했음.

## 주요 변경
1. **기능 토글 추가**
   - `SiteSettings`에 `enable_expert_pdf_preview_tool` 필드를 추가하고 마이그레이션(`0029`)을 생성.
   - 사이트 설정 → 기능 설정 섹션에서 토글을 제어하도록 어드민 UI를 확장.
2. **어드민 전용 PDF 검증 페이지**
   - `ExpertPdfPreviewProxy` 프록시 모델과 `ExpertPdfPreviewAdmin`을 추가해 `어드민 → Expert → 계약서 PDF 검증` 메뉴 신설.
   - 폼(템플릿 선택, Markdown 본문, Payload JSON, 다운로드 파일명)과 즉시 PDF 생성 응답을 제공.
   - 기본 Payload/본문은 `expert/pdf_preview.py` 유틸리티를 통해 샘플 데이터를 재사용하고, WeasyPrint 인라인 폰트 수정 사항과 호환.
3. **문서화**
   - README의 관리자 기능 섹션에 새 도구 사용법과 토글 위치를 명시.

## 사용 방법
1. `관리자 → 사이트 설정 → 기능 설정`에서 **Expert PDF 검증 도구**를 활성화합니다.
2. `어드민 → Expert → 계약서 PDF 검증` 메뉴로 이동해 Payload/본문을 수정한 뒤 “PDF 다운로드” 버튼을 누릅니다.
3. Render 네이티브나 로컬 환경에서 동일한 데이터를 재현하려면 `uv run python scripts/render_sample_contract.py`로 CLI 테스트를 진행할 수 있습니다.
