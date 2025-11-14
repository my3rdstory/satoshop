## 개요
- Expert 현황/관리자 통계의 라이트닝 인증 지표를 전체 사용자 수가 아니라 Expert 계약 생태계를 이용한 계정만 집계하도록 조정
- 30일 활동 수 역시 동일 기준으로 계산해 카드·관리자 화면 모두에서 일관되게 노출

## 상세
1. `expert/stats.py`에서 계약 생성자/상대방 사용자 ID를 모아 Expert용 라이트닝 계정 수(`expert_lightning_users_total/active`)를 계산하고, 전체 라이트닝 계정 수는 참고용으로만 유지
2. `expert/templates/expert/direct_contract_start.html` 4번째 카드 라벨을 “라이트닝 인증 합계”로 통일하고, 최근 30일 인증 인원을 간결하게 노출
3. `expert/templates/admin/expert/usage_stats.html`에서도 동일 용어/문구를 사용하며, 전체 라이트닝 프로필 수는 보조 문구로 안내
4. `README.md`와 `todo.md`에 관련 변경 사항을 기록하여 운영 문서와 작업 현황을 업데이트
