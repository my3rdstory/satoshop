## Why
- Expert 직접 계약 플로우는 현재 서명 이미지를 `DirectContractDocument.creator_signature` / `counterparty_signature` ImageField에 저장하고 있습니다 (`expert/models.py:198-205`).
- 두 뷰(`expert/views.py:180-206`, `expert/views.py:252-285`)가 data URL을 `ContentFile`로 변환해 로컬 MEDIA 스토리지에 그대로 작성하면서 S3 업로드가 전혀 이뤄지지 않습니다.
- 배포 환경은 Redeploy 때마다 컨테이너 파일시스템이 초기화되므로 서명이 유실되고, todo.md에 남겨둔 “서명 이미지 오브젝트 스토리지 업로드” 요구사항이 계속 미뤄지고 있습니다.
- 서명 이미지는 개인정보에 해당해 외부 노출/만료 정책을 강제할 수 있는 프록시·presigned URL 기반 서빙으로 전환해야 합니다.

## What Changes
- data URL 서명을 `storage.utils.upload_file_to_s3`로 전송하는 헬퍼를 추가하고, 업로드 결과(경로, URL, 만료, 파일 크기)를 캡슐화합니다.
- `DirectContractDocument`에 `signature_assets`(JSON) 필드를 추가하고, 새로운 헬퍼 결과를 저장하도록 모델/서비스/템플릿을 업데이트합니다.
- 공유 페이지/이메일은 `ImageField.url` 대신 새로운 presigned URL(또는 내부 프록시 엔드포인트)을 사용해 서명을 노출하고, URL 만료시 다시 갱신하도록 합니다.
- 기존 로컬 파일은 마이그레이션 단계에서 순차적으로 S3로 업로드해 데이터 손실을 막습니다.

## Impact
- Expert 전자 계약 흐름에만 영향이 있으며, products/orders 등 다른 앱은 변경하지 않습니다.
- 마이그레이션이 포함되므로 배포 전 `uv run python manage.py migrate`가 필요합니다.
- S3 자격 미설정 환경에서는 업로드 실패 이유를 명확히 노출하고, QA는 로컬 스토리지를 계속 쓸 수 있도록 토글을 제공합니다.
