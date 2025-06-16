"""
S3 호환 오브젝트 스토리지를 위한 Django Storage Backend
iwinv 오브젝트 스토리지 Swift API 호환
"""

import os
import mimetypes
import logging
from datetime import datetime
from urllib.parse import urljoin
import uuid

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import now
from .fallback_upload import direct_upload_with_fallback

# 로거 설정
logger = logging.getLogger(__name__)


@deconstructible
class S3Storage(Storage):
    """
    S3 호환 오브젝트 스토리지를 위한 커스텀 스토리지 백엔드
    iwinv 오브젝트 스토리지 Swift API와 호환
    """
    
    def __init__(self, **kwargs):
        logger.info("S3Storage 초기화 시작")
        
        self.access_key_id = getattr(settings, 'S3_ACCESS_KEY_ID', None)
        self.secret_access_key = getattr(settings, 'S3_SECRET_ACCESS_KEY', None)
        self.bucket_name = getattr(settings, 'S3_BUCKET_NAME', None)
        self.endpoint_url = getattr(settings, 'S3_ENDPOINT_URL', None)
        self.region_name = getattr(settings, 'S3_REGION_NAME', 'kr-standard')
        self.custom_domain = getattr(settings, 'S3_CUSTOM_DOMAIN', None)
        self.use_ssl = getattr(settings, 'S3_USE_SSL', True)
        self.file_overwrite = getattr(settings, 'S3_FILE_OVERWRITE', False)
        self.max_file_size = getattr(settings, 'S3_MAX_FILE_SIZE', 10 * 1024 * 1024)
        self.allowed_extensions = getattr(settings, 'S3_ALLOWED_FILE_EXTENSIONS', [])
        
        logger.debug(f"S3 설정값: bucket={self.bucket_name}, endpoint={self.endpoint_url}, "
                    f"region={self.region_name}, ssl={self.use_ssl}")
        
        # 필수 설정값 검증
        if not all([self.access_key_id, self.secret_access_key, self.bucket_name, self.endpoint_url]):
            missing_settings = []
            if not self.access_key_id: missing_settings.append('S3_ACCESS_KEY_ID')
            if not self.secret_access_key: missing_settings.append('S3_SECRET_ACCESS_KEY')
            if not self.bucket_name: missing_settings.append('S3_BUCKET_NAME')
            if not self.endpoint_url: missing_settings.append('S3_ENDPOINT_URL')
            
            error_msg = f"S3 스토리지를 사용하려면 다음 설정이 필요합니다: {', '.join(missing_settings)}"
            logger.error(error_msg)
            raise ImproperlyConfigured(error_msg)
        
        # S3 클라이언트 초기화
        self._client = None
        self._connection = None
        logger.info("S3Storage 초기화 완료")
    
    @property
    def client(self):
        """S3 클라이언트 지연 초기화"""
        if self._client is None:
            logger.debug(f"S3 클라이언트 생성 중... endpoint={self.endpoint_url}")
            try:
                # iwinv 오브젝트 스토리지 최적화 설정
                from botocore.client import Config
                
                config = Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path',  # path-style addressing 사용
                        'payload_signing_enabled': True,  # Swift API 호환을 위해 payload signing 활성화
                    },
                    region_name=self.region_name,
                    retries={'max_attempts': 3},
                    tcp_keepalive=True,  # 연결 유지
                    max_pool_connections=10  # 연결 풀 최적화
                )
                
                self._client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region_name,
                    use_ssl=self.use_ssl,
                    config=config
                )
                
                logger.info("S3 클라이언트 생성 성공")
            except Exception as e:
                logger.error(f"S3 클라이언트 생성 실패: {e}")
                raise
        return self._client
    
    def _save(self, name, content):
        """파일을 S3에 저장 (iwinv Swift API 호환)"""
        logger.info(f"파일 저장 시작: {name}")
        
        # 파일 내용 읽기
        if hasattr(content, 'temporary_file_path'):
            # 임시 파일 경로에서 읽기
            with open(content.temporary_file_path(), 'rb') as f:
                content_data = f.read()
        else:
            # 메모리에서 읽기
            content.seek(0)
            content_data = content.read()
        
        file_size = len(content_data)
        logger.info(f"파일 크기: {file_size} bytes")
        
        # 파일 크기 검증
        if file_size > self.max_file_size:
            raise ValueError(f"파일 크기({file_size} bytes)가 제한({self.max_file_size} bytes)을 초과합니다.")
        
        # Swift API PUT 메서드를 사용한 업로드
        try:
            # Content-Type 추정
            content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
            
            # ETag 계산 (MD5 hash)
            import hashlib
            etag = hashlib.md5(content_data).hexdigest()
            
            logger.debug(f"업로드 정보: Content-Type={content_type}, ETag={etag}")
            
            # boto3로 먼저 시도 (Swift API 호환 헤더 포함)
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=name,
                Body=content_data,
                ContentType=content_type,
                ContentLength=file_size,
                Metadata={
                    'uploaded-by': 'satoshop-django',
                    'upload-method': 'put-object'
                }
            )
            
            logger.info(f"파일 저장 성공 (boto3): {name}")
            return name
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.warning(f"boto3 업로드 실패 ({error_code}), fallback 시도: {e}")
            
            # Direct upload with fallback 사용
            success = direct_upload_with_fallback(
                self.access_key_id,
                self.secret_access_key,
                self.bucket_name,
                name,
                content_data,
                self.endpoint_url,
                self.region_name,
                self.use_ssl
            )
            
            if success:
                logger.info(f"파일 저장 성공 (fallback): {name}")
                return name
            else:
                logger.error(f"파일 저장 실패 (모든 방법): {name}")
                raise Exception(f"파일 저장에 실패했습니다: {name}")
                
        except Exception as e:
            logger.error(f"파일 저장 중 예외: {name} - {e}")
            
            # 예외 발생 시에도 fallback 시도
            try:
                success = direct_upload_with_fallback(
                    self.access_key_id,
                    self.secret_access_key,
                    self.bucket_name,
                    name,
                    content_data,
                    self.endpoint_url,
                    self.region_name,
                    self.use_ssl
                )
                
                if success:
                    logger.info(f"파일 저장 성공 (예외 후 fallback): {name}")
                    return name
            except Exception as fallback_error:
                logger.error(f"Fallback 업로드도 실패: {fallback_error}")
            
            raise Exception(f"파일 저장에 실패했습니다: {name} - {str(e)}")
    
    def _open(self, name, mode='rb'):
        """S3에서 파일 읽기 (Swift API GET 호환)"""
        try:
            logger.info(f"파일 열기 시도: {name}")
            
            response = self.client.get_object(Bucket=self.bucket_name, Key=name)
            content = response['Body'].read()
            
            logger.info(f"파일 열기 성공: {name} ({len(content)} bytes)")
            return ContentFile(content)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.warning(f"파일을 찾을 수 없음: {name}")
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {name}")
            else:
                logger.error(f"파일 열기 실패: {name} - {e}")
                raise
        except Exception as e:
            logger.error(f"파일 열기 중 예외 발생: {name} - {e}")
            raise
    
    def delete(self, name):
        """S3에서 파일 삭제"""
        try:
            logger.info(f"파일 삭제 시도: {name}")
            
            self.client.delete_object(Bucket=self.bucket_name, Key=name)
            
            logger.info(f"파일 삭제 성공: {name}")
            return True
        except ClientError as e:
            logger.error(f"파일 삭제 실패: {name} - {e}")
            return False
        except Exception as e:
            logger.error(f"파일 삭제 중 예외 발생: {name} - {e}")
            return False
    
    def exists(self, name):
        """파일이 S3에 존재하는지 확인 (HeadObject 사용 시 fallback 적용)"""
        try:
            logger.debug(f"파일 존재 확인 시도: {name}")
            
            # boto3로 HeadObject 시도
            self.client.head_object(Bucket=self.bucket_name, Key=name)
            logger.debug(f"파일 존재 확인 성공 (boto3): {name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.debug(f"파일이 존재하지 않음: {name}")
                return False
            elif error_code == '405':
                # HeadObject가 지원되지 않는 경우, ListObjects로 대체
                logger.warning(f"HeadObject 지원되지 않음, ListObjects로 대체: {name}")
                try:
                    response = self.client.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=name,
                        MaxKeys=1
                    )
                    exists = any(obj['Key'] == name for obj in response.get('Contents', []))
                    logger.debug(f"파일 존재 확인 (ListObjects): {name} - {exists}")
                    return exists
                except Exception as list_error:
                    logger.error(f"ListObjects 실패: {name} - {list_error}")
                    return False
            else:
                logger.error(f"파일 존재 확인 실패: {name} - {e}")
                return False
        except Exception as e:
            logger.error(f"파일 존재 확인 중 예외 발생: {name} - {e}")
            return False
    
    def size(self, name):
        """파일 크기 반환 (HeadObject 사용 시 fallback 적용)"""
        try:
            logger.debug(f"파일 크기 확인 시도: {name}")
            
            # boto3로 HeadObject 시도
            response = self.client.head_object(Bucket=self.bucket_name, Key=name)
            size = response['ContentLength']
            logger.debug(f"파일 크기 확인 성공 (boto3): {name} - {size} bytes")
            return size
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.debug(f"파일이 존재하지 않음: {name}")
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {name}")
            elif error_code == '405':
                # HeadObject가 지원되지 않는 경우, ListObjects로 대체
                logger.warning(f"HeadObject 지원되지 않음, ListObjects로 대체: {name}")
                try:
                    response = self.client.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=name,
                        MaxKeys=1
                    )
                    for obj in response.get('Contents', []):
                        if obj['Key'] == name:
                            size = obj['Size']
                            logger.debug(f"파일 크기 확인 (ListObjects): {name} - {size} bytes")
                            return size
                    raise FileNotFoundError(f"파일을 찾을 수 없습니다: {name}")
                except FileNotFoundError:
                    raise
                except Exception as list_error:
                    logger.error(f"ListObjects 실패: {name} - {list_error}")
                    raise Exception(f"파일 크기 확인 실패: {list_error}")
            else:
                logger.error(f"파일 크기 확인 실패: {name} - {e}")
                raise Exception(f"파일 크기 확인 실패: {e}")
        except Exception as e:
            logger.error(f"파일 크기 확인 중 예외 발생: {name} - {e}")
            raise
    
    def url(self, name):
        """파일의 URL 반환 (보안 개선된 방식)"""
        if self.custom_domain:
            # 커스텀 도메인이 설정된 경우
            protocol = 'https' if self.use_ssl else 'http'
            return f"{protocol}://{self.custom_domain}/{name}"
        else:
            # Django를 통한 프록시 URL 생성 (보안 강화)
            # AWS Access Key ID 등 민감한 정보 노출을 방지
            from django.urls import reverse
            import urllib.parse
            
            try:
                # 파일 경로를 안전하게 인코딩
                encoded_path = urllib.parse.quote(name, safe='/')
                # Django 뷰를 통한 프록시 URL 생성
                return f"/media/s3/{encoded_path}"
            except Exception as e:
                logger.warning(f"프록시 URL 생성 실패, fallback 사용: {e}")
                # fallback으로 pre-signed URL 사용 (단축된 만료 시간)
                try:
                    return self.client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': name},
                        ExpiresIn=300  # 5분 유효 (보안 강화)
                    )
                except ClientError as e:
                    raise IOError(f"S3 URL 생성 실패: {e}")
    
    def get_accessed_time(self, name):
        """파일 접근 시간 (S3에서는 지원하지 않음)"""
        return None
    
    def get_created_time(self, name):
        """파일 생성 시간"""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=name)
            return response.get('LastModified')
        except ClientError:
            return None
    
    def get_modified_time(self, name):
        """파일 수정 시간"""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=name)
            return response.get('LastModified')
        except ClientError:
            return None
    
    def get_valid_name(self, name):
        """유효한 파일명으로 변환"""
        # S3에서 사용할 수 없는 문자 제거/변환
        name = name.replace(' ', '_')
        return name
    
    def get_available_name(self, name, max_length=None):
        """사용 가능한 파일명 생성"""
        if self.file_overwrite:
            return self.get_valid_name(name)
        
        # 파일이 이미 존재하면 숫자를 붙여서 새 이름 생성
        if self.exists(name):
            dir_name, file_name = os.path.split(name)
            file_root, file_ext = os.path.splitext(file_name)
            
            count = 1
            while self.exists(name):
                name = os.path.join(dir_name, f"{file_root}_{count}{file_ext}")
                count += 1
        
        return self.get_valid_name(name)
    
    def listdir(self, path):
        """디렉토리의 파일 목록 반환"""
        if path and not path.endswith('/'):
            path += '/'
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=path,
                Delimiter='/'
            )
            
            directories = []
            files = []
            
            # 디렉토리 목록
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    dir_name = prefix['Prefix'][len(path):].rstrip('/')
                    if dir_name:
                        directories.append(dir_name)
            
            # 파일 목록
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_name = obj['Key'][len(path):]
                    if file_name and '/' not in file_name:
                        files.append(file_name)
            
            return directories, files
        except ClientError as e:
            raise IOError(f"S3 디렉토리 목록 조회 실패: {e}")
    
    def generate_filename(self, filename):
        """고유한 파일명 생성"""
        # 파일 확장자 분리
        name, ext = os.path.splitext(filename)
        
        # UUID와 타임스탬프로 고유한 파일명 생성
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"{timestamp}_{unique_id}{ext}" 