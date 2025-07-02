#!/bin/bash

# 밋업 예약 정리 스크립트
# 이 스크립트는 만료된 임시 예약을 자동으로 정리합니다.
# 크론탭에 등록하여 정기적으로 실행하세요.

# 프로젝트 디렉토리로 이동
cd "$(dirname "$0")/.." || exit 1

# 로그 파일 설정
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/meetup_cleanup.log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "밋업 예약 정리 작업 시작"
log "=========================================="

# UV 명령 사용 여부 확인
if command -v uv >/dev/null 2>&1; then
    PYTHON_CMD="uv run python"
    log "UV 환경에서 실행"
else
    PYTHON_CMD="python"
    log "기본 Python 환경에서 실행"
fi

# 만료된 예약 정리 실행
log "만료된 예약 정리 실행 중..."
$PYTHON_CMD manage.py cleanup_expired_reservations 2>&1 | while IFS= read -r line; do
    # 색상 코드 제거
    clean_line=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g')
    log "$clean_line"
done

# 현재 통계 확인
log "현재 밋업 통계 확인..."
$PYTHON_CMD manage.py meetup_stats 2>&1 | while IFS= read -r line; do
    # 색상 코드 제거
    clean_line=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g')
    log "$clean_line"
done

log "=========================================="
log "밋업 예약 정리 작업 완료"
log "=========================================="

# 로그 파일 크기 관리 (10MB 이상이면 백업)
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 10485760 ]; then
    mv "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d_%H%M%S).bak"
    log "로그 파일이 백업되었습니다."
fi 