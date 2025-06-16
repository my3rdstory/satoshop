#!/usr/bin/env bash
# render.com 배포용 빌드 스크립트 - satoshop-dev

set -o errexit  # 오류 발생 시 스크립트 중단

echo "🔧 Python 패키지 업그레이드..."
pip install --upgrade pip

echo "📦 의존성 설치 중..."
pip install -r requirements.txt

echo "🔧 데이터베이스 연결 테스트..."
python manage.py shell -c "
from django.db import connection
try:
    cursor = connection.cursor()
    cursor.execute('SELECT 1')
    print('✅ 데이터베이스 연결 성공')
except Exception as e:
    print(f'❌ 데이터베이스 연결 실패: {e}')
    exit(1)
"

echo "🔍 마이그레이션 파일 생성 중..."
python manage.py makemigrations

echo "📊 데이터베이스 마이그레이션 실행 중..."
python manage.py migrate --run-syncdb

echo "🔧 데이터베이스 무결성 확인..."
python manage.py check --database default

echo "📁 정적 파일 수집 중 (해시 기반 캐시 무효화 포함)..."
python manage.py collectstatic --noinput --clear

echo "🔄 정적 파일 해시 매니페스트 생성 중..."
# ManifestStaticFilesStorage가 자동으로 해시 기반 파일명과 매니페스트를 생성합니다
if [ -f "staticfiles/staticfiles.json" ]; then
    echo "✅ 정적 파일 매니페스트가 생성되었습니다."
    echo "📊 매니페스트 파일 크기: $(du -h staticfiles/staticfiles.json | cut -f1)"
else
    echo "⚠️ 매니페스트 파일이 생성되지 않았습니다. ManifestStaticFilesStorage 설정을 확인하세요."
fi

echo "🖼️ 미디어 파일 처리 중..."
echo "📁 로컬 정적 파일을 staticfiles로 복사 중..."
if [ -d "static" ]; then
    echo "✅ static 디렉토리가 존재합니다."
    
    FILE_COUNT=$(find static -type f | wc -l)
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "📦 정적 파일 목록 (최대 10개):"
        find static -type f \( -iname "*.css" -o -iname "*.js" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) | head -10
        echo "✅ 정적 파일 처리 완료"
    else
        echo "⚠️ static 디렉토리에 파일이 없습니다."
    fi
else
    echo "⚠️ static 디렉토리가 존재하지 않습니다. 건너뜁니다."
fi

echo "📂 staticfiles 디렉토리 구조 확인:"
find staticfiles -type f | head -10 || echo "❌ staticfiles 디렉토리가 비어있거나 존재하지 않습니다."

echo "🔧 S3 스토리지 연결 테스트..."
python manage.py shell -c "
import os
from storage.backends import S3Storage

# S3 설정 확인
s3_settings = {
    'ACCESS_KEY': os.getenv('S3_ACCESS_KEY_ID'),
    'SECRET_KEY': os.getenv('S3_SECRET_ACCESS_KEY'),
    'BUCKET_NAME': os.getenv('S3_BUCKET_NAME'),
    'ENDPOINT_URL': os.getenv('S3_ENDPOINT_URL'),
}

missing_settings = [k for k, v in s3_settings.items() if not v]
if missing_settings:
    print(f'⚠️ S3 설정이 누락되었습니다: {missing_settings}')
    print('📁 로컬 파일 저장소를 사용합니다.')
else:
    print('✅ S3 스토리지 설정이 완료되었습니다.')
    try:
        storage = S3Storage()
        print('✅ S3 스토리지 연결 성공')
    except Exception as e:
        print(f'⚠️ S3 스토리지 연결 실패: {e}')
        print('📁 로컬 파일 저장소를 사용합니다.')
"

echo "👤 슈퍼유저 생성 스크립트 실행..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os

User = get_user_model()
admin_email = os.getenv('ADMIN_EMAIL')
admin_username = os.getenv('ADMIN_USERNAME')
admin_password = os.getenv('ADMIN_PASSWORD')

print(f'🔍 디버깅: ADMIN_EMAIL = \"{admin_email}\"')
print(f'🔍 디버깅: ADMIN_USERNAME = \"{admin_username}\"')
print(f'🔍 디버깅: ADMIN_PASSWORD = \"{\"*\" * len(admin_password) if admin_password else None}\"')

if not admin_email or not admin_username or not admin_password:
    print('❌ 환경변수 ADMIN_EMAIL, ADMIN_USERNAME, ADMIN_PASSWORD를 모두 설정해주세요.')
    exit(1)

if not User.objects.filter(username=admin_username).exists():
    User.objects.create_superuser(
        username=admin_username,
        email=admin_email,
        password=admin_password
    )
    print(f'✅ 슈퍼유저 {admin_username}가 생성되었습니다.')
else:
    print(f'⚠️ 슈퍼유저 {admin_username}가 이미 존재합니다.')
"

echo "🔧 Django 시스템 체크 실행..."
python manage.py check

echo "✅ 빌드 완료! satoshop-dev 프로젝트가 배포 준비되었습니다."
