## 1. 헬퍼/스토리지 준비
- [ ] data URL을 ContentFile로 변환한 뒤 `upload_file_to_s3`를 호출해 서명 이미지를 저장하는 `store_signature_asset()` 유틸을 expert 앱에 추가한다.
- [ ] 업로드 실패 시 사용자에게 명확한 오류 메시지를 돌려주고, 로컬 개발(미설정)에서는 기존 MEDIA 저장을 fallback 옵션으로 둘지 여부를 결정한다.

## 2. 모델·마이그레이션
- [ ] `DirectContractDocument`에 `signature_assets`(JSON) 필드 및 헬퍼 프로퍼티를 추가하고, S3 경로/URL/업로드 시각을 저장한다.
- [ ] 새 필드를 포함하는 데이터 마이그레이션을 작성해 기존 `creator_signature` / `counterparty_signature` 파일이 존재하면 순차적으로 S3로 업로드하고 결과를 JSON에 반영한다.

## 3. 서명 플로우 업데이트
- [ ] `DirectContractReviewView.form_valid()`와 `DirectContractInviteView.form_valid()`에서 ImageField 저장 대신 서명 헬퍼를 호출해 JSON 필드를 갱신한다.
- [ ] 서명 업로드 성공 시 기존 ImageField를 비워서 중복 저장을 막고, 업로드 실패 시 롤백/오류 처리를 명확히 한다.

## 4. 서빙/표시 계층
- [ ] `contract_invite.html` 등 서명 이미지를 노출하는 템플릿을 `document.get_signature_url("creator")` 등의 새 헬퍼로 교체하고, URL이 만료되면 재생성하도록 뷰에 재검증 로직을 추가한다.
- [ ] 이메일/관리자 화면이 동일한 URL/프록시를 사용하도록 일관성 있게 정리한다.

## 5. 운영 가이드 & 검증
- [ ] README 또는 Expert 관련 문서에 S3 자격/버킷 요구사항과 presigned URL 만료 정책을 추가한다.
- [ ] 로컬·스테이징에서 Creator/Counterparty 플로우를 각각 실행해 서명이 S3에 저장되고 공유 페이지에서 노출되는지 확인하는 수동 테스트 절차를 남긴다.
