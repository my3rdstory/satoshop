# Render Docker 배포 파이프라인 정비

## 배경
- Expert PDF 한글 깨짐과 weasyprint 의존성 오류가 Render 기본 빌드 이미지와 호환되지 않아 배포마다 문제가 재현됨.
- GitHub 푸시 → Render 자동 배포가 requirements/pip 스크립트에 의존해 재현성이 낮았음.

## 주요 변경
1. **컨테이너 환경 통합**
   - `Dockerfile`에서 uv 기반 Python 3.13 이미지를 사용하고 Cairo/Pango/폰트 의존성을 apt 레벨에서 고정 설치.
   - `scripts/docker-entrypoint.sh`가 인증서 복원, 마이그레이션, 정적 자산 수집을 자동화.
   - `.dockerignore`로 불필요한 로컬 산출물(.venv, staticfiles 등)을 이미지에 포함하지 않음.
2. **Render Blueprint 추가**
   - `render.yaml`로 Docker 웹 서비스와 관리형 Postgres를 동시에 생성하고 `main` 브랜치 자동 배포를 켬.
   - `DB_*` 변수는 데이터베이스에서 자동 주입, 비밀환경변수는 `sync:false`로 명시.
3. **문서화**
   - README에 Docker 빌드/실행 예제와 Render Blueprint 적용 절차, RUN_* 토글 설명을 정리.

## 기대 효과
- Docker 이미지가 모든 의존성을 포함하므로 Render 빌드 시 한글 PDF/폰트 문제가 사라짐.
- main 브랜치 푸시만으로 Render 배포가 자동 실행되고, 동일 이미지를 다른 환경에도 재사용 가능.
- 신규 기여자가 README 안내만으로 로컬에서 Docker로 앱을 구동하고 Render 설정을 재현할 수 있음.
