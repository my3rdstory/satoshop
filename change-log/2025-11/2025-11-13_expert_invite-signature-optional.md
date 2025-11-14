# Expert 초대 링크 서명 옵션 복구

- `CounterpartySignatureForm`의 초기화 로직을 하나로 통합해 `signature_optional`/`require_performer_lightning` 키워드를 직접 처리하도록 수정했습니다. Django `BaseForm`로 잘못 전달되던 인자가 제거돼 `/expert/contracts/direct/link/<slug>/` 진입 시 500 오류가 더는 발생하지 않습니다.
- 수행자 역할일 때만 `performer_lightning_address` 필드를 유지·필수화하고, 그 외에는 필드를 제거해 템플릿에 불필요한 입력이 노출되지 않도록 했습니다.
- 정확한 수동 테스트 절차를 README에 추가해 계약 초대 링크 렌더링 및 서명 재사용 시나리오를 언제든 재현하고 검증할 수 있게 했습니다.
- 기존 서명이 감지되면 초대 폼에서 서명 패드가 완전히 숨겨지고, 체크박스/결제 상태만으로 버튼이 활성화되도록 템플릿과 `contract_signature.js`를 업데이트했습니다. 필요 시 서명 필드를 초기화하면 다시 서명 패드가 노출됩니다.
