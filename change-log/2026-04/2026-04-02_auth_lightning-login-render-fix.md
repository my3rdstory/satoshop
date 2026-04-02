# 2026-04-02 auth lightning-login-render-fix

## 요약
- Render 운영 환경에서 라이트닝 로그인 실패를 유발하던 LNURL DER 서명 미지원 문제를 수정했습니다.
- `lnurl_auth_callback` 내부 `cache` 스코프 충돌을 제거해 검증 실패 시 500 대신 정상 오류 응답과 오류 캐시 저장이 이뤄지도록 복구했습니다.
- Gunicorn 멀티워커 환경에서도 LNURL/Nostr 인증 상태가 공유되도록 운영 기본 캐시를 파일 기반으로 조정했습니다.

## 상세 변경
1. `myshop/crypto.py`
   - secp256k1 ECDSA digest 검증 시 64바이트 raw 서명과 ASN.1 DER 서명을 모두 허용하도록 보강했습니다.
2. `accounts/lnurl_service.py`
   - LNURL 서명 길이와 추정 형식을 로그에 남겨 운영 장애 분석 시 raw/DER 구분이 가능하도록 했습니다.
3. `accounts/views.py`
   - 함수 내부 중복 `cache` import를 제거해 `UnboundLocalError`가 발생하지 않도록 정리했습니다.
4. `satoshop/settings.py`
   - 클라우드 운영 환경에서 Django 기본 캐시를 파일 기반으로 바꿔 Gunicorn 워커 간 인증 상태 캐시를 공유하게 했습니다.
5. `README.md`
   - 운영 인증 캐시 동작과 멀티 인스턴스 확장 시 외부 공유 캐시가 필요하다는 점을 문서화했습니다.

## 운영 메모
- Render에 재배포되면 `/accounts/lightning-login/` 흐름에서 DER 서명을 보내는 지갑도 정상 검증됩니다.
- 현재 파일 캐시는 단일 인스턴스/단일 컨테이너의 멀티워커 문제를 해결합니다. 향후 다중 인스턴스 확장 시에는 Redis 같은 외부 공유 캐시를 붙여야 합니다.
- 수동 검증은 라이트닝 로그인 페이지에서 QR 스캔 후, 콜백 로그에 `sig_len`, `format`, `서명 검증 성공`, 상태 폴링의 `authenticated=True`가 순서대로 찍히는지 확인하면 됩니다.
