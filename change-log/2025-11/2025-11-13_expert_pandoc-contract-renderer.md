# Expert 최종 계약서 Pandoc 변환

- `expert/contract_flow.py`에서 ReportLab 기반 계약서 렌더링을 완전히 제거하고 Pandoc CLI로 Markdown → PDF 파이프라인을 재구성했습니다. 계약 개요/지급 내역/수행 내역/본문/서명 정보를 모두 Markdown 섹션으로 빌드해 Pandoc이 그대로 렌더링합니다.
- Pandoc 실행 파일 경로, PDF 엔진, 추가 옵션을 환경 변수(`EXPERT_PANDOC_PATH`, `EXPERT_PANDOC_PDF_ENGINE`, `EXPERT_PANDOC_EXTRA_ARGS`)로 제어할 수 있도록 `satoshop/settings.py`를 확장했습니다.
- 새 환경 변수 `EXPERT_PANDOC_GEOMETRY`로 여백(geometry) 값을 조정하고, `EXPERT_PANDOC_HEADER_INCLUDES` 기본값에 `\AtBeginEnvironment{longtable}{\raggedright}`를 적용해 표가 좌측 정렬되도록 했으며 필요 시 사용자 정의 LaTeX 스니펫을 주입할 수 있습니다.
- README의 Expert 섹션에 Pandoc 설치 및 설정 지침을 추가해 배포 환경에서 필요한 OS 패키지를 명확히 했습니다.
- Render 배포 스크립트(`build.sh`)가 `pandoc`, `texlive-xetex`, `fonts-noto-cjk`를 자동 설치해 서버 빌드 단계에서 바로 PDF를 생성할 수 있게 했습니다.
- 최종 계약서 파일명에 타임스탬프(`direct-contract-<slug>-YYYYMMDDHHMMSS.pdf`)를 붙여 CDN/브라우저 캐시가 남아있는 경우에도 항상 최신 파일을 내려받도록 했습니다.
