# Expert Pandoc 폰트 경로 고정

- Pandoc 명령어 생성 시 `expert/fonts/` 폰트 번들을 `mainfontoptions/sansfontoptions/...`에 `Path=...`와 `BoldFont=` 옵션으로 주입해 XeLaTeX이 시스템 전역 설치 없이도 Noto Sans KR을 찾을 수 있게 했습니다. Render 환경처럼 패키지 설치가 제한된 곳에서도 동일한 PDF가 생성됩니다.
- `EXPERT_FONT_DIR`이 비어 있으면 기존 동작을 유지하되, 경로가 존재할 경우 `OSFONTDIR` 뿐 아니라 Pandoc 변수에도 옵션을 넣어 폰트 검색 실패를 원천 차단했습니다.
- README의 Pandoc 안내 섹션에 “번들 폰트를 직접 참조한다”는 내용을 추가해 운영자가 폰트 설치 없이도 동작함을 명시했습니다.
- mainfont/sansfont 변수에 전달하는 값도 번들 폰트 파일명(예: `NotoSansKR-Regular.ttf`)으로 자동 치환해, XeLaTeX이 시스템 글꼴에 의존하지 않고도 계약 PDF를 렌더링하도록 보완했습니다.
