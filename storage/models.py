"""
첨부파일 관리를 위한 Django 모델들
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.conf import settings


class AttachmentManager(models.Manager):
    """첨부파일 모델 매니저"""
    
    def for_object(self, obj):
        """특정 객체에 연결된 첨부파일들을 반환"""
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=content_type, object_id=obj.pk)
    
    def active(self):
        """활성 상태인 첨부파일들을 반환"""
        return self.filter(is_deleted=False)


class Attachment(models.Model):
    """
    첨부파일 모델
    GenericForeignKey를 사용하여 어떤 모델에든 첨부할 수 있음
    """
    
    # Generic Foreign Key로 어떤 모델에든 연결 가능
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 파일 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_size = models.PositiveIntegerField(verbose_name='파일 크기 (bytes)')
    file_type = models.CharField(max_length=50, blank=True, verbose_name='파일 타입')
    
    # 메타데이터
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='업로드 일시')
    uploaded_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='업로드한 사용자'
    )
    
    # 상태 관리
    is_deleted = models.BooleanField(default=False, verbose_name='삭제 여부')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제 일시')
    
    # 추가 정보
    description = models.TextField(blank=True, verbose_name='설명')
    download_count = models.PositiveIntegerField(default=0, verbose_name='다운로드 횟수')
    
    objects = AttachmentManager()
    
    class Meta:
        verbose_name = '첨부파일'
        verbose_name_plural = '첨부파일들'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.get_file_size_display()})"
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_file_url(self):
        """S3 파일의 URL을 생성하여 반환"""
        try:
            # S3 설정값들
            endpoint_url = getattr(settings, 'S3_ENDPOINT_URL', None)
            bucket_name = getattr(settings, 'S3_BUCKET_NAME', None)
            use_ssl = getattr(settings, 'S3_USE_SSL', True)
            
            if not endpoint_url or not bucket_name:
                return None
            
            # URL 생성
            protocol = 'https' if use_ssl else 'http'
            if endpoint_url.startswith(('http://', 'https://')):
                base_url = endpoint_url
            else:
                base_url = f"{protocol}://{endpoint_url}"
            
            # Path-style URL 생성
            url = f"{base_url}/{bucket_name}/{self.file_path}"
            return url
        except Exception:
            return None
    
    def get_file_extension(self):
        """파일 확장자 반환"""
        import os
        return os.path.splitext(self.original_name)[1].lower()
    
    def is_image(self):
        """이미지 파일인지 확인"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        return self.get_file_extension() in image_extensions
    
    def is_document(self):
        """문서 파일인지 확인"""
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt']
        return self.get_file_extension() in doc_extensions
    
    def soft_delete(self):
        """소프트 삭제"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def hard_delete(self):
        """하드 삭제 (오브젝트 스토리지에서도 파일 삭제)"""
        from .utils import delete_file_from_s3
        
        # S3에서 파일 삭제
        delete_result = delete_file_from_s3(self.file_path)
        if delete_result['success']:
            # DB에서도 삭제
            self.delete()
            return True
        else:
            # S3 삭제 실패 시에도 DB는 삭제 (로그로 기록)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'오브젝트 스토리지 파일 삭제 실패: {self.file_path} - {delete_result.get("error")}')
            self.delete()
            return False
    
    def delete(self, using=None, keep_parents=False):
        """Django 기본 delete 메서드 오버라이드 - 오브젝트 스토리지에서도 파일 삭제"""
        from .utils import delete_file_from_s3
        
        # S3에서 파일 삭제 시도
        delete_result = delete_file_from_s3(self.file_path)
        if not delete_result['success']:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'오브젝트 스토리지 파일 삭제 실패: {self.file_path} - {delete_result.get("error")}')
        
        # DB에서 삭제
        return super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """삭제 취소"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def increment_download_count(self):
        """다운로드 횟수 증가"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class TemporaryUpload(models.Model):
    """
    임시 업로드 파일 모델
    실제 모델에 연결되기 전까지 임시로 저장
    """
    
    # 파일 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_size = models.PositiveIntegerField(verbose_name='파일 크기 (bytes)')
    file_type = models.CharField(max_length=50, blank=True, verbose_name='파일 타입')
    
    # 업로드 정보
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='업로드 일시')
    uploaded_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE,
        verbose_name='업로드한 사용자'
    )
    
    # 세션 정보 (로그인하지 않은 사용자용)
    session_key = models.CharField(max_length=40, blank=True, verbose_name='세션 키')
    
    # 만료 시간 (기본 24시간)
    expires_at = models.DateTimeField(verbose_name='만료 일시')
    
    # 상태
    is_used = models.BooleanField(default=False, verbose_name='사용 여부')
    
    class Meta:
        verbose_name = '임시 업로드'
        verbose_name_plural = '임시 업로드들'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
            # 추가 성능 최적화 인덱스
            models.Index(fields=['uploaded_by']),     # 사용자별 임시 업로드 조회용
            models.Index(fields=['session_key']),     # 세션별 임시 업로드 조회용
            models.Index(fields=['expires_at', 'is_used']), # 만료 파일 정리용
        ]
    
    def __str__(self):
        return f"임시: {self.original_name}"
    
    def is_expired(self):
        """만료되었는지 확인"""
        return timezone.now() > self.expires_at
    
    def mark_as_used(self):
        """사용됨으로 표시"""
        self.is_used = True
        self.save(update_fields=['is_used'])
    
    @classmethod
    def cleanup_expired(cls):
        """만료된 임시 파일들 정리"""
        expired_files = cls.objects.filter(expires_at__lt=timezone.now())
        
        # S3에서 파일 삭제
        from .utils import delete_file_from_s3
        for temp_file in expired_files:
            delete_file_from_s3(temp_file.file_path)
        
        # DB에서 삭제
        expired_files.delete()


class UploadSession(models.Model):
    """
    업로드 세션 모델
    여러 파일 업로드 시 세션을 통해 관리
    """
    
    session_id = models.CharField(max_length=100, unique=True, verbose_name='세션 ID')
    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        verbose_name='사용자'
    )
    session_key = models.CharField(max_length=40, blank=True, verbose_name='세션 키')
    
    # 업로드 정보
    total_files = models.PositiveIntegerField(default=0, verbose_name='전체 파일 수')
    uploaded_files = models.PositiveIntegerField(default=0, verbose_name='업로드된 파일 수')
    failed_files = models.PositiveIntegerField(default=0, verbose_name='실패한 파일 수')
    
    # 상태
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('uploading', '업로드중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 시간 정보
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성 일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 일시')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료 일시')
    
    class Meta:
        verbose_name = '업로드 세션'
        verbose_name_plural = '업로드 세션들'
        ordering = ['-created_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['session_id']),     # 세션 ID 조회용 (unique이지만 최적화)
            models.Index(fields=['user']),           # 사용자별 세션 조회용
            models.Index(fields=['session_key']),    # 세션키별 조회용
            models.Index(fields=['status']),         # 상태별 조회용
            models.Index(fields=['created_at']),     # 정렬용
            models.Index(fields=['updated_at']),     # 수정일 기반 조회용
            models.Index(fields=['completed_at']),   # 완료일 기반 조회용
        ]
    
    def __str__(self):
        return f"세션 {self.session_id} ({self.get_status_display()})"
    
    def mark_completed(self):
        """완료 상태로 변경"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def mark_failed(self):
        """실패 상태로 변경"""
        self.status = 'failed'
        self.save(update_fields=['status'])
    
    def get_progress_percentage(self):
        """업로드 진행률 반환"""
        if self.total_files == 0:
            return 0
        return int((self.uploaded_files / self.total_files) * 100) 