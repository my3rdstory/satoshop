# Expert 계약 PDF WeasyPrint 전환

- Pandoc/XeLaTeX 파이프라인을 완전히 제거하고 WeasyPrint 기반 HTML→PDF 렌더링으로 교체했습니다. 더 이상 TinyTeX, Pandoc 바이너리를 준비할 필요가 없으며, 계약 Markdown을 그대로 HTML 템플릿(`expert/contract_pdf.html`)로 감싸 깔끔한 PDF를 생성합니다.
- WeasyPrint에서 사용할 전용 스타일(`expert/static/expert/css/contract_pdf.css`)과 Noto Sans KR 번들 폰트를 자동으로 로드해 한글 본문과 테이블이 일관된 타이포그래피로 출력됩니다. 이모지 역시 더 이상 제거하지 않아도 그대로 유지됩니다.
- README와 build 스크립트를 업데이트해 새로운 의존성(WeasyPrint)과 필요 패키지를 안내하고, 더 이상 사용하지 않는 Pandoc/TinyTeX 관련 설정·환경 변수를 제거했습니다.
