## 개요
- Expert 계약서/채팅 PDF 생성기를 ReportLab에서 fpdf2로 전환해 줄바꿈 이슈를 근본적으로 해결하고, 의존성을 경량화했습니다.

## 상세
1. `expert/contract_flow.py`에 fpdf2 기반 렌더러를 추가해 Markdown 블록을 직접 파싱한 뒤 문단/표/코드/인용구를 모두 수동으로 그립니다. ReportLab Flowable, ParagraphStyle, Canvas 의존성은 완전히 제거했습니다.
2. 수행 내역·표 셀·작업 로그 등 다중 줄 필드는 `InlineHTMLParser`로 인라인 태그를 해석하고, fpdf2 `write`/`multi_cell` 조합으로 줄바꿈과 굵기/기울임을 유지합니다. 표 셀 높이는 `split_only=True`로 선 계산 후 padding해 행 높이를 안정화했습니다.
3. 채팅 로그 PDF(`expert/services.py`)도 fpdf2로 이관해 동일한 폰트 해상도와 페이지 번호 방식을 적용했습니다.
4. `pyproject.toml`에서 `reportlab`을 제거하고 `fpdf2`를 의존성으로 추가했으며, README의 PDF 파이프라인 설명을 fpdf2 기반으로 갱신했습니다.
