# 🔧 환율 자동 업데이트 웹훅 설정 가이드

GitHub Actions에서 데이터베이스 연결 오류가 발생하는 문제를 해결하기 위해 **웹훅 방식**으로 변경되었습니다.

## ❌ 이전 문제 상황
```
GitHub Actions → Django 명령어 직접 실행 → PostgreSQL 연결 실패
ERROR: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: No such file or directory
```

## ✅ 현재 해결된 방식
```
GitHub Actions → 웹훅 HTTP 요청 → 실제 서버 → 환율 업데이트 성공
```

## 📋 빠른 설정 체크리스트

### 1️⃣ 웹훅 토큰 생성
```bash
uv run python scripts/generate_webhook_token.py
```

예시 출력:
```
📋 URL-safe 토큰 (권장):
   <value>
```

### 2️⃣ GitHub Secrets 설정

**GitHub 리포지토리** → **Settings** → **Secrets and variables** → **Actions**

추가할 시크릿:
```
WEBHOOK_URL=https://your-render-app.onrender.com/webhook/update-exchange-rate/
WEBHOOK_TOKEN=<value>
```

⚠️ **중요**: `WEBHOOK_URL` 끝에 반드시 `/`를 포함하세요!

### 3️⃣ 서버 환경변수 설정

**Render.com Dashboard** → **Your Service** → **Environment**

추가할 환경변수:
```
WEBHOOK_TOKEN=<value>
```

### 4️⃣ 웹훅 엔드포인트 테스트

```bash
# 로컬 테스트
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"token": "<value>", "source": "manual_test"}' \
  http://localhost:8000/webhook/update-exchange-rate/

# 실제 서버 테스트
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"token": "<value>", "source": "manual_test"}' \
  https://your-render-app.onrender.com/webhook/update-exchange-rate/
```

**성공 응답 예시:**
```json
{
  "success": true,
  "message": "환율 업데이트 성공",
  "btc_krw_rate": 145615000.0,
  "updated_at": "2025-06-16T12:15:56.378530+00:00",
  "source": "manual_test",
  "timestamp": "2025-06-16T12:15:56.378530+00:00",
  "processing_time": {
    "update_duration": "1.23s",
    "total_duration": "1.45s"
  }
}
```

### 5️⃣ GitHub Actions 수동 테스트

1. **GitHub** → **Actions** 탭
2. **환율 자동 업데이트 (웹훅 방식)** 워크플로우 선택
3. **Run workflow** 버튼 클릭

**성공 로그 예시:**
```
🚀 GitHub Actions에서 환율 업데이트 웹훅 호출 시작
⏰ 시작 시간: Mon Jun 16 12:26:30 UTC 2025
🔧 실행 모드: 웹훅 방식 (DB 직접 연결 안함)
📡 서버 URL: https://your-app.onrender.com/webhook/update-exchange-rate/
🔐 토큰 설정: ✅ (길이: 43자)
📞 웹훅 호출 중...
📊 HTTP 응답 코드: 200
📄 응답 내용: {"success":true,"message":"환율 업데이트 성공","processing_time":{"update_duration":"1.23s","total_duration":"1.45s"}}
✅ 환율 업데이트 웹훅 호출 성공!
🎉 환율이 정상적으로 업데이트되었습니다.
⏰ 완료 시간: Mon Jun 16 12:26:32 UTC 2025
```

## 🚀 개선된 시스템 특징

### 🔧 향상된 GitHub Actions
- ✅ **환경변수 체크**: WEBHOOK_URL과 WEBHOOK_TOKEN 존재 여부 확인
- ✅ **타임아웃 설정**: 5분 제한으로 무한 대기 방지
- ✅ **상세한 오류 처리**: HTTP 상태 코드별 맞춤 메시지
- ✅ **연결 안정성**: 10초 연결 타임아웃, 30초 최대 대기
- ✅ **실행 추적**: 시작/완료 시간 로깅

### 🛡️ 강화된 보안
- ✅ **토큰 인증**: 안전한 32자 이상 토큰
- ✅ **요청 추적**: IP 주소, User-Agent 로깅
- ✅ **상세한 오류 메시지**: 디버깅 정보 제공
- ✅ **성능 모니터링**: 처리 시간 측정

## 🔍 문제 해결

### ❌ 인증 실패 (401 오류)
**증상:**
```
❌ 인증 실패 (HTTP 401)
🔑 WEBHOOK_TOKEN이 서버와 일치하지 않습니다.
```

**해결방법:**
1. GitHub Secrets의 `WEBHOOK_TOKEN` 확인
2. 서버 환경변수의 `WEBHOOK_TOKEN` 확인
3. 두 값이 정확히 일치하는지 확인
4. 필요시 새 토큰 생성 후 양쪽에 업데이트

### ❌ 엔드포인트 없음 (404 오류)
**증상:**
```
❌ 엔드포인트를 찾을 수 없음 (HTTP 404)
🌐 WEBHOOK_URL이 올바른지 확인하세요.
```

**해결방법:**
1. `WEBHOOK_URL` 확인: `https://your-domain.com/webhook/update-exchange-rate/`
2. URL 끝에 `/` 포함 확인
3. 서버가 정상 작동하는지 확인

### ❌ 서버 오류 (500 오류)
**증상:**
```
❌ 서버 내부 오류 (HTTP 500)
🔧 서버에서 환율 업데이트 중 오류가 발생했습니다.
```

**해결방법:**
1. 서버 로그 확인 (Render.com Dashboard)
2. 업비트 API 상태 확인
3. 서버 환경변수 설정 확인

### ❌ 환경변수 미설정
**증상:**
```
❌ WEBHOOK_URL이 설정되지 않았습니다.
❌ WEBHOOK_TOKEN이 설정되지 않았습니다.
```

**해결방법:**
1. GitHub 리포지토리 → Settings → Secrets and variables → Actions
2. 필요한 시크릿 추가
3. 값이 올바르게 입력되었는지 확인

## 📊 모니터링

### GitHub Actions 로그
```
🚀 GitHub Actions에서 환율 업데이트 웹훅 호출 시작
⏰ 시작 시간: Mon Jun 16 12:26:30 UTC 2025
🔧 실행 모드: 웹훅 방식 (DB 직접 연결 안함)
📡 서버 URL: https://your-app.onrender.com/webhook/update-exchange-rate/
🔐 토큰 설정: ✅ (길이: 43자)
📞 웹훅 호출 중...
📊 HTTP 응답 코드: 200
📄 응답 내용: {"success":true,"message":"환율 업데이트 성공","processing_time":{"update_duration":"1.23s","total_duration":"1.45s"}}
✅ 환율 업데이트 웹훅 호출 성공!
🎉 환율이 정상적으로 업데이트되었습니다.
⏰ 완료 시간: Mon Jun 16 12:26:32 UTC 2025
```

### 서버 로그 (Render.com)
```
INFO: 웹훅 요청 수신 - IP: 140.82.112.XXX, User-Agent: curl/7.88.1
INFO: 웹훅 요청 상세 - 소스: github_actions, 타임스탬프: 2025-06-16T12:26:30.123Z
INFO: 웹훅 인증 성공 - 소스: github_actions, IP: 140.82.112.XXX
INFO: 환율 업데이트 시작
INFO: 환율 업데이트 성공: 1 BTC = 145,615,000 KRW (소요시간: 1.23초)
```

## ✅ 완전히 해결된 문제들

- ❌ `connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed`
- ❌ `No such file or directory`
- ❌ `Is the server running locally and accepting connections`
- ❌ `django.db.utils.OperationalError`

**이유**: GitHub Actions에서 더 이상 데이터베이스에 직접 연결하지 않고, 웹훅을 통해 실제 서버에 요청을 보내기 때문입니다.

## 🎯 다음 단계

1. **GitHub Secrets 설정** (WEBHOOK_URL, WEBHOOK_TOKEN)
2. **서버 환경변수 설정** (WEBHOOK_TOKEN)
3. **웹훅 테스트** (curl 명령어로 수동 테스트)
4. **GitHub Actions 테스트** ("Run workflow" 버튼)
5. **자동 스케줄 확인** (5분마다 정상 실행)

---

💡 **추가 도움이 필요하면 GITHUB_ACTIONS_EXCHANGE_RATE_AUTOMATION.md 파일을 참조하세요.** 