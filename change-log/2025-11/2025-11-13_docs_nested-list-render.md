## 개요
- 수행 내역 Markdown에서 2단계 이상 목록을 입력해도 계약 PDF에 동일한 계층 구조로 렌더링되도록 ReportLab 변환 로직을 개선
- 샘플 수행 내역(`sample_worklog.md`)과 PDF 출력물을 최신 상태로 갱신해 검증 자료를 추가

## 상세
1. `expert/contract_flow.py`의 `_build_list_flowable`에 중첩 리스트 지원을 추가해, `<ul>/<ol>`이 `<li>` 내부에 들어가면 `ListFlowable`을 재귀로 구성하고 깊이에 따라 들여쓰기·bullet 모양(•/◦/▪/‣)을 다르게 적용하며, 하위 목록도 동일 카드 내에서 연속 렌더링되도록 개선
2. `sample_worklog.md`의 “1. 프로젝트 개요”와 “4.2 라이트닝 결제 위젯” 섹션에 2단계 불릿 예시를 넣어 렌더링 결과를 확인할 수 있도록 문서를 보강
3. `scripts/render_sample_contract.py`를 이용해 PDF를 재생성했으며, `expert/docs/expert-worklog-sample-20251113-092434-52d087.pdf`에 반영
