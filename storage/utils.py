"""
S3 오브젝트 스토리지 관련 유틸리티 함수들
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
from .backends import S3Storage
from django.core.files.base import ContentFile
from django.db import models
import io

# 조건부 import
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pillow_avif  # AVIF 지원
    AVIF_AVAILABLE = True
except ImportError:
    AVIF_AVAILABLE = False

# 로거 설정
logger = logging.getLogger(__name__)


def generate_file_path(original_filename: str, prefix: str = None) -> str:
    """
    업로드할 파일의 경로를 생성합니다.
    
    Args:
        original_filename: 원본 파일명
        prefix: 폴더 prefix (예: 'notices', 'boards')
    
    Returns:
        생성된 파일 경로
    """
    # 파일 확장자 추출
    file_ext = os.path.splitext(original_filename)[1].lower()
    
    # UUID로 고유한 파일명 생성
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    
    # 날짜별 폴더 구조 생성 (YYYY/MM/DD)
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    if prefix:
        return f"{prefix}/{date_path}/{unique_filename}"
    else:
        return f"{date_path}/{unique_filename}"


def upload_file_to_s3(
    file: UploadedFile, 
    prefix: str = None, 
    storage: S3Storage = None
) -> Dict[str, Any]:
    """
    파일을 S3에 업로드합니다.
    
    Args:
        file: Django UploadedFile 객체
        prefix: 폴더 prefix
        storage: S3Storage 인스턴스 (없으면 새로 생성)
    
    Returns:
        업로드 결과 정보
        {
            'success': bool,
            'file_path': str,
            'file_url': str,
            'original_name': str,
            'file_size': int,
            'error': str (실패시)
        }
    """
    logger.info(f"=== S3 파일 업로드 시작: {file.name} ===")
    logger.info(f"파일 크기: {file.size} bytes")
    logger.info(f"prefix: {prefix}")
    
    if storage is None:
        logger.debug("새로운 S3Storage 인스턴스 생성")
        try:
            storage = S3Storage()
            logger.info("S3Storage 인스턴스 생성 성공")
        except Exception as e:
            logger.error(f"S3Storage 인스턴스 생성 실패: {e}")
            return {
                'success': False,
                'error': f'S3Storage 초기화 실패: {str(e)}',
                'original_name': file.name,
                'file_size': file.size if hasattr(file, 'size') else 0,
            }
    
    try:
        # 파일 검증
        logger.debug(f"파일 정보: name={file.name}, size={file.size}, content_type={getattr(file, 'content_type', 'unknown')}")
        
        # 파일 경로 생성
        logger.debug("파일 경로 생성 시작")
        file_path = generate_file_path(file.name, prefix)
        logger.info(f"생성된 파일 경로: {file_path}")
        
        # 파일 업로드
        logger.info("S3 스토리지에 파일 저장 시작")
        logger.debug(f"storage.save() 호출: file_path={file_path}")
        
        saved_path = storage.save(file_path, file)
        logger.info(f"파일 저장 완료: {saved_path}")
        
        # 파일 URL 생성
        logger.debug("파일 URL 생성 시작")
        try:
            file_url = storage.url(saved_path)
            logger.info(f"생성된 파일 URL: {file_url}")
        except Exception as url_error:
            logger.warning(f"파일 URL 생성 실패: {url_error}, 기본 URL 사용")
            file_url = f"/media/{saved_path}"  # fallback URL
        
        result = {
            'success': True,
            'file_path': saved_path,
            'file_url': file_url,
            'original_name': file.name,
            'file_size': file.size,
        }
        
        logger.info(f"=== S3 파일 업로드 성공: {file.name} ===")
        logger.debug(f"최종 결과: {result}")
        return result
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"=== S3 파일 업로드 실패: {file.name} ===")
        logger.error(f"오류 메시지: {error_msg}")
        logger.error(f"오류 상세:", exc_info=True)
        
        return {
            'success': False,
            'error': error_msg,
            'original_name': file.name,
            'file_size': file.size if hasattr(file, 'size') else 0,
        }


def delete_file_from_s3(file_path: str, storage: S3Storage = None) -> Dict[str, Any]:
    """
    S3에서 파일을 삭제합니다.
    
    Args:
        file_path: 삭제할 파일 경로
        storage: S3Storage 인스턴스
    
    Returns:
        삭제 결과
        {
            'success': bool,
            'error': str (실패시)
        }
    """
    if storage is None:
        storage = S3Storage()
    
    try:
        storage.delete(file_path)
        return {'success': True}
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_file_url(file_path: str, storage: S3Storage = None) -> Optional[str]:
    """
    파일의 URL을 반환합니다.
    
    Args:
        file_path: 파일 경로
        storage: S3Storage 인스턴스
    
    Returns:
        파일 URL (실패시 None)
    """
    if storage is None:
        storage = S3Storage()
    
    try:
        return storage.url(file_path)
    except Exception:
        return None


def validate_file(file: UploadedFile) -> Dict[str, Any]:
    """
    업로드된 파일을 검증합니다.
    
    Args:
        file: Django UploadedFile 객체
    
    Returns:
        검증 결과
        {
            'is_valid': bool,
            'errors': list,
            'file_info': dict
        }
    """
    logger.debug(f"=== 파일 검증 시작: {file.name} ===")
    errors = []
    
    # 파일 크기 제한 (기본 10MB)
    max_file_size = getattr(settings, 'MAX_FILE_SIZE', 10 * 1024 * 1024)
    logger.debug(f"파일 크기 검사: {file.size} bytes (제한: {max_file_size} bytes)")
    
    if file.size > max_file_size:
        error_msg = f'파일 크기가 {max_file_size // (1024 * 1024)}MB를 초과합니다.'
        logger.warning(f"파일 크기 초과: {error_msg}")
        errors.append(error_msg)
    
    # 허용된 파일 확장자 검사
    allowed_extensions = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', None)
    logger.debug(f"허용된 확장자: {allowed_extensions}")
    
    if allowed_extensions:
        file_ext = os.path.splitext(file.name)[1].lower()
        logger.debug(f"파일 확장자: {file_ext}")
        
        if file_ext not in allowed_extensions:
            error_msg = f'허용되지 않는 파일 형식입니다. 허용 형식: {", ".join(allowed_extensions)}'
            logger.warning(f"허용되지 않는 확장자: {error_msg}")
            errors.append(error_msg)
    
    # 파일명 길이 검사
    logger.debug(f"파일명 길이: {len(file.name)} 문자")
    if len(file.name) > 255:
        error_msg = '파일명이 너무 깁니다.'
        logger.warning(f"파일명 길이 초과: {error_msg}")
        errors.append(error_msg)
    
    is_valid = len(errors) == 0
    result = {
        'is_valid': is_valid,
        'errors': errors,
        'file_info': {
            'name': file.name,
            'size': file.size,
            'content_type': getattr(file, 'content_type', 'unknown')
        }
    }
    
    logger.debug(f"=== 파일 검증 완료: {file.name} ===")
    logger.debug(f"검증 결과: {'성공' if is_valid else '실패'}")
    if not is_valid:
        logger.debug(f"검증 오류: {errors}")
    
    return result


def get_file_info(file_path: str, storage: S3Storage = None) -> Optional[Dict[str, Any]]:
    """
    S3에 저장된 파일의 정보를 반환합니다.
    
    Args:
        file_path: 파일 경로
        storage: S3Storage 인스턴스
    
    Returns:
        파일 정보 (실패시 None)
        {
            'exists': bool,
            'size': int,
            'modified_time': datetime,
            'url': str
        }
    """
    if storage is None:
        storage = S3Storage()
    
    try:
        if not storage.exists(file_path):
            return {'exists': False}
        
        return {
            'exists': True,
            'size': storage.size(file_path),
            'modified_time': storage.get_modified_time(file_path),
            'url': storage.url(file_path)
        }
    
    except Exception:
        return None


def bulk_upload_files(files: list, prefix: str = None) -> Dict[str, Any]:
    """
    여러 파일을 한번에 업로드합니다.
    
    Args:
        files: UploadedFile 객체들의 리스트
        prefix: 폴더 prefix
    
    Returns:
        업로드 결과
        {
            'success_count': int,
            'failed_count': int,
            'results': list,
            'errors': list
        }
    """
    results = []
    errors = []
    success_count = 0
    failed_count = 0
    
    storage = S3Storage()
    
    for file in files:
        # 파일 검증
        validation = validate_file(file)
        if not validation['is_valid']:
            errors.extend(validation['errors'])
            failed_count += 1
            continue
        
        # 파일 업로드
        result = upload_file_to_s3(file, prefix, storage)
        results.append(result)
        
        if result['success']:
            success_count += 1
        else:
            failed_count += 1
            errors.append(f"{file.name}: {result.get('error', '알 수 없는 오류')}")
    
    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'results': results,
        'errors': errors
    }


def process_store_image(image_file, target_width=1000, target_ratio=(16, 9)) -> Dict[str, Any]:
    """
    스토어 이미지를 처리합니다.
    - 16:9 비율로 자르기
    - 1000px 너비로 리사이즈
    - AVIF 포맷으로 변환
    
    Args:
        image_file: 업로드된 이미지 파일
        target_width: 목표 너비 (기본값: 1000px)
        target_ratio: 목표 비율 (기본값: 16:9)
    
    Returns:
        처리 결과 정보
        {
            'success': bool,
            'processed_file': ContentFile,
            'original_size': tuple,
            'processed_size': tuple,
            'error': str (실패시)
        }
    """
    try:
        if not PIL_AVAILABLE:
            return {
                'success': False,
                'error': 'Pillow 패키지가 설치되지 않았습니다. pip install Pillow을 실행해주세요.'
            }
        
        logger.info(f"이미지 처리 시작: {image_file.name}")
        
        # 이미지 열기
        with Image.open(image_file) as img:
            original_size = img.size
            logger.info(f"원본 이미지 크기: {original_size}")
            
            # RGB 모드로 변환 (AVIF는 RGBA를 지원하지 않을 수 있음)
            if img.mode in ('RGBA', 'LA'):
                # 투명 배경을 흰색으로 변환
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 목표 비율 계산
            target_height = int(target_width * target_ratio[1] / target_ratio[0])
            target_size = (target_width, target_height)
            
            # 이미지 자르기 및 리사이즈 (16:9 비율 맞추기)
            img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
            
            logger.info(f"처리된 이미지 크기: {img.size}")
            
            # 포맷 결정 및 저장
            output = io.BytesIO()
            
            if AVIF_AVAILABLE:
                # AVIF 포맷으로 저장
                img.save(output, format='AVIF', quality=85, speed=6)
                file_ext = '.avif'
            else:
                # AVIF가 지원되지 않으면 WebP로 저장
                img.save(output, format='WebP', quality=85, method=6)
                file_ext = '.webp'
            
            output.seek(0)
            
            # 파일명 변경
            original_name = os.path.splitext(image_file.name)[0]
            processed_filename = f"{original_name}{file_ext}"
            
            processed_file = ContentFile(output.getvalue(), name=processed_filename)
            
            return {
                'success': True,
                'processed_file': processed_file,
                'original_size': original_size,
                'processed_size': img.size,
                'filename': processed_filename
            }
            
    except ImportError as e:
        error_msg = f"이미지 처리에 필요한 패키지가 설치되지 않았습니다: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"이미지 처리 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


def upload_store_image(image_file, store, user) -> Dict[str, Any]:
    """
    스토어 이미지를 처리하고 업로드합니다.
    
    Args:
        image_file: 업로드된 이미지 파일
        store: Store 모델 인스턴스
        user: 업로드하는 사용자
    
    Returns:
        업로드 결과
        {
            'success': bool,
            'store_image': StoreImage (성공시),
            'error': str (실패시)
        }
    """
    try:
        from stores.models import StoreImage
        
        # 이미지 처리
        process_result = process_store_image(image_file)
        if not process_result['success']:
            return process_result
        
        # S3에 업로드
        prefix = f"stores/{store.store_id}/images"
        upload_result = upload_file_to_s3(
            process_result['processed_file'], 
            prefix=prefix
        )
        
        if not upload_result['success']:
            return upload_result
        
        # DB에 저장
        # 다음 순서 계산
        last_order = StoreImage.objects.filter(store=store).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        # 파일 크기 다시 계산 (ContentFile에서)
        process_result['processed_file'].seek(0)
        file_content = process_result['processed_file'].read()
        actual_file_size = len(file_content)
        process_result['processed_file'].seek(0)  # 다시 처음으로
        
        store_image = StoreImage.objects.create(
            store=store,
            original_name=image_file.name,
            file_path=upload_result['file_path'],
            file_url=upload_result['file_url'],
            file_size=actual_file_size,
            width=process_result['processed_size'][0],
            height=process_result['processed_size'][1],
            order=last_order + 1,
            uploaded_by=user
        )
        
        return {
            'success': True,
            'store_image': store_image
        }
        
    except Exception as e:
        error_msg = f"스토어 이미지 업로드 실패: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


def upload_product_image(image_file, product, user) -> Dict[str, Any]:
    """
    상품 이미지를 처리하고 업로드합니다.
    
    Args:
        image_file: 업로드된 이미지 파일
        product: Product 모델 인스턴스
        user: 업로드하는 사용자
    
    Returns:
        업로드 결과
        {
            'success': bool,
            'product_image': ProductImage (성공시),
            'error': str (실패시)
        }
    """
    try:
        from products.models import ProductImage
        
        # 이미지 처리 (1:1 비율로 500x500 크기)
        process_result = process_product_image(image_file)
        if not process_result['success']:
            return process_result
        
        # S3에 업로드
        prefix = f"products/{product.store.store_id}/{product.id}/images"
        upload_result = upload_file_to_s3(
            process_result['processed_file'], 
            prefix=prefix
        )
        
        if not upload_result['success']:
            return upload_result
        
        # DB에 저장
        # 다음 순서 계산
        last_order = ProductImage.objects.filter(product=product).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        # 파일 크기 다시 계산 (ContentFile에서)
        process_result['processed_file'].seek(0)
        file_content = process_result['processed_file'].read()
        actual_file_size = len(file_content)
        process_result['processed_file'].seek(0)  # 다시 처음으로
        
        product_image = ProductImage.objects.create(
            product=product,
            original_name=image_file.name,
            file_path=upload_result['file_path'],
            file_url=upload_result['file_url'],
            file_size=actual_file_size,
            width=process_result['processed_size'][0],
            height=process_result['processed_size'][1],
            order=last_order + 1,
            uploaded_by=user
        )
        
        return {
            'success': True,
            'product_image': product_image
        }
        
    except Exception as e:
        error_msg = f"상품 이미지 업로드 실패: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


def process_product_image(image_file, target_size=500) -> Dict[str, Any]:
    """
    상품 이미지를 처리합니다.
    - 1:1 비율로 자르기
    - 500x500px로 리사이즈
    - AVIF 포맷으로 변환
    
    Args:
        image_file: 업로드된 이미지 파일
        target_size: 목표 크기 (기본값: 500px)
    
    Returns:
        처리 결과 정보
        {
            'success': bool,
            'processed_file': ContentFile,
            'original_size': tuple,
            'processed_size': tuple,
            'error': str (실패시)
        }
    """
    try:
        if not PIL_AVAILABLE:
            return {
                'success': False,
                'error': 'Pillow 패키지가 설치되지 않았습니다. pip install Pillow을 실행해주세요.'
            }
        
        logger.info(f"상품 이미지 처리 시작: {image_file.name}")
        
        # 이미지 열기
        with Image.open(image_file) as img:
            original_size = img.size
            logger.info(f"원본 이미지 크기: {original_size}")
            
            # RGB 모드로 변환 (AVIF는 RGBA를 지원하지 않을 수 있음)
            if img.mode in ('RGBA', 'LA'):
                # 투명 배경을 흰색으로 변환
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 1:1 비율로 자르기 (중앙 기준)
            width, height = img.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            img = img.crop((left, top, right, bottom))
            
            # 목표 크기로 리사이즈
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
            logger.info(f"처리된 이미지 크기: {img.size}")
            
            # 포맷 결정 및 저장
            output = io.BytesIO()
            
            if AVIF_AVAILABLE:
                # AVIF 포맷으로 저장
                img.save(output, format='AVIF', quality=85, speed=6)
                file_ext = '.avif'
            else:
                # AVIF가 지원되지 않으면 WebP로 저장
                img.save(output, format='WebP', quality=85, method=6)
                file_ext = '.webp'
            
            output.seek(0)
            
            # 파일명 변경
            original_name = os.path.splitext(image_file.name)[0]
            processed_filename = f"{original_name}{file_ext}"
            
            processed_file = ContentFile(output.getvalue(), name=processed_filename)
            
            return {
                'success': True,
                'processed_file': processed_file,
                'original_size': original_size,
                'processed_size': img.size,
                'filename': processed_filename
            }
            
    except ImportError as e:
        error_msg = f"이미지 처리에 필요한 패키지가 설치되지 않았습니다: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"상품 이미지 처리 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        } 