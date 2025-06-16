# Render.com Cron Jobs 설정 가이드

SatoShop의 환율 자동 업데이트를 위한 Render.com Cron Jobs 설정 방법입니다.

## 🎯 개요

Django 앱 내부 스케줄러 대신 Render.com의 Cron Jobs 서비스를 사용하여 환율을 자동 업데이트합니다.

### 장점
- ✅ 웹 서비스와 독립적으로 실행
- ✅ 자동 재시작 및 오류 복구
- ✅ 리소스 효율성 (필요할 때만 실행)
- ✅ 멀티 인스턴스 환경에서 중복 실행 방지

## 🚀 설정 방법

### 1. Render.com 대시보드에서 Cron Job 생성

1. **Render.com 대시보드** 접속
2. **"New +"** 버튼 클릭
3. **"Cron Job"** 선택

### 2. 기본 설정

```yaml
Name: satoshop-exchange-rate-updater
Environment: Same as your web service
Repository: Your GitHub repository
Branch: main (or your main branch)
```

### 3. 명령어 설정

```bash
# 환율 업데이트 명령어
python manage.py update_exchange_rate --verbose
```

### 4. 스케줄 설정

#### 권장 스케줄 (5분마다)
```
*/5 * * * *
```

#### 다른 옵션들
```bash
# 1분마다 (너무 빈번할 수 있음)
* * * * *

# 10분마다 (권장)
*/10 * * * *

# 15분마다
*/15 * * * *

# 30분마다
*/30 * * * *

# 1시간마다
0 * * * *
```

### 5. 환경 변수 설정

Cron Job에 다음 환경 변수들을 설정하세요:

```env
# 데이터베이스 연결 (웹 서비스와 동일)
DATABASE_URL=your-database-url

# Django 설정
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Django 스케줄러 비활성화 (중요!)
ENABLE_DJANGO_SCHEDULER=false

# 기타 필요한 환경 변수들...
```

## 🔧 테스트 방법

### 1. 로컬에서 명령어 테스트

```bash
# 기본 실행
uv run python manage.py update_exchange_rate

# 상세 로그와 함께 실행
uv run python manage.py update_exchange_rate --verbose

# 강제 업데이트
uv run python manage.py update_exchange_rate --force --verbose
```

### 2. Render.com에서 수동 실행

1. Render.com 대시보드에서 생성한 Cron Job 선택
2. **"Trigger Run"** 버튼 클릭
3. 로그에서 실행 결과 확인

## 📊 모니터링

### 1. Render.com 대시보드

- **Logs**: 각 실행의 상세 로그 확인
- **Metrics**: 실행 시간, 성공/실패 통계
- **Alerts**: 실패 시 이메일 알림 설정 가능

### 2. Django 어드민

- **환율 데이터**: `/admin/myshop/exchangerate/`에서 최신 환율 확인
- **업데이트 간격**: 사이트 설정에서 간격 조정 가능

### 3. 로그 예시

#### 성공적인 실행
```
🚀 [2025-06-15 10:05:00] 환율 업데이트 시작 (Render.com Cron Job)
⚙️ 환율 업데이트 간격: 5분
📊 현재 환율: 1 BTC = 145,602,000 KRW
🌐 업비트 API에서 환율 데이터 가져오는 중...
✅ 환율 업데이트 성공!
   새로운 환율: 1 BTC = 145,615,000 KRW
   업데이트 시간: 2025-06-15 10:05:02
📈 환율 상승: +13,000 KRW (+0.01%)
💾 저장된 환율 데이터: 15개
🎉 [2025-06-15 10:05:02] 환율 업데이트 완료
   실행 시간: 1.23초
```

#### 스킵된 실행 (아직 시간이 안 됨)
```
🚀 [2025-06-15 10:03:00] 환율 업데이트 시작 (Render.com Cron Job)
⚙️ 환율 업데이트 간격: 5분
⏰ 아직 업데이트 시간이 되지 않았습니다.
   마지막 업데이트: 2025-06-15 10:00:15
   경과 시간: 0:02:45
   업데이트 간격: 5분
```

## 🛠️ 문제 해결

### 1. 환율이 업데이트되지 않는 경우

```bash
# 강제 업데이트로 테스트
python manage.py update_exchange_rate --force --verbose
```

### 2. API 호출 실패

- 업비트 API 상태 확인: https://upbit.com/
- 네트워크 연결 확인
- API 호출 제한 확인

### 3. 데이터베이스 연결 오류

- `DATABASE_URL` 환경 변수 확인
- PostgreSQL 서비스 상태 확인

### 4. 중복 실행 방지

Django 앱 내부 스케줄러가 비활성화되었는지 확인:
```env
ENABLE_DJANGO_SCHEDULER=false
```

## 📋 체크리스트

배포 전 확인사항:

- [ ] Render.com Cron Job 생성 완료
- [ ] 스케줄 설정 완료 (권장: `*/5 * * * *`)
- [ ] 환경 변수 설정 완료
- [ ] `ENABLE_DJANGO_SCHEDULER=false` 설정
- [ ] 로컬에서 명령어 테스트 완료
- [ ] Render.com에서 수동 실행 테스트 완료
- [ ] Django 어드민에서 환율 데이터 확인

## 🔄 마이그레이션 가이드

기존 Django 스케줄러에서 Render.com Cron Jobs로 전환:

1. **환경 변수 추가**:
   ```env
   ENABLE_DJANGO_SCHEDULER=false
   ```

2. **Render.com Cron Job 생성** (위 가이드 참조)

3. **웹 서비스 재배포**:
   - Django 스케줄러가 비활성화됨
   - 기존 스케줄러 작업이 중단됨

4. **Cron Job 활성화**:
   - 첫 실행 후 정상 동작 확인

5. **모니터링**:
   - 24시간 동안 정상 동작 확인
   - 환율 데이터 업데이트 확인

## 💡 팁

1. **스케줄 간격**: 5-10분이 적당합니다 (1분은 너무 빈번)
2. **알림 설정**: Render.com에서 실패 시 이메일 알림 설정
3. **로그 보관**: 중요한 로그는 별도로 저장 고려
4. **백업 계획**: API 실패 시 대체 환율 소스 고려

---

이 가이드를 따라 설정하면 안정적이고 효율적인 환율 자동 업데이트 시스템을 구축할 수 있습니다. 