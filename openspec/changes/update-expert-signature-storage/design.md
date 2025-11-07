## Overview
서명 이미지는 현재 Django `ImageField`가 `MEDIA_ROOT`에 직접 저장하고 있어 컨테이너 재시작 시 사라지고, 공개 경로 제어도 불가능하다. 기존 storage 앱에는 S3 업로드/URL/삭제 유틸이 이미 있으므로 Expert 앱에서 동일한 파이프라인을 재사용해 안전한 오브젝트 스토리지로 이관한다.

## Storage Strategy
1. **업로드 경로**: `expert/contracts/signatures/YYYY/MM/DD/<uuid>.png` 형태로 고정한다. data URL에서 MIME을 파싱해 확장자를 결정한다.
2. **도메인 객체**: `SignatureAsset` (dict) = `{ "path": str, "url": str, "size": int, "uploaded_at": datetime, "expires_at": datetime|None }` 구조를 JSONField에 저장한다.
3. **URL 관리**: `storage.backends.S3Storage`는 프라이빗 버킷을 가정한다. 기본 URL은 presigned URL(임시)로 발급하고, 만료 후에는 `get_signature_url()`이 새 presigned URL을 만들어 반환하도록 한다. 프록시 방식을 택할 경우 `/expert/contracts/signatures/<slug>/<role>/`와 같은 내부 뷰를 만들어 서명 파일을 스트리밍한다.
4. **Fallback**: `S3_*` 환경변수가 비어 있으면 기존 ImageField를 그대로 사용하도록 feature flag(`EXPERT_SIGNATURE_USE_MEDIA=false` 등)를 도입한다. QA 환경에서는 flag를 false로 두고, 운영에서는 true + S3 구성으로 강제한다.

## Model Changes
- `DirectContractDocument.signature_assets = models.JSONField(default=dict, blank=True)` 추가.
- `creator_signature` / `counterparty_signature` 필드는 일단 유지하되, 마이그레이션에서 기존 파일을 읽어 S3에 업로드한 뒤 JSON에 저장하고, 업로드 성공 시 파일 필드를 비운다.
- 헬퍼 메서드:
  ```python
  def store_signature(self, role, data_url, user_agent):
      asset = upload_signature_asset(data_url, prefix='contracts/signatures')
      self.signature_assets[role] = asset
      self.save(update_fields=['signature_assets', 'updated_at'])
  ```

## Request Flow Updates
- 검토 단계: `build_creator_hash` 이후 `store_signature('creator', data_url, ...)` 호출.
- 공유 링크: 상대방 서명 시 동일 헬퍼 사용 + mediator hash 생성.
- 각 뷰는 asset 저장 실패 시 사용자에게 에러를 보여주고, 성공해야 다음 단계로 진행한다.

## Template / API Updates
- 템플릿에서 `document.get_signature_asset('creator')` 헬퍼를 사용해 URL/업로드 시각 등을 보여준다. URL 없으면 “업로드 대기” 메시지 유지.
- PDF 생성 시 기존과 동일하게 data를 포함하지만, 필요하면 서명 URL에서 이미지를 다운로드해 PDF에 삽입할 수 있도록 후속 개선 여지를 남긴다.

## Migration Plan
1. 새 필드 추가 마이그레이션.
2. 데이터 마이그레이션: 각 `DirectContractDocument` 행에 대해 `creator_signature`/`counterparty_signature` 파일이 존재하면 `upload_file_to_s3`로 올리고 결과를 JSON에 기록, 성공 시 기존 파일 삭제.
3. 운영 배포 전 `uv run python manage.py migrate` → 샘플 계약으로 서명 플로우 테스트.
