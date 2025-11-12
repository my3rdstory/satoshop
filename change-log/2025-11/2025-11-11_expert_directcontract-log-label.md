## 변경 개요
- Django Admin에서 `DirectContractStageLog` 메뉴명을 한글(`직접 계약 단계 로그`)로 노출하도록 `verbose_name`을 지정했습니다.
- 동일 관리자 화면의 기본 정보 섹션에 노출되는 `단계` 표시가 실제 최신 단계 상태를 반영하도록 보완했습니다.
- 계약 생성자/상대방의 로그인·결제 정보를 한눈에 볼 수 있도록 참여자 요약 박스를 추가했습니다.
- 중복 정보가 되던 메타 정보 섹션은 제거하고, 해시 비교 카드가 기본 정보 바로 아래에 오도록 재배치했습니다.

## 상세 내용
- `expert.models.DirectContractStageLog.Meta`에 `verbose_name`/`verbose_name_plural`을 추가해 관리자 메뉴와 모델 헤더가 일관된 한글 표현을 사용합니다.
- `DirectContractStageLogAdmin.stage_display`가 해당 계약의 전체 로그를 조회해 가장 나중 단계(완료 기준)를 계산하도록 `_resolve_current_stage` 헬퍼를 추가했습니다.
- `DirectContractStageLogAdmin`에 `participant_overview` 필드와 전용 렌더러를 더해 각 참여자의 계정/이메일/라이트닝 ID/서명 시각과 결제 영수증을 박스 형태로 노출합니다.
- 기존 `meta_details` 블록을 제거하고 `fieldsets` 순서를 `기본 정보 → 해시 비교 → 참여자 요약`으로 재구성했습니다.
- 데이터 스키마 변경은 없으며, 마이그레이션 없이 적용됩니다.
