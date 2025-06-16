"""
Stores 앱 시그널 처리
"""

import logging
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from .models import Store, StoreImage
from storage.utils import delete_file_from_s3

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=StoreImage)
def delete_store_image_file(sender, instance, **kwargs):
    """
    StoreImage가 삭제되기 전에 S3에서 파일을 삭제합니다.
    Django Admin이나 어떤 방식으로 삭제되든 자동으로 실행됩니다.
    """
    if instance.file_path:
        logger.info(f"이미지 삭제 시그널 실행: {instance.original_name} (파일: {instance.file_path})")
        
        try:
            # S3에서 파일 삭제
            delete_result = delete_file_from_s3(instance.file_path)
            
            if delete_result['success']:
                logger.info(f"S3 파일 삭제 성공: {instance.file_path}")
            else:
                logger.warning(f"S3 파일 삭제 실패: {instance.file_path} - {delete_result.get('error')}")
                
        except Exception as e:
            logger.error(f"S3 파일 삭제 중 예외 발생: {instance.file_path} - {e}")
    else:
        logger.debug(f"파일 경로가 없는 이미지 삭제: {instance.original_name}")


@receiver(post_delete, sender=StoreImage)
def log_store_image_deleted(sender, instance, **kwargs):
    """
    StoreImage 삭제 후 로그 기록
    """
    logger.info(f"StoreImage 삭제 완료: {instance.original_name} (ID: {instance.id})")


@receiver(pre_delete, sender=Store)
def delete_store_related_files(sender, instance, **kwargs):
    """
    Store가 삭제되기 전에 관련된 모든 이미지 파일을 S3에서 삭제합니다.
    """
    logger.info(f"스토어 삭제 시그널 실행: {instance.store_name} (ID: {instance.store_id})")
    
    # 스토어 관련 이미지들을 조회하고 삭제
    store_images = instance.images.all()
    deleted_count = 0
    
    for image in store_images:
        if image.file_path:
            try:
                delete_result = delete_file_from_s3(image.file_path)
                if delete_result['success']:
                    deleted_count += 1
                    logger.info(f"스토어 삭제 시 이미지 파일 삭제 성공: {image.file_path}")
                else:
                    logger.warning(f"스토어 삭제 시 이미지 파일 삭제 실패: {image.file_path} - {delete_result.get('error')}")
            except Exception as e:
                logger.error(f"스토어 삭제 시 이미지 파일 삭제 중 예외: {image.file_path} - {e}")
    
    if deleted_count > 0:
        logger.info(f"스토어 삭제 시 총 {deleted_count}개의 이미지 파일 삭제됨")


@receiver(post_delete, sender=Store)
def log_store_deleted(sender, instance, **kwargs):
    """
    Store 삭제 후 로그 기록
    """
    logger.info(f"Store 삭제 완료: {instance.store_name} (ID: {instance.store_id})") 