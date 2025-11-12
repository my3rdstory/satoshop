# Expert 계약 PDF 한글 폰트 안정화

## 배경
- 계약서/채팅 PDF 생성 시 서버에 한글 폰트가 없으면 ReportLab 기본 Helvetica가 사용되어 한글이 깨짐.

## 변경 사항
- ReportLab `UnicodeCIDFont` 기반 `HYSMyeongJo-Medium`/`HYGoThic-Medium` 폰트를 후보로 등록하여 한글 폰트가 시스템에 없어도 자동으로 CJK CID 폰트를 사용.
- 동일 로직을 계약서 PDF와 채팅 로그 PDF에서 공통으로 사용하도록 `resolve_contract_pdf_font` 헬퍼를 노출.
- README에 PDF 한글 폰트 자동 등록 동작과 커스터마이징 방법을 문서화.

## 검증
- 한글 텍스트가 포함된 계약서/채팅 내용을 기준으로 PDF 생성 후 한글이 정상적으로 노출되는지 확인한다. (관리자: Expert → 계약서 → `PDF 생성` 액션 또는 채팅 PDF 생성 액션)
