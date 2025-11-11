## 변경 개요
- Django Admin에서 `DirectContractStageLog` 메뉴명을 한글(`직접 계약 단계 로그`)로 노출하도록 `verbose_name`을 지정했습니다.
- 동일 관리자 화면의 기본 정보 섹션에 노출되는 `단계` 표시가 실제 최신 단계 상태를 반영하도록 보완했습니다.

## 상세 내용
- `expert.models.DirectContractStageLog.Meta`에 `verbose_name`/`verbose_name_plural`을 추가해 관리자 메뉴와 모델 헤더가 일관된 한글 표현을 사용합니다.
- `DirectContractStageLogAdmin.stage_display`가 해당 계약의 전체 로그를 조회해 가장 나중 단계(완료 기준)를 계산하도록 `_resolve_current_stage` 헬퍼를 추가했습니다.
- 데이터 스키마 변경은 없으며, 마이그레이션 없이 적용됩니다.
