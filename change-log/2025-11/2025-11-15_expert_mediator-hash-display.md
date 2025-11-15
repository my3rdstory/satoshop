## 개요
- 최종 계약서 생성 시 사토샵(시스템) 해시를 DB에 저장하지만 UI에는 반영되지 않던 문제를 해결

## 상세
1. `expert/views.py`에서 계약 완료 시 `DirectContractDocument.mediator_hash`, `mediator_hash_meta`를 `update_fields`에 포함해 실제 DB에 저장되도록 수정.
2. 초대/공유 화면(`contract_invite.html`)이 이미 해당 필드를 표시하므로, 저장 누락 문제 해결 후 즉시 웹 화면에서도 사토샵 해시값이 노출된다.
