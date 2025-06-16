#!/usr/bin/env python
"""
S3 오브젝트 스토리지 연결 테스트 스크립트

사용법:
    python commons/storage/test_s3_connection.py
"""

import os
import sys
import django
from pathlib import Path

# Django 설정 로드
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'satoshop.settings')
django.setup()

from storage.backends import S3Storage
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def test_s3_connection():
    """S3 연결 테스트"""
    print("=" * 60)
    print("S3 오브젝트 스토리지 연결 테스트")
    print("=" * 60)
    
    # iwinv 호환을 위한 전역 환경변수 설정
    import os
    os.environ['AWS_S3_DISABLE_CHECKSUM'] = '1'
    os.environ['AWS_S3_DISABLE_MULTIPART_UPLOADS'] = '1'
    
    try:
        # S3Storage 인스턴스 생성
        print("\n1. S3Storage 인스턴스 생성 중...")
        storage = S3Storage()
        print("✅ S3Storage 인스턴스 생성 성공")
        
        # S3 클라이언트 연결 테스트
        print("\n2. S3 클라이언트 연결 테스트 중...")
        client = storage.client
        print("✅ S3 클라이언트 연결 성공")
        
        # 버킷 존재 확인
        print(f"\n3. 버킷 '{storage.bucket_name}' 존재 확인 중...")
        response = client.head_bucket(Bucket=storage.bucket_name)
        print("✅ 버킷 존재 확인 완료")
        
        # 버킷 내용 나열 (최대 5개)
        print(f"\n4. 버킷 '{storage.bucket_name}' 내용 확인 중...")
        try:
            response = client.list_objects_v2(Bucket=storage.bucket_name, MaxKeys=5)
            if 'Contents' in response:
                print(f"   버킷에 {len(response['Contents'])}개의 파일이 있습니다:")
                for obj in response['Contents']:
                    print(f"   - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print("   버킷이 비어있습니다.")
        except Exception as e:
            print(f"   ⚠️  버킷 내용 확인 중 오류: {e}")
        
        # 간단한 파일 업로드 테스트
        print("\n5. 간단한 파일 업로드 테스트 중...")
        test_content = b"S3 connection test file"
        test_key = "test/connection_test.txt"
        
        try:
            # 먼저 boto3로 시도
            import os
            import io
            
            # checksum 기능 비활성화
            os.environ['AWS_S3_DISABLE_CHECKSUM'] = '1'
            
            # BytesIO로 변환하여 업로드
            file_obj = io.BytesIO(test_content)
            
            try:
                client.put_object(
                    Bucket=storage.bucket_name,
                    Key=test_key,
                    Body=file_obj,
                    ContentType='text/plain',
                    ContentLength=len(test_content)  # 파일 크기 명시적 지정
                )
                print("✅ 테스트 파일 업로드 성공 (boto3)")
            except Exception as boto_error:
                if 'MissingContentLength' in str(boto_error):
                    print("   ⚠️  boto3 업로드 실패, 직접 HTTP 업로드로 재시도...")
                    
                    # 직접 HTTP 업로드 시도
                    from storage.fallback_upload import direct_s3_upload
                    
                    result = direct_s3_upload(
                        bucket_name=storage.bucket_name,
                        key=test_key,
                        content=test_content,
                        content_type='text/plain',
                        access_key=storage.access_key_id,
                        secret_key=storage.secret_access_key,
                        endpoint_url=storage.endpoint_url,
                        region=storage.region_name
                    )
                    
                    if result['success']:
                        print("✅ 테스트 파일 업로드 성공 (직접 HTTP)")
                    else:
                        raise Exception(f"직접 HTTP 업로드도 실패: {result.get('error', 'Unknown error')}")
                else:
                    raise boto_error
            
            # 업로드한 파일 확인
            response = client.head_object(Bucket=storage.bucket_name, Key=test_key)
            print(f"   업로드된 파일 크기: {response['ContentLength']} bytes")
            
            # 테스트 파일 삭제
            client.delete_object(Bucket=storage.bucket_name, Key=test_key)
            print("✅ 테스트 파일 삭제 완료")
            
        except Exception as e:
            print(f"   ❌ 파일 업로드 테스트 실패: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 S3 연결 테스트 완료! 모든 기능이 정상 작동합니다.")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ S3 연결 테스트 실패: {e}")
        print("\n🔧 문제 해결 방법:")
        print("1. .env 파일의 S3 설정값을 확인하세요")
        print("2. iwinv 오브젝트 스토리지 액세스 키가 유효한지 확인하세요")
        print("3. 버킷이 존재하고 접근 권한이 있는지 확인하세요")
        print("4. 네트워크 연결 상태를 확인하세요")
        return False


def show_current_settings():
    """현재 S3 설정값 표시"""
    from django.conf import settings
    
    print("\n📋 현재 S3 설정값:")
    print("-" * 40)
    
    s3_settings = {
        'S3_ACCESS_KEY_ID': getattr(settings, 'S3_ACCESS_KEY_ID', None),
        'S3_SECRET_ACCESS_KEY': getattr(settings, 'S3_SECRET_ACCESS_KEY', None),
        'S3_BUCKET_NAME': getattr(settings, 'S3_BUCKET_NAME', None),
        'S3_ENDPOINT_URL': getattr(settings, 'S3_ENDPOINT_URL', None),
        'S3_REGION_NAME': getattr(settings, 'S3_REGION_NAME', None),
        'S3_USE_SSL': getattr(settings, 'S3_USE_SSL', None),
    }
    
    for key, value in s3_settings.items():
        if key == 'S3_SECRET_ACCESS_KEY' and value:
            # 시크릿 키는 마스킹
            display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
        else:
            display_value = value
        
        status = "✅" if value else "❌"
        print(f"{status} {key}: {display_value}")


if __name__ == "__main__":
    show_current_settings()
    print()
    success = test_s3_connection()
    
    if not success:
        sys.exit(1) 