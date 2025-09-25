from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from storage.backends import S3Storage
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import timedelta
import hashlib
import logging
from stores.models import Store
from PIL import Image
import io

logger = logging.getLogger(__name__)


def validate_file_size(value):
    """파일 크기 제한 - 100MB"""
    file_size = value.size
    if file_size > 104857600:  # 100MB
        raise ValidationError('파일 크기는 100MB를 초과할 수 없습니다.')


def digital_file_upload_to(instance, filename):
    """디지털 파일 업로드 경로 생성"""
    from datetime import datetime
    import uuid
    import os
    
    # 파일 확장자 추출
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    # 고유한 파일명 생성
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{timestamp}_{unique_id}.{ext}" if ext else f"{timestamp}_{unique_id}"
    
    # 날짜별 디렉토리 구조
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    # 최종 경로: digital_files/2025/01/18/20250118_123456_abcdef12.png
    return f'digital_files/{date_path}/{new_filename}'


def preview_image_upload_to(instance, filename):
    """미리보기 이미지 업로드 경로 생성"""
    from datetime import datetime
    import uuid
    import os
    
    # 파일 확장자 추출
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    # 고유한 파일명 생성
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{timestamp}_{unique_id}.{ext}" if ext else f"{timestamp}_{unique_id}"
    
    # 날짜별 디렉토리 구조
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    # 최종 경로: digital_files/previews/2025/01/18/20250118_123456_abcdef12.jpg
    return f'digital_files/previews/{date_path}/{new_filename}'


class DigitalFile(models.Model):
    """디지털 파일"""
    PRICE_DISPLAY_CHOICES = [
        ('free', '무료'),
        ('sats', '사토시 가격'),
        ('krw', '원화연동 가격'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='digital_files')
    name = models.CharField(max_length=200, verbose_name="파일명")
    description = models.TextField(verbose_name="파일 설명", blank=True)
    
    # 파일 정보
    file = models.FileField(
        upload_to=digital_file_upload_to, 
        verbose_name="파일",
        validators=[validate_file_size],
        storage=S3Storage() if hasattr(settings, 'S3_ACCESS_KEY_ID') and settings.S3_ACCESS_KEY_ID else default_storage
    )
    original_filename = models.CharField(max_length=255, verbose_name="원본 파일명", blank=True)
    file_size = models.PositiveIntegerField(verbose_name="파일 크기(bytes)", null=True, blank=True)
    file_hash = models.CharField(max_length=64, verbose_name="파일 해시", blank=True, editable=False)
    
    # 미리보기 이미지 (선택사항)
    preview_image = models.ImageField(
        upload_to=preview_image_upload_to,
        verbose_name="미리보기 이미지",
        blank=True,
        null=True,
        storage=S3Storage() if hasattr(settings, 'S3_ACCESS_KEY_ID') and settings.S3_ACCESS_KEY_ID else default_storage
    )
    
    # 가격 정보
    price_display = models.CharField(
        max_length=10,
        choices=PRICE_DISPLAY_CHOICES,
        default='free',
        verbose_name='가격 표시 방식'
    )
    price = models.PositiveIntegerField(verbose_name="가격(satoshi)", default=0)
    price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name="원화 가격", help_text="원화 단위")
    
    # 할인 정보
    is_discounted = models.BooleanField(default=False, verbose_name="할인 적용")
    discounted_price = models.PositiveIntegerField(verbose_name="할인가(satoshi)", null=True, blank=True)
    discounted_price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name="원화 할인가", help_text="원화 단위")
    discount_end_date = models.DateField(verbose_name="할인 종료일", null=True, blank=True)
    discount_end_time = models.TimeField(verbose_name="할인 종료시간", null=True, blank=True)
    
    # 판매 설정
    max_downloads = models.PositiveIntegerField(
        verbose_name="최대 다운로드 횟수", 
        null=True, 
        blank=True,
        help_text="비워두면 무제한"
    )
    download_expiry_days = models.PositiveIntegerField(
        verbose_name="다운로드 유효기간(일)", 
        null=True, 
        blank=True,
        help_text="구매 후 다운로드 가능 기간, 비워두면 무제한"
    )
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    is_temporarily_closed = models.BooleanField(default=False, verbose_name="일시중단")
    
    # 안내 메시지
    purchase_message = models.TextField(verbose_name="구매완료 안내메시지", blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "디지털 파일"
        verbose_name_plural = "디지털 파일"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['deleted_at']),
            models.Index(fields=['store', 'deleted_at']),
            models.Index(fields=['price_display']),
            models.Index(fields=['is_discounted']),
            models.Index(fields=['is_temporarily_closed']),
            models.Index(fields=['store', 'is_discounted']),
        ]
    
    def __str__(self):
        return f"[{self.store.store_name}] {self.name}"
    
    def save(self, *args, **kwargs):
        # 기존 인스턴스 가져오기
        if self.pk:
            old_instance = DigitalFile.objects.filter(pk=self.pk).first()
            
            # 기존 파일이 있고 새 파일로 교체하는 경우
            if old_instance and old_instance.file and self.file and old_instance.file != self.file:
                # 기존 파일 삭제
                try:
                    if old_instance.file.storage.exists(old_instance.file.name):
                        old_instance.file.storage.delete(old_instance.file.name)
                        logger.info(f"Deleted old file from storage: {old_instance.file.name}")
                except Exception as e:
                    logger.error(f"Error deleting old file: {e}")
            
            # 기존 썸네일이 있고 새 썸네일로 교체하는 경우
            if old_instance and old_instance.preview_image and self.preview_image and old_instance.preview_image != self.preview_image:
                # 기존 썸네일 삭제
                try:
                    if old_instance.preview_image.storage.exists(old_instance.preview_image.name):
                        old_instance.preview_image.storage.delete(old_instance.preview_image.name)
                        logger.info(f"Deleted old preview image from storage: {old_instance.preview_image.name}")
                except Exception as e:
                    logger.error(f"Error deleting old preview image: {e}")
        
        # 미리보기 이미지가 있고 처리되지 않은 경우 16:9 비율로 리사이징
        if self.preview_image and hasattr(self.preview_image, 'file'):
            try:
                # 이미지 열기
                img = Image.open(self.preview_image.file)
                
                # RGBA인 경우 RGB로 변환
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 16:9 비율로 리사이징 (가로 1000px 기준)
                target_width = 1000
                target_height = int(target_width * 9 / 16)  # 562px
                
                # 현재 이미지의 비율 계산
                current_ratio = img.width / img.height
                target_ratio = 16 / 9
                
                if current_ratio > target_ratio:
                    # 이미지가 더 넓은 경우 - 좌우를 잘라냄
                    new_height = img.height
                    new_width = int(new_height * target_ratio)
                    left = (img.width - new_width) // 2
                    right = left + new_width
                    img = img.crop((left, 0, right, img.height))
                else:
                    # 이미지가 더 높은 경우 - 상하를 잘라냄
                    new_width = img.width
                    new_height = int(new_width / target_ratio)
                    top = (img.height - new_height) // 2
                    bottom = top + new_height
                    img = img.crop((0, top, img.width, bottom))
                
                # 최종 크기로 리사이징
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # 메모리에 저장
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)
                
                # 파일명 생성
                file_name = self.preview_image.name.split('/')[-1]
                if not file_name.lower().endswith('.jpg'):
                    file_name = file_name.rsplit('.', 1)[0] + '.jpg'
                
                # ContentFile로 변환하여 저장
                self.preview_image.save(file_name, ContentFile(output.read()), save=False)
                
                logger.info(f"Resized preview image to 16:9 ratio (1000x562)")
            except Exception as e:
                logger.error(f"Error resizing preview image: {e}")
        
        if self.file:
            # 원본 파일명 저장
            if not self.original_filename:
                self.original_filename = self.file.name.split('/')[-1]
            
            # 파일 크기 저장
            if not self.file_size:
                self.file_size = self.file.size
            
            # 파일 해시 생성 (중복 파일 체크용)
            if not self.file_hash:
                hasher = hashlib.sha256()
                for chunk in self.file.chunks():
                    hasher.update(chunk)
                self.file_hash = hasher.hexdigest()
        
        super().save(*args, **kwargs)
    
    @property
    def is_discount_active(self):
        """할인이 현재 활성화되어 있는지 확인"""
        if not self.is_discounted:
            return False
        
        if not self.discount_end_date:
            return True
        
        now = timezone.now()
        if self.discount_end_time:
            end_datetime = timezone.datetime.combine(
                self.discount_end_date, 
                self.discount_end_time,
                tzinfo=now.tzinfo
            )
        else:
            end_datetime = timezone.datetime.combine(
                self.discount_end_date,
                timezone.datetime.max.time(),
                tzinfo=now.tzinfo
            )
        
        return now <= end_datetime
    
    @property
    def current_price(self):
        """현재 적용 가격 (할인 적용)"""
        if self.price_display == 'free':
            return 0
        
        if self.is_discount_active:
            if self.price_display == 'krw':
                return self.discounted_price_krw or self.price_krw
            return self.discounted_price or self.price
        
        if self.price_display == 'krw':
            return self.price_krw
        return self.price
    
    @property
    def current_price_sats(self):
        """현재 가격 (사토시 단위로 변환)"""
        if self.price_display == 'free':
            return 0
        
        current = self.current_price
        
        if self.price_display == 'krw' and current is not None:
            from myshop.models import ExchangeRate
            try:
                latest_rate = ExchangeRate.objects.latest('created_at')
                if latest_rate and latest_rate.btc_krw_rate > 0:
                    btc_amount = current / float(latest_rate.btc_krw_rate)
                    sats_amount = btc_amount * 100_000_000
                    return round(sats_amount)
            except ExchangeRate.DoesNotExist:
                pass
        
        return current
    
    @property
    def price_sats(self):
        """정상 가격 (사토시 단위로 변환)"""
        if self.price_display == 'free':
            return 0
        
        if self.price_display == 'krw' and self.price_krw is not None:
            from myshop.models import ExchangeRate
            try:
                latest_rate = ExchangeRate.objects.latest('created_at')
                if latest_rate and latest_rate.btc_krw_rate > 0:
                    btc_amount = self.price_krw / float(latest_rate.btc_krw_rate)
                    sats_amount = btc_amount * 100_000_000
                    return round(sats_amount)
            except ExchangeRate.DoesNotExist:
                pass
        
        return self.price
    
    @property
    def current_price_krw(self):
        """현재 원화 가격 (원화연동인 경우)"""
        if self.price_display != 'krw':
            return None
        
        if self.is_discount_active:
            return self.discounted_price_krw or self.price_krw
        return self.price_krw
    
    @property
    def price_unit(self):
        """가격 단위 반환"""
        if self.price_display == 'free':
            return ''
        elif self.price_display == 'krw':
            return '원'
        return 'sats'
    
    @property
    def available_downloads(self):
        """판매 가능한 다운로드 수"""
        if not self.max_downloads:
            return None  # 무제한
        
        sold_count = self.orders.filter(status='confirmed').count()
        return max(0, self.max_downloads - sold_count)
    
    @property
    def is_sold_out(self):
        """매진 여부"""
        if not self.max_downloads:
            return False
        return self.available_downloads <= 0
    
    @property
    def download_count(self):
        """총 다운로드 횟수"""
        return FileDownloadLog.objects.filter(
            order__digital_file=self
        ).count()
    
    @property
    def sales_count(self):
        """판매 횟수"""
        return self.orders.filter(status='confirmed').count()
    
    @property
    def get_price_sats(self):
        """정가를 사토시로 반환"""
        if self.price_display == 'free':
            return 0
        
        if self.price_display == 'krw' and self.price_krw is not None:
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                btc_amount = self.price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return round(sats_amount)
        
        return self.price
    
    @property
    def discount_percentage(self):
        """할인율 계산"""
        if not self.is_discount_active:
            return 0
        
        if self.price_display == 'krw':
            if self.price_krw and self.discounted_price_krw:
                return round((self.price_krw - self.discounted_price_krw) / self.price_krw * 100)
        else:
            if self.price and self.discounted_price:
                return round((self.price - self.discounted_price) / self.price * 100)
        
        return 0
    
    @property
    def discount_amount(self):
        """할인 금액 (사토시 단위)"""
        if not self.is_discount_active:
            return 0
        
        original_sats = self.get_price_sats
        current_sats = self.current_price_sats
        
        return original_sats - current_sats
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return "알 수 없음"
        
        size = self.file_size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_file_extension(self):
        """파일 확장자 반환"""
        if self.original_filename:
            ext = self.original_filename.rsplit('.', 1)[-1].upper()
            return ext
        return "알 수 없음"
    
    def get_file_type_display(self):
        """파일 유형을 사용자 친화적으로 표시"""
        if not self.original_filename:
            return "알 수 없음"
        
        ext = self.original_filename.rsplit('.', 1)[-1].lower()
        
        # 파일 유형 매핑
        file_types = {
            # 문서
            'pdf': 'PDF 문서',
            'doc': 'Word 문서',
            'docx': 'Word 문서',
            'xls': 'Excel 문서',
            'xlsx': 'Excel 문서',
            'ppt': 'PowerPoint 문서',
            'pptx': 'PowerPoint 문서',
            'txt': '텍스트 파일',
            'rtf': 'RTF 문서',
            'odt': 'OpenDocument 문서',
            
            # 이미지
            'jpg': 'JPG 이미지',
            'jpeg': 'JPEG 이미지',
            'png': 'PNG 이미지',
            'gif': 'GIF 이미지',
            'bmp': 'BMP 이미지',
            'svg': 'SVG 이미지',
            'webp': 'WebP 이미지',
            'ico': '아이콘 파일',
            'tiff': 'TIFF 이미지',
            'psd': 'Photoshop 파일',
            'ai': 'Illustrator 파일',
            
            # 동영상
            'mp4': 'MP4 동영상',
            'avi': 'AVI 동영상',
            'mov': 'MOV 동영상',
            'wmv': 'WMV 동영상',
            'flv': 'FLV 동영상',
            'mkv': 'MKV 동영상',
            'webm': 'WebM 동영상',
            
            # 오디오
            'mp3': 'MP3 오디오',
            'wav': 'WAV 오디오',
            'flac': 'FLAC 오디오',
            'aac': 'AAC 오디오',
            'ogg': 'OGG 오디오',
            'wma': 'WMA 오디오',
            'm4a': 'M4A 오디오',
            
            # 압축
            'zip': 'ZIP 압축파일',
            'rar': 'RAR 압축파일',
            '7z': '7Z 압축파일',
            'tar': 'TAR 압축파일',
            'gz': 'GZ 압축파일',
            'bz2': 'BZ2 압축파일',
            
            # 코드/개발
            'py': 'Python 파일',
            'js': 'JavaScript 파일',
            'html': 'HTML 파일',
            'css': 'CSS 파일',
            'json': 'JSON 파일',
            'xml': 'XML 파일',
            'java': 'Java 파일',
            'cpp': 'C++ 파일',
            'c': 'C 파일',
            'php': 'PHP 파일',
            'rb': 'Ruby 파일',
            'go': 'Go 파일',
            'swift': 'Swift 파일',
            'kt': 'Kotlin 파일',
            
            # 기타
            'epub': 'EPUB 전자책',
            'mobi': 'MOBI 전자책',
            'apk': 'Android 앱',
            'exe': 'Windows 실행파일',
            'dmg': 'macOS 설치파일',
            'iso': 'ISO 이미지',
        }
        
        return file_types.get(ext, f'{ext.upper()} 파일')
    
    @property
    def preview_image_url(self):
        """미리보기 이미지 URL을 안전하게 반환"""
        if not self.preview_image:
            return None
        try:
            return self.preview_image.url
        except Exception as e:
            logger.warning(f"Preview image URL error for file {self.id}: {e}")
            return None
    
    @property
    def krw_price_display(self):
        """원화 가격 표시 문자열"""
        if self.price_display == 'krw' and self.price_krw:
            return f"{self.price_krw:,.0f}원"
        return ""
    
    @property
    def krw_discounted_price_display(self):
        """원화 할인 가격 표시 문자열"""
        if self.price_display == 'krw' and self.is_discount_active and self.discounted_price_krw:
            return f"{self.discounted_price_krw:,.0f}원"
        return ""
    
    def delete(self, *args, **kwargs):
        """파일 삭제 시 오브젝트 스토리지에서도 삭제"""
        # 파일 삭제
        if self.file and self.file.name:
            try:
                # exists 체크 없이 바로 삭제 시도 (exists가 에러를 발생시킬 수 있음)
                self.file.storage.delete(self.file.name)
                logger.info(f"Deleted file from storage: {self.file.name}")
            except Exception as e:
                logger.error(f"Error deleting file {self.file.name}: {e}", exc_info=True)
                # 에러가 발생해도 계속 진행
        
        # 미리보기 이미지 삭제
        if self.preview_image and self.preview_image.name:
            try:
                # exists 체크 없이 바로 삭제 시도
                self.preview_image.storage.delete(self.preview_image.name)
                logger.info(f"Deleted preview image from storage: {self.preview_image.name}")
            except Exception as e:
                logger.error(f"Error deleting preview image {self.preview_image.name}: {e}", exc_info=True)
                # 에러가 발생해도 계속 진행
        
        super().delete(*args, **kwargs)


class FileOrder(models.Model):
    """파일 구매 주문"""
    STATUS_CHOICES = [
        ('pending', '결제 대기'),
        ('confirmed', '구매 확정'),
        ('cancelled', '구매 취소'),
    ]
    
    # 기본 정보
    digital_file = models.ForeignKey(DigitalFile, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_orders')
    
    # 주문 정보
    order_number = models.CharField(max_length=100, unique=True, verbose_name="주문번호")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태")
    
    # 임시 예약 정보
    is_temporary_reserved = models.BooleanField(default=True, verbose_name="임시 예약 상태")
    reservation_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="예약 만료 시간")
    auto_cancelled_reason = models.CharField(max_length=100, blank=True, verbose_name="자동 취소 사유")
    
    # 가격 정보
    price = models.PositiveIntegerField(verbose_name="구매가(satoshi)")
    
    # 할인 정보
    is_discounted = models.BooleanField(default=False, verbose_name="할인 적용")
    discount_rate = models.PositiveIntegerField(default=0, verbose_name="할인율(%)")
    original_price = models.PositiveIntegerField(null=True, blank=True, verbose_name="원래 가격(satoshi)")
    
    # 결제 정보
    payment_hash = models.CharField(max_length=255, blank=True, verbose_name="결제 해시")
    payment_request = models.TextField(blank=True, verbose_name="결제 요청(인보이스)")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="결제 완료 시간")
    
    # 구매 확정 정보
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="구매 확정 시간")
    confirmation_message_sent = models.BooleanField(default=False, verbose_name="확정 안내 발송 여부")
    
    # 다운로드 만료일
    download_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="다운로드 만료일")
    
    # 다운로드 클릭 추적
    download_clicked = models.BooleanField(default=False, verbose_name="다운로드 버튼 클릭 여부")
    download_clicked_at = models.DateTimeField(null=True, blank=True, verbose_name="다운로드 버튼 첫 클릭 시간")
    download_click_count = models.PositiveIntegerField(default=0, verbose_name="다운로드 클릭 횟수")
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "파일 주문"
        verbose_name_plural = "파일 주문"
        ordering = ['-created_at']
        # 동일한 사용자가 동일한 파일에 중복 구매 방지
        constraints = [
            models.UniqueConstraint(
                fields=['digital_file', 'user'],
                condition=models.Q(status='confirmed'),
                name='unique_confirmed_file_order_per_user'
            )
        ]
        indexes = [
            models.Index(fields=['digital_file']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', '-confirmed_at'], name='file_fileor_status_fc4bb0_idx'),
            models.Index(fields=['digital_file', 'user']),
            models.Index(fields=['digital_file', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['is_discounted']),
            models.Index(fields=['download_clicked']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # 주문번호 생성
        if not self.order_number:
            import uuid
            store_id = self.digital_file.store.store_id
            date_str = timezone.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:8].upper()
            self.order_number = f"{store_id}-FILE-{date_str}-{unique_id}"
        
        # 임시 예약 만료 시간 설정 (15분)
        if self.is_temporary_reserved and not self.reservation_expires_at:
            self.reservation_expires_at = timezone.now() + timedelta(minutes=15)
        
        # 다운로드 만료일 설정
        if self.status == 'confirmed' and not self.download_expires_at:
            if self.digital_file.download_expiry_days:
                self.download_expires_at = timezone.now() + timedelta(days=self.digital_file.download_expiry_days)
        
        super().save(*args, **kwargs)
    
    @property
    def is_download_expired(self):
        """다운로드 기간 만료 여부"""
        if not self.download_expires_at:
            return False
        return timezone.now() > self.download_expires_at
    
    @property
    def can_download(self):
        """다운로드 가능 여부"""
        return (
            self.status == 'confirmed' and 
            not self.is_download_expired and
            self.digital_file.is_active
        )
    
    @property
    def remaining_downloads(self):
        """남은 다운로드 횟수"""
        # 파일의 최대 다운로드 횟수가 설정되어 있지 않으면 무제한
        if not self.digital_file.max_downloads:
            return None
        
        # 현재 사용자의 다운로드 횟수
        download_count = FileDownloadLog.objects.filter(order=self).count()
        
        # 보통 구매당 1회 다운로드로 제한
        return max(0, 1 - download_count)


class FileDownloadLog(models.Model):
    """파일 다운로드 로그"""
    order = models.ForeignKey(FileOrder, on_delete=models.CASCADE, related_name='download_logs')
    ip_address = models.GenericIPAddressField(verbose_name="IP 주소")
    user_agent = models.TextField(verbose_name="User Agent", blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True, verbose_name="다운로드 시간")
    
    class Meta:
        verbose_name = "다운로드 로그"
        verbose_name_plural = "다운로드 로그"
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['downloaded_at']),
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.downloaded_at}"
