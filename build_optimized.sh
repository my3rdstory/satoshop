#!/usr/bin/env bash
# render.com 배포용 최적화된 빌드 스크립트

set -o errexit

if [ -f "scripts/render_setup_signer.sh" ]; then
    # shellcheck source=/dev/null
    . scripts/render_setup_signer.sh
fi

echo "📦 의존성 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📊 데이터베이스 마이그레이션 실행 중..."
python manage.py migrate --noinput

echo "📁 정적 파일 수집 중..."
python manage.py collectstatic --noinput --clear

echo "👤 슈퍼유저 확인..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os

User = get_user_model()
admin_username = os.getenv('ADMIN_USERNAME')
admin_email = os.getenv('ADMIN_EMAIL')
admin_password = os.getenv('ADMIN_PASSWORD')

if admin_username and admin_email and admin_password:
    if not User.objects.filter(username=admin_username).exists():
        User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password
        )
        print(f'✅ 슈퍼유저 {admin_username} 생성')
    else:
        print(f'✅ 슈퍼유저 {admin_username} 확인')
"

echo "✅ 빌드 완료!"
