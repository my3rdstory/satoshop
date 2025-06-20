# 외부 서버 Crontab 환율 업데이트 설정 가이드

Render.com에서 crontab 설정이 어려울 때, 별도의 리눅스 서버에서 crontab을 사용하여 주기적으로 SatoShop 환율을 업데이트하는 방법입니다.

## 📋 개요

- **목적**: 외부 리눅스 서버에서 crontab으로 주기적 환율 업데이트
- **방식**: 웹훅 호출을 통한 환율 업데이트
- **주기**: 10분마다 (또는 원하는 간격)
- **대상**: 여러 SatoShop 서버 동시 업데이트 가능

## 🏗️ 아키텍처

```
외부 리눅스 서버 (crontab)
         ↓ (HTTP POST 웹훅)
    SatoShop 서버들
         ↓ (업비트 API 호출)
    환율 데이터 업데이트
```

## 📁 파일 구조

```
scripts/
├── exchange_rate_updater.py    # 메인 업데이트 스크립트
├── requirements.txt            # Python 패키지 요구사항
├── config.env.example          # 환경 변수 예시
├── install_cron_updater.sh     # 자동 설치 스크립트 (한방 설치)
├── show_webhook_token.sh       # 토큰 확인 스크립트
├── generate_new_token.sh       # 새 토큰 생성 스크립트
├── manage_webhook_token.sh     # 토큰 관리 통합 스크립트
└── generate_webhook_token.py   # 토큰 생성 스크립트 (수동용)
```

## ⚡ 빠른 시작 (3단계)

```bash
# 1. 파일 다운로드 후 설치
sudo ./install_cron_updater.sh

# 2. 생성된 토큰을 각 SatoShop 서버에 설정
satoshop-webhook show

# 3. Crontab 설정
sudo crontab -u satoshop -e
# 추가: */10 * * * * /opt/satoshop-exchange-updater/run_updater.sh >/dev/null 2>&1
```

> 🎉 **완료!** 이제 10분마다 자동으로 환율이 업데이트됩니다.

---

## 🚀 상세 설치 방법

### 1. 파일 준비

외부 리눅스 서버에 파일을 업로드합니다:

```bash
# 작업 디렉토리 생성
mkdir -p ~/satoshop-cron
cd ~/satoshop-cron

# 필요한 파일들을 서버에 업로드
# - exchange_rate_updater.py
# - install_cron_updater.sh
```

### 2. 자동 설치 실행

```bash
# 실행 권한 부여
chmod +x install_cron_updater.sh

# 자동 설치 (루트 권한 필요)
sudo ./install_cron_updater.sh
```

설치 스크립트가 다음 작업을 **한 번에** 모두 수행합니다:
- Python 및 uv 패키지 매니저 자동 설치
- Python 가상환경 생성 (uv 우선 사용)
- 필요한 패키지 설치 (uv로 빠른 설치)
- **웹훅 토큰 자동 생성** 🆕
- 모든 스크립트 파일 복사 및 **권한 자동 설정** 🆕
- 시스템 사용자 생성
- 로그 및 로그 로테이션 설정
- **전역 명령어 생성** (`satoshop-webhook`) 🆕

### 3. 서버 환경변수 설정 (중요!)

설치 스크립트가 자동으로 웹훅 토큰을 생성합니다. 생성된 토큰을 각 SatoShop 서버에 설정해야 합니다.

```bash
# 생성된 토큰 확인 (새로운 통합 명령어)
satoshop-webhook show

# 또는 기존 방식
./scripts/show_webhook_token.sh
```

**각 SatoShop 서버에 환경변수 추가:**
- **Render.com**: Dashboard → Service → Environment → Add Environment Variable
  - Key: `WEBHOOK_TOKEN`
  - Value: `생성된_토큰_값`

> 💡 토큰이 모든 서버에 동일하게 설정되어야 합니다!

### 4. 수동 테스트

```bash
# 스크립트 수동 실행 테스트
sudo -u satoshop /opt/satoshop-exchange-updater/run_updater.sh

# 로그 확인
tail -f /var/log/satoshop_exchange_updater.log
```

### 5. Crontab 설정

```bash
# satoshop 사용자의 crontab 편집
sudo crontab -u satoshop -e

# 다음 라인 추가 (10분마다 실행)
*/10 * * * * /opt/satoshop-exchange-updater/run_updater.sh >/dev/null 2>&1
```

## ⚙️ 환경 변수 설정

### 필수 설정

```env
# 웹훅 인증 토큰 (필수)
SATOSHOP_WEBHOOK_TOKEN=your_webhook_token_here
```

### 선택적 설정

```env
# 커스텀 웹훅 URL 목록 (기본값 사용 안 할 경우)
SATOSHOP_WEBHOOK_URLS=https://your-domain1.com/webhook/update-exchange-rate/,https://your-domain2.com/webhook/update-exchange-rate/
```

기본 URL 목록:
- `https://satoshop-dev.onrender.com/webhook/update-exchange-rate/`
- `https://satoshop.onrender.com/webhook/update-exchange-rate/`  
- `https://store.btcmap.kr/webhook/update-exchange-rate/`

## 📊 모니터링

### 로그 확인

```bash
# 실시간 로그 보기
tail -f /var/log/satoshop_exchange_updater.log

# 최근 로그 확인
tail -n 50 /var/log/satoshop_exchange_updater.log

# 오늘 로그만 보기
grep "$(date +%Y-%m-%d)" /var/log/satoshop_exchange_updater.log
```

### Crontab 상태 확인

```bash
# 현재 crontab 목록 확인
sudo crontab -u satoshop -l

# cron 서비스 상태 확인
sudo systemctl status cron
```

## 🔧 고급 설정

### 실행 주기 변경

```bash
# crontab 편집
sudo crontab -u satoshop -e
```

주기 예시:
```cron
# 5분마다
*/5 * * * * /opt/satoshop-exchange-updater/run_updater.sh >/dev/null 2>&1

# 15분마다  
*/15 * * * * /opt/satoshop-exchange-updater/run_updater.sh >/dev/null 2>&1

# 매시 정각
0 * * * * /opt/satoshop-exchange-updater/run_updater.sh >/dev/null 2>&1

# 평일 오전 9시부터 오후 6시까지 10분마다
*/10 9-18 * * 1-5 /opt/satoshop-exchange-updater/run_updater.sh >/dev/null 2>&1
```

### 타임아웃 설정

스크립트 내의 `self.timeout` 값을 변경:

```python
def __init__(self):
    # ...
    self.timeout = 60  # 60초로 변경
```

### 알림 설정

실패시 이메일 알림을 받으려면:

```bash
# crontab에서 MAILTO 설정
sudo crontab -u satoshop -e

# 맨 위에 추가
MAILTO=your-email@example.com
*/10 * * * * /opt/satoshop-exchange-updater/run_updater.sh
```

## 🐛 문제 해결

### 1. 권한 오류

```bash
# 권한 재설정
sudo chown -R satoshop:root /opt/satoshop-exchange-updater
sudo chmod -R 755 /opt/satoshop-exchange-updater
sudo chmod +x /opt/satoshop-exchange-updater/run_updater.sh
```

### 2. Python 패키지 오류

```bash
# uv 사용 가능시 (빠른 설치)
if command -v uv &> /dev/null; then
    cd /opt/satoshop-exchange-updater
    sudo -u satoshop uv pip install --python venv/bin/python --upgrade requests python-dotenv
else
    # pip 사용
    sudo -u satoshop /opt/satoshop-exchange-updater/venv/bin/pip install --upgrade requests python-dotenv
fi
```

### 3. 로그 파일 문제

```bash
# 로그 파일 재생성
sudo touch /var/log/satoshop_exchange_updater.log
sudo chown satoshop:adm /var/log/satoshop_exchange_updater.log
sudo chmod 640 /var/log/satoshop_exchange_updater.log
```

### 4. 토큰 관련 문제

```bash
# 현재 토큰 확인
/opt/satoshop-exchange-updater/scripts/show_webhook_token.sh

# 새 토큰 생성 (필요시)
sudo /opt/satoshop-exchange-updater/scripts/generate_new_token.sh
```

### 5. 연결 문제

웹훅 URL이 올바른지 확인:

```bash
# 현재 토큰으로 웹훅 테스트
WEBHOOK_TOKEN=$(grep "SATOSHOP_WEBHOOK_TOKEN=" /opt/satoshop-exchange-updater/config.env | cut -d'=' -f2)
curl -X POST https://your-domain.com/webhook/update-exchange-rate/ \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$WEBHOOK_TOKEN\",\"source\":\"manual_test\"}"
```

## 📈 성능 최적화

### 1. uv 패키지 매니저 활용

설치 스크립트가 자동으로 uv를 설치하여 패키지 관리 성능을 향상시킵니다:

- **빠른 설치**: pip 대비 10-100배 빠른 패키지 설치
- **안정성**: 더 나은 종속성 해결
- **캐싱**: 효율적인 패키지 캐싱

```bash
# uv 설치 확인
uv --version

# 수동으로 패키지 재설치 (필요시)
cd /opt/satoshop-exchange-updater
uv pip install --python venv/bin/python requests python-dotenv
```

### 2. 멀티 서버 병렬 처리

스크립트가 자동으로 여러 서버에 병렬로 요청을 보냅니다.

### 3. 로그 로테이션

자동으로 설정되며, 30일간 로그를 보관합니다:

```bash
# 로그 로테이션 상태 확인
sudo logrotate -d /etc/logrotate.d/satoshop-exchange-updater
```

### 4. 시스템 리소스 사용량

```bash
# 프로세스 모니터링
ps aux | grep satoshop

# 메모리 사용량 확인
sudo -u satoshop /opt/satoshop-exchange-updater/venv/bin/python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'CPU: {psutil.cpu_percent()}%')
"
```

## 🔒 보안 고려사항

1. **토큰 보안**: 웹훅 토큰을 안전하게 관리
2. **파일 권한**: 설정 파일 접근 권한 제한
3. **로그 권한**: 로그 파일 읽기 권한 제한
4. **네트워크**: HTTPS만 사용

## 🆘 지원

문제가 발생하면:

1. 로그 파인 확인
2. 수동 실행 테스트
3. 네트워크 연결 확인
4. 웹훅 토큰 확인

---

이 가이드로 외부 서버에서 안정적으로 SatoShop 환율을 업데이트할 수 있습니다. 