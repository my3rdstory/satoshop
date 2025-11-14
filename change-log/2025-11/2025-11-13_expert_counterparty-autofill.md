## 개요
- 공유 링크에서 상대방이 입력한 이메일·라이트닝 주소가 오류 발생 후 페이지를 새로 열어도 그대로 유지되도록 자동 채움 기능을 추가

## 상세
1. `expert/views.py`의 `DirectContractInviteView`에 `get_initial()`을 구현해, 계약 문서에 저장된 `counterparty_email`과 `payload.performer_lightning_address`(또는 `counterparty_lightning_id`) 값을 폼 기본값으로 주입.
2. 상대방이 이미 정보를 저장한 뒤 PDF 생성 단계에서 실패해도 다음 번에는 체크박스만 다시 확인하면 완료할 수 있어 UX가 개선됨.
