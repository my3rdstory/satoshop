# NostrUser 인덱스 리네임 마이그레이션 적용

## 요약
- `accounts.NostrUser.public_key` 인덱스 이름 불일치로 인해 자동 생성된 리네임 마이그레이션을 추가했다.
- 개발 DB에 해당 마이그레이션을 적용해 스키마 상태를 최신으로 맞췄다.

## 상세 변경
- `accounts/migrations/0014_rename_accounts_nos_public__3fe23f_idx_accounts_no_public__df3e9b_idx.py` 추가
  - 기존 인덱스명: `accounts_nos_public__3fe23f_idx`
  - 변경 인덱스명: `accounts_no_public__df3e9b_idx`

## 운영 메모
- `uv run python manage.py migrate` 실행 시 `accounts.0014`까지 정상 적용됨을 확인했다.
