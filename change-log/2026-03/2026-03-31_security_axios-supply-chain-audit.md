# axios 공급망 이슈 점검

## 요약
- 저장소 루트 기준으로 Node 의존성 파일은 없고, 추적 중인 `package.json`/`package-lock.json`은 `analysis_tmp/btcpayserver-doc-master`에만 존재했다.
- 해당 `package.json`의 `devDependencies`에는 `axios`가 직접 선언되어 있지 않았고, `package-lock.json` 전역 검색에서도 `axios`, `plain-crypto-js`가 발견되지 않았다.
- 저장소 내부에 `node_modules`와 `axios` 설치 디렉터리도 없어, 현재 코드베이스 기준으로 `axios@1.14.1`, `axios@0.30.4`, `plain-crypto-js@4.2.1` 노출 흔적은 확인되지 않았다.

## 상세 변경
- `todo.md`
  - axios 공급망 이슈 점검 작업을 완료 항목으로 기록
- 진단 근거
  - `analysis_tmp/btcpayserver-doc-master/package.json`에서 직접 의존성 선언 확인
  - `analysis_tmp/btcpayserver-doc-master/package-lock.json` 전역 검색으로 `axios`, `plain-crypto-js` 부재 확인
  - 저장소 전역 검색으로 `sfrclak.com`, 악성 패키지명, 해당 axios 버전 문자열 부재 확인
  - 저장소 내부 `node_modules` 및 `axios` 디렉터리 부재 확인

## 운영 메모
- GitHub `axios/axios` 이슈 `#10604` 기준으로 `axios@1.14.1`, `axios@0.30.4`가 침해되었다는 보고가 있었고, 이후 npm에서 해당 버전과 관련 토큰이 제거된 정황을 확인했다.
- npm 레지스트리 조회 시 `time` 메타데이터에는 두 버전이 남아 있지만, 개별 버전 조회는 `E404`가 반환되어 현재는 직접 설치 대상에서 제거된 상태로 보인다.
- 이 점검은 현재 저장소 범위만 대상으로 했으므로, 대장이 오늘 다른 프로젝트나 전역 환경에서 `npm install axios@1.14.1` 또는 `npm install axios@0.30.4`를 실행했다면 그 작업 디렉터리의 락파일과 설치 로그를 별도로 확인해야 한다.
