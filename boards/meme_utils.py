"""
밈 게시판 이미지 처리 유틸리티
"""

import os
import io
import logging
from typing import Dict, Any, Tuple
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def process_meme_image(image_file: UploadedFile, max_width: int = 1000) -> Dict[str, Any]:
    """
    밈 이미지를 처리합니다.
    - 1000px 초과시 비율 유지하며 리사이즈
    - GIF를 제외하고 WebP로 변환
    
    Args:
        image_file: 업로드된 이미지 파일
        max_width: 최대 너비 (기본값: 1000px)
    
    Returns:
        처리 결과 정보
        {
            'success': bool,
            'processed_file': ContentFile,
            'original_size': tuple,
            'processed_size': tuple,
            'is_gif': bool,
            'error': str (실패시)
        }
    """
    if not PIL_AVAILABLE:
        return {
            'success': False,
            'error': 'Pillow 패키지가 설치되지 않았습니다.'
        }
    
    try:
        logger.info(f"밈 이미지 처리 시작: {image_file.name}")
        
        # 파일 확장자 확인
        file_ext = os.path.splitext(image_file.name)[1].lower()
        is_gif = file_ext == '.gif'
        
        # GIF 파일은 변환하지 않고 크기만 체크
        if is_gif:
            image_file.seek(0)
            with Image.open(image_file) as img:
                original_size = img.size
                width, height = original_size
                
                # 1000px 이하면 원본 그대로 반환
                if width <= max_width:
                    image_file.seek(0)
                    return {
                        'success': True,
                        'processed_file': ContentFile(image_file.read(), name=image_file.name),
                        'original_size': original_size,
                        'processed_size': original_size,
                        'is_gif': True
                    }
                
                # 1000px 초과시 리사이즈 (GIF 애니메이션 유지)
                ratio = max_width / width
                new_height = int(height * ratio)
                
                # GIF 애니메이션 처리
                frames = []
                durations = []
                
                try:
                    while True:
                        frame = img.copy()
                        frame = frame.resize((max_width, new_height), Image.Resampling.LANCZOS)
                        frames.append(frame)
                        durations.append(img.info.get('duration', 100))
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                
                # 리사이즈된 GIF 저장
                output = io.BytesIO()
                frames[0].save(
                    output,
                    format='GIF',
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=img.info.get('loop', 0)
                )
                output.seek(0)
                
                return {
                    'success': True,
                    'processed_file': ContentFile(output.getvalue(), name=image_file.name),
                    'original_size': original_size,
                    'processed_size': (max_width, new_height),
                    'is_gif': True
                }
        
        # GIF가 아닌 경우 WebP로 변환
        with Image.open(image_file) as img:
            original_size = img.size
            width, height = original_size
            
            # EXIF 정보에 따른 회전 보정
            img = ImageOps.exif_transpose(img)
            
            # WebP는 투명도를 지원하므로 RGBA 모드 유지
            if img.mode == 'RGBA':
                # RGBA 그대로 유지 (투명도 보존)
                pass
            elif img.mode == 'LA':
                # LA를 RGBA로 변환
                img = img.convert('RGBA')
            elif img.mode == 'P' and 'transparency' in img.info:
                # 팔레트 모드에서 투명도가 있는 경우 RGBA로 변환
                img = img.convert('RGBA')
            else:
                # 투명도가 없는 경우 RGB로 변환
                img = img.convert('RGB')
            
            # 1000px 초과시 리사이즈
            if width > max_width:
                ratio = max_width / width
                new_height = int(height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                processed_size = (max_width, new_height)
            else:
                processed_size = original_size
            
            # WebP로 저장
            output = io.BytesIO()
            img.save(output, format='WebP', quality=85, method=6)
            output.seek(0)
            
            # 파일명 변경
            base_name = os.path.splitext(image_file.name)[0]
            new_filename = f"{base_name}.webp"
            
            return {
                'success': True,
                'processed_file': ContentFile(output.getvalue(), name=new_filename),
                'original_size': original_size,
                'processed_size': processed_size,
                'is_gif': False
            }
    
    except Exception as e:
        error_msg = f"밈 이미지 처리 실패: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


def create_meme_thumbnail(image_file: ContentFile, target_ratio: Tuple[int, int] = (4, 3), 
                         target_width: int = 300) -> Dict[str, Any]:
    """
    밈 썸네일을 생성합니다.
    - 4:3 비율로 크롭
    - 300px 너비로 리사이즈
    - WebP 포맷으로 저장
    
    Args:
        image_file: 처리된 이미지 파일
        target_ratio: 목표 비율 (기본값: 4:3)
        target_width: 목표 너비 (기본값: 300px)
    
    Returns:
        썸네일 생성 결과
    """
    if not PIL_AVAILABLE:
        return {
            'success': False,
            'error': 'Pillow 패키지가 설치되지 않았습니다.'
        }
    
    try:
        logger.info("밈 썸네일 생성 시작")
        
        # 이미지 열기
        image_file.seek(0)
        with Image.open(image_file) as img:
            # GIF의 경우 첫 프레임만 사용
            if img.format == 'GIF':
                img.seek(0)
            
            # WebP는 투명도를 지원하므로 가능한 경우 RGBA 유지
            if img.mode == 'RGBA':
                # RGBA 그대로 유지 (투명도 보존)
                pass
            elif img.mode == 'LA':
                # LA를 RGBA로 변환
                img = img.convert('RGBA')
            elif img.mode == 'P' and 'transparency' in img.info:
                # 팔레트 모드에서 투명도가 있는 경우 RGBA로 변환
                img = img.convert('RGBA')
            else:
                # 투명도가 없는 경우 RGB로 변환
                img = img.convert('RGB')
            
            # 목표 높이 계산
            target_height = int(target_width * target_ratio[1] / target_ratio[0])
            target_size = (target_width, target_height)
            
            # ImageOps.fit을 사용하여 비율 맞춰 크롭 및 리사이즈
            thumbnail = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
            
            # WebP로 저장
            output = io.BytesIO()
            thumbnail.save(output, format='WebP', quality=85, method=6)
            output.seek(0)
            
            # 썸네일 파일명 생성
            base_name = os.path.splitext(image_file.name)[0]
            if base_name.endswith('_processed'):
                base_name = base_name[:-10]  # '_processed' 제거
            thumbnail_filename = f"{base_name}_thumb.webp"
            
            return {
                'success': True,
                'thumbnail_file': ContentFile(output.getvalue(), name=thumbnail_filename),
                'thumbnail_size': target_size
            }
    
    except Exception as e:
        error_msg = f"썸네일 생성 실패: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


def validate_meme_image(file: UploadedFile) -> Dict[str, Any]:
    """
    밈 이미지 파일을 검증합니다.
    
    Args:
        file: 업로드된 파일
    
    Returns:
        검증 결과
    """
    errors = []
    
    # 파일 크기 검사 (최대 10MB)
    max_file_size = 10 * 1024 * 1024
    if file.size > max_file_size:
        errors.append(f'파일 크기가 10MB를 초과합니다.')
    
    # 파일 확장자 검사
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext not in allowed_extensions:
        errors.append(f'허용되지 않는 파일 형식입니다. 허용 형식: {", ".join(allowed_extensions)}')
    
    # 이미지 파일인지 확인
    try:
        if PIL_AVAILABLE:
            file.seek(0)
            with Image.open(file) as img:
                # 이미지 크기 확인
                width, height = img.size
                if width < 100 or height < 100:
                    errors.append('이미지가 너무 작습니다. 최소 100x100 픽셀 이상이어야 합니다.')
            file.seek(0)
    except Exception:
        errors.append('유효한 이미지 파일이 아닙니다.')
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }