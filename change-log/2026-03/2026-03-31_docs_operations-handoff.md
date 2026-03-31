# 운영 인수인계 문서 추가

## 요약
- 시스템 운영을 인수인계받는 담당자가 먼저 봐야 할 항목을 정리한 루트 문서를 추가했다.
- 코드 구조, 외부 연동, Render 운영 방식, 일상 운영 체크리스트, 장애 대응 포인트를 한 문서에 묶었다.
- 현재 코드 기준 운영 리스크와 레거시 배포 파일의 위치도 함께 기록했다.

## 상세 변경
- `운영인수인계.md`
  - 운영 우선순위, 필수 환경 변수, 앱별 책임, 외부 서비스 연동 구조 정리
  - Render 배포 구조와 실제 기동 진입점(`Dockerfile`, `scripts/docker-entrypoint.sh`, `render.yaml`) 정리
  - 환율 웹훅/외부 크론, Blink webhook, Discord 명령 동기화, Minihome 도메인 매핑 운영 메모 추가
  - 일일/주간 운영 체크리스트와 장애 대응 흐름 추가
- `todo.md`
  - 이번 인수인계 문서 작업 항목을 완료 처리로 기록

## 운영 메모
- 현재 Render 배포는 Docker 기반이며 `build.sh`가 아니라 `Dockerfile`과 `scripts/docker-entrypoint.sh`가 실제 런타임 기준이다.
- `ln_payment`는 `BLINK_WEBHOOK_SECRET`을 사용할 수 있지만 `render.yaml`에는 기본 선언이 없어 운영 환경 변수 누락 여부를 별도로 점검해야 한다.
