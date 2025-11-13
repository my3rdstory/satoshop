# Expert 계약서 Pandoc 입력 경로 안정화

- `_render_markdown_via_pandoc()`에서 임시 `contract.md` 파일을 생성하지 않고, Markdown 본문을 표준 입력으로 바로 전달하도록 수정했습니다. Render 환경에서 `/tmp/.../contract.md`가 간헐적으로 접근 불가해지며 PDF 생성이 실패하던 문제를 해결했습니다.
- 여전히 `contract.pdf`만 임시 디렉터리에 생성하므로 기존 서명/저장 플로우에 영향이 없고, 실패 시에는 stderr를 포함한 로그가 그대로 남습니다.
