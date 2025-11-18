# 쿠폰 생성기

- `coupon` 앱을 신설하고 `/coupon` 라우트를 전역 URL에 연결해 라이트닝 인보이스 발행 API와 상태 조회 엔드포인트를 제공했습니다.
- 템플릿(`coupon/templates/coupon/coupon_generator.html`)과 전용 Tailwind 스타일/JS(`coupon/static/coupon/{css,js}/coupon_generator.*`)을 추가해 5·10·21·103·210 sats 프리셋, 기타 입력, 만료 타이머, 복사 버튼, Dark 모드 레트로 UI, 캔버스 기반 쿠폰 이미지 다운로드 기능을 구현했습니다.
- Blink 자격 정보 설정을 확장(`satoshop/settings.py`, `env*.example`)하여 `COUPON_BLINK_*` 환경 변수를 통해 쿠폰 페이지 전용 월렛을 선택할 수 있도록 문서/README를 업데이트했습니다.
