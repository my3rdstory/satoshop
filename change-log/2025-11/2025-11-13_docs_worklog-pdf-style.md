## 개요
- WeasyPrint 전용 CSS를 새롭게 정비해 카드형 본문, 헤더/푸터 대비, 다크 모드 팔레트, 3단계 불릿 마커 등 PDF 가독성을 전면 개선
- 샘플 수행 내역 Markdown에 3단계 목록 예시를 추가해 새 스타일을 바로 검증 가능하도록 보강
- README에 샘플 워크로그 PDF 생성 방법과 새 스타일 요약을 문서화

## 상세
1. `expert/static/expert/css/contract_pdf.css`를 색상 변수 기반으로 재작성하여 본문 카드, 헤딩 밑줄, 표 스트라이프, 코드/블록 인용, 다단계 불릿(•/◦/▪)과 다크 모드를 지원하고 페이지 하단에는 "SatoShop Worklog · 현재/전체" 포맷의 페이지 번호를 노출.
   - 하단 텍스트는 "SatoShop Expert Contract"로 조정해 계약 문맥과 일치시키고, 같은 파일의 `@page` 룰에서 관리하도록 함.
2. `expert/docs/sample_worklog.md`의 핵심 기능 요약 섹션에 2단계·3단계 불릿 예시를 추가해 들여쓰기·마커 차이를 PDF에서 바로 확인할 수 있도록 구성.
3. `README.md`에 새 CSS 특징과 `scripts/render_sample_contract.py`를 이용한 샘플 워크로그 PDF 생성 안내를 추가해 운영자가 재현 절차를 쉽게 따라 할 수 있도록 정리.
