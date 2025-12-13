# api · 로컬 개발 환경 403(CSRF/Origin/IP) 완화

## 요약
- Vite 프런트(`http://localhost:5173`)에서 `POST /api/v1/...` 호출 시 Django `CsrfViewMiddleware`로 인해 403이 발생할 수 있어, 외부 API용 POST 뷰에 CSRF 면제를 적용했습니다.
- 운영에서 등록된 Origin/IP allowlist가 로컬 개발까지 차단하지 않도록, `DEBUG=True`일 때 `localhost/127.0.0.1` Origin과 loopback IP는 예외적으로 허용하도록 정책을 보완했습니다.

