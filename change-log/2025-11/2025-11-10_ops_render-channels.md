# Render 배포 channels 의존성 누락 해결

## 배경
- Render는 `requirements.txt`만 설치 대상으로 삼는데, 최근 uv 의존성 정비 후 `channels` 항목이 다시 export되지 않아 `ModuleNotFoundError: No module named 'channels'`로 배포가 중단되었습니다.

## 변경 사항
- `uv export --format requirements-txt`로 requirements 파일을 재생성하여 `channels==4.3.1`을 포함하도록 복구했습니다.
- README 설치 안내에 uv export 재생성 절차와 누락 시 증상을 명시해 이후 의존성 추가 시 동일 문제가 재발하지 않도록 했습니다.

## 검증
- 새 `requirements.txt`에서 `channels==4.3.1` 항목을 확인하고 Render 배포가 해당 파일을 사용하도록 push 예정입니다.
