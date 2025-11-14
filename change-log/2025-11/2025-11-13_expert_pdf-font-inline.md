# Expert PDF 한글 폰트 인라인 처리

## 배경
- Render 네이티브(Non-Docker) 배포 환경에서 OS에 설치된 한글 폰트 여부에 따라 WeasyPrint PDF 출력이 깨지는 문제가 반복됨.
- 기존에는 시스템 폰트 또는 파일 경로를 직접 참조했기 때문에, 빌드/런타임 위치가 달라지면 폰트 로딩이 실패했습니다.

## 주요 변경
1. `expert/contract_flow.py`
   - `@font-face` CSS를 base64 데이터 URI로 인라인해 PDF 생성 시점에 폰트를 그대로 포함.
   - CSS 문자열을 LRU 캐시에 보관해 매 호출마다 디스크를 읽지 않도록 최적화.
2. README 업데이트
   - 한글 폰트 처리 방식과 `scripts/render_sample_contract.py`로 네이티브 환경에서 즉시 검증하는 방법을 문서화.

## 기대 효과
- Render 네이티브/로컬/도커 환경 구분 없이 동일한 한글 렌더링 품질 보장.
- 신규 폰트를 추가해도 환경 변수(`EXPERT_FONT_DIR`) 혹은 기본 폴더만 맞추면 바로 적용되며, 테스트 스크립트로 즉시 결과 확인 가능.
