## 개요
- 계약 기본 payload JSON을 Blink 인보이스 연계 PoC 사양으로 교체하고 워크로그 마크다운을 최신 문안으로 포함

## 상세
1. `expert/pdf_preview.py`의 `DEFAULT_PAYLOAD`에 제공된 계약 정보 전체를 반영하고 `work_log_markdown` 본문을 그대로 내장해 미리보기/관리자 도구에서 동일한 JSON을 재사용하도록 정리.
