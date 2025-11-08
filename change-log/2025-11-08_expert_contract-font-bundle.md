# Expert 계약 PDF 폰트 기본값 개선

## 배경
- 서버 환경마다 한글 TTF 설치 여부가 달라 ReportLab이 `DejaVu Sans` 같은 라틴 폰트를 선택해 한글이 깨지는 사례가 있었습니다.

## 변경 사항
- ReportLab 폰트 탐색 순서를 `expert/fonts/` 사용자 정의 → 시스템 Noto 계열 → 내장 CID(`HYSMyeongJo-Medium`, `HYGoThic-Medium`) → 라틴 폰트 순으로 재구성해, 시스템 폰트가 없어도 항상 CID 폰트가 선택되도록 수정.
- `expert/fonts/README.md`를 추가해 필요 시 프로젝트 안에 TTF/OTF를 투입하면 자동으로 사용된다는 사실을 안내.
- README의 한글 폰트 섹션을 업데이트하여 기본 CID 동작과 커스터마이징 방법을 문서화.

## 검증
- 계약서/채팅 PDF 생성 시 한글이 포함된 데이터를 넣고 PDF를 생성하면 이제 `HYSMyeongJo-Medium`(또는 `HYGoThic-Medium`)가 임베드되어 한글이 정상 표기되는지 확인한다.
