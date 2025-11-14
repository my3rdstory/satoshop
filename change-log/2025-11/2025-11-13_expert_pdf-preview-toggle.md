# Expert PDF 검증 토글을 Expert 메뉴로 이동

## 배경
- 기존에는 SiteSettings > 기능 설정에서만 검증 도구를 켜거나 끌 수 있어 Expert 담당자가 메뉴를 오가기 번거로웠음.

## 변경 사항
1. SiteSettings 어드민에서 `enable_expert_pdf_preview_tool` 필드를 숨기고,
2. `어드민 → Expert → 계약서 PDF 검증` 페이지 상단에 활성/비활성 버튼을 추가해 즉시 토글 가능하도록 개선.
3. 토글 조작은 동일한 SiteSettings 필드를 업데이트하지만, 권한이 있는 사용자는 Expert 메뉴 안에서 바로 제어할 수 있음.
4. README의 안내 문구를 해당 메뉴 중심으로 갱신.

## 기대 효과
- Expert 계약 담당자가 다른 설정 메뉴로 이동하지 않아도 PDF 검증을 켜거나 끌 수 있어 검증 플로우가 단순해집니다.
