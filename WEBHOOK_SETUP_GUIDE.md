# 🔧 환율 자동 업데이트 웹훅 설정 가이드

GitHub Actions에서 데이터베이스 연결 오류가 발생하는 문제를 해결하기 위해 **웹훅 방식**으로 변경되었습니다.

## 📋 빠른 설정 체크리스트

### 1️⃣ 웹훅 토큰 생성
```bash
uv run python scripts/generate_webhook_token.py
```

예시 출력:
```
📋 URL-safe 토큰 (권장):
   RhTiiR28mELTm3c0OIdibgupkDoWg9XKzZtQ0-NdtMY
```

### 2️⃣ GitHub Secrets 설정

**GitHub 리포지토리** → **Settings** → **Secrets and variables** → **Actions**

추가할 시크릿:
```
WEBHOOK_URL=https://your-render-app.onrender.com/webhook/update-exchange-rate/
WEBHOOK_TOKEN=RhTiiR28mELTm3c0OIdibgupkDoWg9XKzZtQ0-NdtMY
```

### 3️⃣ 서버 환경변수 설정

**Render.com Dashboard** → **Your Service** → **Environment**

추가할 환경변수:
```
WEBHOOK_TOKEN=RhTiiR28mELTm3c0OIdibgupkDoWg9XKzZtQ0-NdtMY
```

### 4️⃣ 웹훅 엔드포인트 테스트

```bash
# 로컬 테스트
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"token": "RhTiiR28mELTm3c0OIdibgupkDoWg9XKzZtQ0-NdtMY", "source": "manual_test"}' \
  http://localhost:8000/webhook/update-exchange-rate/

# 실제 서버 테스트
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"token": "RhTiiR28mELTm3c0OIdibgupkDoWg9XKzZtQ0-NdtMY", "source": "manual_test"}' \
  https://your-render-app.onrender.com/webhook/update-exchange-rate/
```

**성공 응답 예시:**
```json
{
  "success": true,
  "message": "환율 업데이트 성공",
  "btc_krw_rate": 145615000.0,
  "updated_at": "2025-06-16T12:15:56.378530+00:00"
}
```

### 5️⃣ GitHub Actions 수동 테스트

1. **GitHub** → **Actions** 탭
2. **환율 자동 업데이트** 워크플로우 선택
3. **Run workflow** 버튼 클릭

## 🚀 변경된 시스템 구조

### 이전 (문제 발생)
```
GitHub Actions → Django 명령어 직접 실행 → PostgreSQL 연결 실패 ❌
```

### 현재 (해결됨)
```
GitHub Actions → 웹훅 HTTP 요청 → 실제 서버 → 환율 업데이트 ✅
```

## 🔍 문제 해결

### 인증 실패 (401 오류)
- GitHub Secrets의 `WEBHOOK_TOKEN`과 서버의 `WEBHOOK_TOKEN`이 일치하는지 확인
- 토큰을 새로 생성하여 양쪽에 동일하게 설정

### 서버 응답 없음 (타임아웃)
- `WEBHOOK_URL`이 올바른지 확인
- 서버가 정상 작동하는지 확인
- URL 끝에 `/`가 있는지 확인: `/webhook/update-exchange-rate/`

### 환율 업데이트 실패 (500 오류)
- 업비트 API 상태 확인
- 서버 로그 확인
- Django 어드민에서 환율 데이터 확인

## 📊 모니터링

### GitHub Actions 로그
```
🚀 GitHub Actions에서 환율 업데이트 웹훅 호출 시작
📡 서버 URL: https://your-app.onrender.com/webhook/update-exchange-rate/
📊 응답 코드: 200
📄 응답 내용: {"success":true,"message":"환율 업데이트 성공"}
✅ 환율 업데이트 웹훅 호출 성공
```

### 서버 로그 (Render.com)
```
INFO: 웹훅 인증 성공 - 소스: github_actions
INFO: 환율 업데이트 시작
INFO: 환율 업데이트 성공: 1 BTC = 145,615,000 KRW
```

## ✅ 이제 이 문제들이 해결됩니다

- ❌ `connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed`
- ❌ `No such file or directory`
- ❌ `Is the server running locally and accepting connections`

**이유**: GitHub Actions에서 더 이상 데이터베이스에 직접 연결하지 않고, 웹훅을 통해 실제 서버에 요청을 보내기 때문입니다.

---

💡 **추가 도움이 필요하면 GITHUB_ACTIONS_EXCHANGE_RATE_AUTOMATION.md 파일을 참조하세요.** 