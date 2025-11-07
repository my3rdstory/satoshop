## ADDED Requirements

### Requirement: Signature assets must be stored in object storage
Expert 직접 계약 플로우는 서명 이미지를 로컬 MEDIA 대신 S3 호환 오브젝트 스토리지에 업로드해 보존해야 한다 (MUST).

#### Scenario: Creator completes final review
- **GIVEN** 계약 생성자가 검토 화면(`expert/contract_review.html`)에서 data URL 서명을 제출하고 S3 자격이 정상 구성되어 있을 때
- **WHEN** `DirectContractReviewView.form_valid()`가 서명을 저장하면
- **THEN** 시스템은 `storage.utils.upload_file_to_s3`를 사용해 `expert/contracts/signatures/...` 경로에 파일을 업로드하고
- **AND** 업로드 결과(경로, URL, 크기, 업로드 시각)를 `DirectContractDocument.signature_assets['creator']`에 기록해야 한다.

#### Scenario: Counterparty signs via invite link
- **GIVEN** 초대 링크(`/expert/contracts/direct/link/<slug>/`)에서 상대방이 서명을 제출했을 때
- **WHEN** `DirectContractInviteView.form_valid()`가 실행되면
- **THEN** 상대방 서명 또한 동일한 S3 업로드 경로로 저장되고 `signature_assets['counterparty']`에 기록되어야 한다.

### Requirement: Signature assets must be served through controlled URLs
저장된 서명 이미지는 presigned URL 또는 내부 프록시를 통해 제한적으로 노출되어야 한다 (MUST).

#### Scenario: Contract invite page renders signatures
- **GIVEN** 계약이 완료되어 `signature_assets`에 creator/counterparty 항목이 존재할 때
- **WHEN** `/expert/contracts/direct/link/<slug>/` 페이지가 렌더링되면
- **THEN** 템플릿은 `document.get_signature_url('<role>')` 헬퍼를 통해 presigned URL(또는 프록시 엔드포인트)을 가져와 `<img>`에 설정하고
- **AND** URL이 만료되었거나 자격이 비활성화된 경우 “업로드된 서명이 없습니다”라는 대체 문구를 표시해야 한다.

#### Scenario: Email delivery includes signature access result
- **GIVEN** 계약이 완료되어 이메일 발송 로직이 실행될 때
- **WHEN** `send_direct_contract_document_email()` 또는 후속 알림이 서명 정보를 노출하면
- **THEN** 시스템은 `signature_assets`에 저장된 URL을 그대로 이메일에 내장하지 않고, presigned URL 또는 프록시 링크만 사용하며, 링크 생성 실패 시 알림 메시지에 이유를 포함해야 한다.

### Requirement: Migration preserves existing signatures
과거 계약에 저장된 로컬 서명 파일은 배포 시 S3로 이관되어야 한다 (MUST).

#### Scenario: Data migration runs on existing documents
- **GIVEN** 배포 전에 로컬 MEDIA에 `creator_signature` 또는 `counterparty_signature` 파일이 남아 있을 때
- **WHEN** 새 데이터 마이그레이션이 실행되면
- **THEN** 각 파일을 S3에 업로드하고 `signature_assets`에 경로를 기록하며
- **AND** 업로드가 성공한 파일은 로컬에서 삭제하거나 더 이상 참조하지 않아야 한다.
