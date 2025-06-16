"""
iwinv 오브젝트 스토리지 호환을 위한 직접 HTTP 업로드
Swift API PUT 메서드 구현
"""

import requests
import hashlib
import hmac
import base64
import urllib.parse
from datetime import datetime
import logging
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import mimetypes

logger = logging.getLogger(__name__)


def create_signature_v4(method, url, headers, payload, access_key, secret_key, region, service='s3'):
    """AWS Signature Version 4 생성"""
    
    # 1. Canonical Request 생성
    parsed_url = urllib.parse.urlparse(url)
    canonical_uri = parsed_url.path
    canonical_querystring = parsed_url.query
    
    # 헤더 정렬 및 정규화
    canonical_headers = []
    signed_headers = []
    for key in sorted(headers.keys()):
        canonical_headers.append(f"{key.lower()}:{headers[key]}")
        signed_headers.append(key.lower())
    
    canonical_headers_str = '\n'.join(canonical_headers) + '\n'
    signed_headers_str = ';'.join(signed_headers)
    
    # payload hash
    payload_hash = hashlib.sha256(payload).hexdigest()
    
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers_str}\n{signed_headers_str}\n{payload_hash}"
    
    # 2. String to Sign 생성
    timestamp = headers['x-amz-date']
    date = timestamp[:8]
    credential_scope = f"{date}/{region}/{service}/aws4_request"
    string_to_sign = f"AWS4-HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    
    # 3. Signing Key 생성
    def sign(key, message):
        return hmac.new(key, message.encode('utf-8'), hashlib.sha256).digest()
    
    k_date = sign(f"AWS4{secret_key}".encode('utf-8'), date)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    
    # 4. Signature 생성
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # 5. Authorization 헤더 생성
    authorization = f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers_str}, Signature={signature}"
    
    return authorization


def direct_s3_upload(bucket_name, key, content, content_type, access_key, secret_key, endpoint_url, region='kr-standard'):
    """
    직접 HTTP PUT 요청으로 iwinv 오브젝트 스토리지에 파일 업로드
    Swift API 호환 구현
    """
    try:
        logger.info(f"Swift API 직접 업로드 시작: {key}")
        
        # URL 생성 (path-style addressing)
        parsed_endpoint = urllib.parse.urlparse(endpoint_url)
        url = f"{endpoint_url}/{bucket_name}/{key}"
        
        # 현재 시간 생성
        now = datetime.utcnow()
        timestamp = now.strftime('%Y%m%dT%H%M%SZ')
        
        # MD5 해시 계산 (ETag)
        content_md5 = hashlib.md5(content).hexdigest()
        
        # Swift API 호환 헤더 준비
        headers = {
            'Host': parsed_endpoint.netloc,
            'Content-Type': content_type,
            'Content-Length': str(len(content)),
            'ETag': content_md5,  # Swift API ETag 헤더
            'x-amz-content-sha256': hashlib.sha256(content).hexdigest(),
            'x-amz-date': timestamp,
            'x-amz-storage-class': 'STANDARD',  # 스토리지 클래스 명시
        }
        
        # Authorization 헤더 생성
        authorization = create_signature_v4('PUT', url, headers, content, access_key, secret_key, region)
        headers['Authorization'] = authorization
        
        logger.debug(f"업로드 URL: {url}")
        logger.debug(f"Content-Length: {len(content)}")
        logger.debug(f"Content-Type: {content_type}")
        logger.debug(f"ETag: {content_md5}")
        
        # HTTP PUT 요청으로 직접 업로드 (Swift API 호환)
        response = requests.put(
            url,
            data=content,
            headers=headers,
            timeout=60,  # 타임아웃 연장
            verify=True,
            stream=False  # 스트리밍 비활성화
        )
        
        logger.debug(f"응답 상태: {response.status_code}")
        logger.debug(f"응답 헤더: {dict(response.headers)}")
        
        # Swift API 성공 상태 코드 확인
        if response.status_code in [200, 201, 202]:
            logger.info(f"Swift API 직접 업로드 성공: {key} (상태: {response.status_code})")
            return {
                'success': True,
                'status_code': response.status_code,
                'etag': response.headers.get('ETag', content_md5).strip('"'),
                'content_length': response.headers.get('Content-Length'),
            }
        else:
            logger.error(f"Swift API 직접 업로드 실패: {response.status_code}")
            logger.error(f"응답 내용: {response.text}")
            return {
                'success': False,
                'status_code': response.status_code,
                'error': response.text,
            }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP 요청 오류: {e}")
        return {
            'success': False,
            'error': f'HTTP 요청 실패: {str(e)}',
        }
    except Exception as e:
        logger.error(f"Swift API 직접 업로드 중 오류: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
        }


def direct_upload_with_fallback(access_key, secret_key, bucket_name, key, content_data, endpoint_url, region='kr-standard', use_ssl=True):
    """
    boto3 업로드 시도 후 실패하면 Swift API 직접 HTTP 업로드로 fallback
    """
    # Content-Type 추정
    content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
    
    # 1. 먼저 boto3로 시도
    try:
        logger.info(f"boto3 업로드 시도: {key}")
        
        config = Config(
            signature_version='s3v4',
            s3={
                'addressing_style': 'path',
                'payload_signing_enabled': True,
            },
            region_name=region,
            retries={'max_attempts': 1},  # 빠른 fallback을 위해 재시도 1회로 제한
            read_timeout=30,
            connect_timeout=10
        )
        
        client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            use_ssl=use_ssl,
            config=config
        )
        
        # boto3로 업로드 시도 (추가 메타데이터 포함)
        client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content_data,
            ContentType=content_type,
            ContentLength=len(content_data),
            Metadata={
                'uploaded-by': 'django-workflow',
                'upload-timestamp': datetime.utcnow().isoformat(),
            }
        )
        
        logger.info(f"boto3 업로드 성공: {key}")
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = str(e)
        
        logger.warning(f"boto3 업로드 실패 ({error_code}): {error_message}")
        logger.info(f"Swift API 직접 업로드로 재시도...")
        
        # 2. Swift API 직접 HTTP 업로드로 fallback
        result = direct_s3_upload(
            bucket_name=bucket_name,
            key=key,
            content=content_data,
            content_type=content_type,
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            region=region
        )
        
        return result['success']
            
    except Exception as e:
        logger.warning(f"boto3 업로드 중 예외 발생: {e}")
        logger.info(f"Swift API 직접 업로드로 재시도...")
        
        # 예외가 발생한 경우에도 Swift API 직접 HTTP 업로드로 시도
        result = direct_s3_upload(
            bucket_name=bucket_name,
            key=key,
            content=content_data,
            content_type=content_type,
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            region=region
        )
        
        return result['success'] 