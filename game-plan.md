# To the Selker! - 게임 설계 문서

## 기본 개발 구조
- 게임과 관련된 js를 만들 때에는 하나의 파일 속에 많이 넣지 말고, 단위 기능별로 js를 만들어 모듈화해야 한다.
- 분위기는 레트로 게임 분위기로 구성

## 기본 정보
- **게임 제목**: To the Selker!
- **게임 엔진**: Phaser.js 3.60.0
- **게임 장르**: 2D 탑뷰 서바이버 디펜스
- **플랫폼**: 웹브라우저 (PC/모바일 대응)
- **백엔드**: Django 5.2.4 + Python 3.13.4
- **패키지 관리**: uv
- **환경 변수**: python-decouple

## 게임 시스템

### 1. 웨이브 시스템
- **주기**: 15초마다 웨이브 증가
- **웨이브 표시**: 현재 웨이브와 다음 웨이브까지 남은 시간 표시
- **웨이브 종료 시**:
  - 보스 몬스터 1체 등장
  - 추가 일반 몬스터 (웨이브 × 2 + 무기레벨 보정)
  - 화면에 "WAVE X!" 및 "BOSS APPEARS!" 알림

### 2. 적 시스템

#### 일반 적 (빨간색)
- **체력**: 1
- **데미지**: 10 (충돌 시)
- **점수**: 10점
- **스폰**: 1초마다 (웨이브 수 + 무기레벨 보정)만큼 생성
- **크기**: 웨이브 10 이상에서 20% 감소 (30 → 24 픽셀)

#### 총 쏘는 적 (주황색, 웨이브 5+)
- **체력**: 3
- **데미지**: 충돌 8, 탄환 5
- **점수**: 30점
- **특징**: 2-3초마다 플레이어 방향으로 노란 탄환 발사
- **출현 확률**: 30%

#### 보스 (보라색)
- **체력**: 50 + (웨이브 × 30)
- **데미지**: 충돌 15, 방사탄 10, 추적탄 15
- **점수**: 500 × 웨이브
- **공격 패턴**:
  - 방사형 탄막: 4발에서 시작, 최대 8발
  - 추적 미사일: 플레이어를 따라가는 노란 탄환
- **특징**: 
  - 체력바 표시
  - 플레이어 받는 데미지 1.5배
  - 격파 시 아이템 3개 확정 드롭
  - 이동 속도: 20 (느림)

### 3. 무기 시스템
- **기본 무기**: 초록색 직사탄
- **발사 방식**: 
  - PC: 마우스 클릭
  - 자동 발사: 0.5초마다 가장 가까운 적에게
- **무기 레벨**: 
  - 레벨당 발사체 수 증가
  - 화면에 "Weapon Lv: X" 표시
- **밸런스**: 무기 레벨 3 이상부터 적 스폰 수도 증가

### 4. 아이템 시스템
- **드롭률**: 일반 적 5%, 보스 100%
- **아이템 종류**:
  - **무기 강화** (파란색): 무기 레벨 +1
  - **체력 회복** (초록색): HP +20
  - **폭탄** (노란색): 화면의 모든 적 제거 (보스 포함)
- **가중치 시스템**:
  - 초반(웨이브 1-3): 무기 드롭률 높음
  - 체력 50 미만: 회복 드롭률 높음
  - 후반(웨이브 5+): 폭탄 드롭률 높음
- **효과**: 획득 시 캐릭터 위에 메시지 표시

### 5. 플레이어 시스템
- **체력**: 100
- **이동 속도**: 200 (화면 크기에 따라 조정)
- **조작**:
  - PC: 방향키
  - 모바일: 가상 조이스틱 (오른쪽 하단)

### 6. UI 시스템
- **좌측 상단**: 
  - Wave: X
  - HP: X
  - Next wave: Xs
  - Weapon Lv: X
- **우측 상단**: Score (오른쪽 정렬)
- **게임 오버**: 
  - GAME OVER 애니메이션
  - 1.5초 후 랭킹 화면으로 자동 이동

### 7. 랭킹 시스템
- **저장 방식**:
  - FastAPI + SQLite3 서버 (온라인)
  - localStorage (오프라인 백업)
- **저장 데이터**:
  - 닉네임, 점수, 웨이브, 무기 레벨, 플레이 시간
- **랭킹 화면**:
  - TOP 10 표시
  - 순위, 이름, 점수, 웨이브 표시
  - 현재 플레이어 노란색 강조
  - 새 게임/메인 메뉴 선택

### 8. 설정 시스템
- **닉네임 변경**
- **사운드 ON/OFF**
- **게임 데이터 초기화**

### 9. 모바일 대응
- **가상 조이스틱**: 오른쪽 하단 (MOVE 표시)
- **반응형 디자인**: 
  - 화면 크기에 따른 자동 스케일링
  - 모바일에서 추가 20% 축소
  - 모든 게임 요소 크기 자동 조정

### 10. 사운드 시스템
- **BGM**: assets/audio/bgm.mp3
- **볼륨**: 50%
- **반복 재생**: 활성화

## 기술 구조

### Django 프로젝트 구조
```
minigame/                # Django 프로젝트
├── .venv/              # 가상환경
├── .env                # 환경 변수 (SECRET_KEY, DEBUG 등)
├── .gitignore          # Git 제외 파일
├── manage.py           # Django 관리 스크립트
├── README.md           # 프로젝트 문서
├── CLAUDE.md           # 개발 지침
├── game-plan.md        # 게임 설계 문서
├── minigame/           # 메인 프로젝트 설정
│   ├── settings.py     # Django 설정 (환경 변수 사용)
│   ├── urls.py         # 메인 URL 라우팅
│   ├── wsgi.py         # WSGI 설정
│   └── asgi.py         # ASGI 설정
├── main/               # 게임 목록 앱
│   ├── templates/
│   │   └── main/
│   │       └── index.html  # 게임 목록 페이지
│   ├── static/
│   │   └── main/
│   │       └── css/
│   │           └── style.css  # 메인 페이지 스타일
│   ├── views.py        # 게임 목록 뷰
│   └── urls.py         # main 앱 URL
└── selker/             # To the Selker! 게임 앱
    ├── templates/
    │   └── selker/
    │       └── game.html   # 게임 페이지 템플릿
    ├── static/
    │   └── selker/
    │       ├── css/
    │       │   └── game.css  # 게임 스타일
    │       ├── js/         # 게임 JavaScript 파일들
    │       ├── audio/      # 게임 사운드 파일
    │       └── html/       # HTML 폼 파일
    ├── views.py        # 게임 뷰
    └── urls.py         # selker 앱 URL
```

### URL 라우팅 구조
- `/` - 게임 목록 페이지 (main 앱)
- `/selker/` - To the Selker! 게임 페이지
- `/admin/` - Django 관리자 페이지

### 게임 파일 구조 (selker/static/selker/js/)
```
js/
├── main.js              # 메인 진입점
├── config.js            # 게임 설정
├── scenes/              # 씬 파일들
│   ├── BootScene.js     # 닉네임 입력
│   ├── MainMenuScene.js # 메인 메뉴
│   ├── SettingsScene.js # 설정
│   ├── GameScene.js     # 게임 플레이
│   └── RankingScene.js  # 랭킹 표시
├── entities/            # 엔티티 클래스
│   ├── Boss.js          # 보스 클래스
│   └── ShooterEnemy.js  # 총쏘는 적
├── utils/               # 유틸리티
│   ├── MobileControls.js # 모바일 컨트롤
│   └── ScaleManager.js  # 화면 크기 관리
└── services/            # 서비스
    └── api.js           # API 통신

backend/                 # FastAPI 서버 (별도 운영)
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI 앱
│   ├── database.py     # SQLite3 설정
│   └── schemas.py      # Pydantic 모델
├── run.py              # 서버 실행 스크립트
└── rankings.db         # SQLite3 데이터베이스
```

### Django 통합
- **정적 파일 서빙**: Django의 static 시스템 사용
- **템플릿 시스템**: Django 템플릿으로 게임 페이지 렌더링
- **URL 라우팅**: Django URL 패턴으로 게임 접근
- **환경 설정**: python-decouple을 통한 환경 변수 관리

### API 엔드포인트
- POST `/api/rankings` - 랭킹 저장
- GET `/api/rankings` - 랭킹 목록 조회
- GET `/api/rankings/top` - 상위 랭킹 조회
- GET `/api/stats` - 게임 통계

### 단축키
- **S**: 게임 시작 (메인 메뉴/랭킹 화면)
- **M**: 메인 메뉴로 이동 (랭킹 화면)
- **ESC**: 메인 메뉴로 이동 (랭킹 화면)

## 시스템 흐름
1. **웹사이트 접속**: 루트 URL(/) → 게임 목록 페이지
2. **게임 선택**: 게임 카드 클릭 → 새 탭에서 게임 열기
3. **게임 시작**: 닉네임 입력 → 메인 메뉴
4. **메인 메뉴**: Start Game / Rankings / Settings
5. **게임 플레이**: 웨이브 진행 → 보스 전투 → 아이템 수집
6. **게임 오버**: GAME OVER 애니메이션 → localStorage에 랭킹 저장 → 랭킹 화면
7. **랭킹 화면**: localStorage에서 TOP 10 표시 → 새 게임 or 메인 메뉴

## 시스템 환경
- **Python**: 3.13.4
- **Django**: 5.2.4
- **패키지 관리**: uv (빠른 Python 패키지 관리자)
- **환경 변수**: python-decouple (.env 파일 사용)
- **데이터베이스**: SQLite3 (개발 환경)
- **시간대**: Asia/Seoul
- **언어**: ko-kr

## Django 명령어
```bash
# 가상환경 활성화
source .venv/bin/activate

# 서버 실행
uv run python manage.py runserver

# 마이그레이션
uv run python manage.py migrate

# 슈퍼유저 생성
uv run python manage.py createsuperuser

# 새 앱 생성
uv run python manage.py startapp [앱이름]
```

## 밸런스 정책
1. 초반은 쉽게, 점진적으로 어려워지는 구조
2. 무기가 강해질수록 적도 많아짐
3. 아이템은 희귀하게, 전략적 사용 유도
4. 보스는 도전적이되 극복 가능한 수준
5. 첫 보스 난이도 하향 조정 (체력 80, 공격 주기 4초)