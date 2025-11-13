# Expert 계약 PDF 이모지 제거

- Pandoc PDF 생성 시 번들 폰트에 없는 이모지(U+1F300~1FAFF 등)가 포함되면 XeLaTeX이 PDF를 만들지 못하던 문제를 해결하기 위해, 계약 Markdown을 렌더링하기 전에 이모지/Variation Selector를 제거하는 전처리기를 추가했습니다.
- `expert/contract_flow.py`의 `_sanitize_markdown`이 모든 계약 본문과 요약 섹션에 적용되어, 경고 없이 안정적으로 PDF가 생성됩니다. 필요한 경우에는 추후 폴백 폰트가 준비됐을 때 전처리를 조정하면 됩니다.
