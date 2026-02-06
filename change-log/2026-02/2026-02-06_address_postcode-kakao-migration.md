## 배경
- Daum 우편번호 서비스 공지(QnA #1498, 2026-02-05)에 따라 구 CDN(`t1.daumcdn.net`)은 2026-04-01부터 차단 예정.
- 기존 코드베이스는 `daum.Postcode` 및 Daum CDN URL을 사용하고 있어 공식 가이드 기준으로 전환이 필요했음.

## 변경 사항
- 주문/밋업/BAH 홍보요청 템플릿의 우편번호 스크립트 URL을 `https://t1.kakaocdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js`로 통일.
- 프론트 JS의 우편번호 인스턴스 생성 코드를 `daum.Postcode`에서 `window.kakao.Postcode`로 변경.
- 스크립트 미로딩 시 콘솔 경고/에러 후 모달을 닫도록 방어 로직 보강.
- README 외부 서비스 항목에 카카오 우편번호 연동 기준을 명시.

## 영향
- 주소 검색 모달이 공식 마이그레이션 가이드와 동일한 네임스페이스/엔드포인트로 동작.
- 2026-04-01 이후 구 CDN 차단 시점에도 주소 검색 기능 중단 위험을 줄임.

## 대장 수동 테스트 가이드
1. `/orders/shipping-info/` 진입 후 주소 검색 모달을 열어 주소 선택 시 우편번호/주소/상세주소 포커스 이동이 정상인지 확인.
2. `/meetup/add/` 및 밋업 수정 페이지에서 주소 검색 모달이 열리고 선택값이 `location_postal_code`, `location_address`에 채워지는지 확인.
3. `/stores/bah/promotion-request/`에서 주소 검색 버튼 클릭 시 모달 열림/주소 반영/저장 버튼 활성화 로직이 정상인지 확인.
4. 브라우저 다크모드에서 우편번호 모달 테마(배경/텍스트)가 깨지지 않는지 확인.
