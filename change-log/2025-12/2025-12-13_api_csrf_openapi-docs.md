# api · CSRF 쿠키 발급 엔드포인트 문서/스웨거 노출

## 요약
- 브라우저 기반 로컬 연동 테스트에서 필요한 `GET /api/v1/csrf/` 엔드포인트가 Swagger UI에 보이지 않던 문제를 해결했습니다.
- `api/static/api/openapi-v1.json`에 `/csrf/` 경로를 추가해 `/api/v1/docs/`에서 바로 확인할 수 있게 했습니다.
- `README.md` 외부 API 섹션에 CSRF 로컬 테스트 절차(`CSRF_TRUSTED_ORIGINS` + `X-CSRFToken` + credentials) 안내를 추가했습니다.

