from django.db import models
from django.core.validators import MinValueValidator
from stores.models import Store

class MenuCategory(models.Model):
    """메뉴 카테고리 모델"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='menu_categories')
    name = models.CharField(max_length=50, verbose_name='카테고리명')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '메뉴 카테고리'
        verbose_name_plural = '메뉴 카테고리'
        unique_together = ['store', 'name']  # 같은 스토어 내에서 카테고리명 중복 방지
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.store.store_name} - {self.name}"

class Menu(models.Model):
    """메뉴 모델"""
    PRICE_DISPLAY_CHOICES = [
        ('sats', '사토시 고정'),
        ('krw', '원화 비율 연동'),
    ]
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='menus')
    categories = models.ManyToManyField(MenuCategory, blank=True, related_name='menus', verbose_name='카테고리')
    
    # 기본 정보
    name = models.CharField(max_length=100, verbose_name='메뉴명')
    description = models.TextField(verbose_name='메뉴 설명')
    image = models.ImageField(upload_to='menu_images/%Y/%m/%d/', blank=True, null=True, verbose_name='메뉴 이미지')
    
    # 가격 정보
    price_display = models.CharField(max_length=10, choices=PRICE_DISPLAY_CHOICES, default='sats', verbose_name='가격 표시 방식')
    price = models.PositiveIntegerField(validators=[MinValueValidator(0)], verbose_name='가격')
    price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name='원화 가격')
    is_discounted = models.BooleanField(default=False, verbose_name='할인 적용')
    discounted_price = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name='할인가')
    discounted_price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name='원화 할인가')
    
    # 상태 정보
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    is_temporarily_out_of_stock = models.BooleanField(default=False, verbose_name='일시품절')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '메뉴'
        verbose_name_plural = '메뉴'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.store.store_name} - {self.name}"

    @property
    def public_price(self):
        """사용자용 가격 (항상 사토시) - 원화 연동 시 최신 환율 반영"""
        if self.price_display == 'krw' and self.price_krw is not None:
            # 원화 연동 메뉴: 최신 환율로 사토시 가격 계산
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                # 원화를 사토시로 변환
                btc_amount = self.price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return round(sats_amount)
        return self.price

    @property
    def public_discounted_price(self):
        """사용자용 할인가 (항상 사토시) - 원화 연동 시 최신 환율 반영"""
        if not self.is_discounted or not self.discounted_price:
            return None
        
        if self.price_display == 'krw' and self.discounted_price_krw is not None:
            # 원화 연동 메뉴: 최신 환율로 사토시 할인가 계산
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                # 원화를 사토시로 변환
                btc_amount = self.discounted_price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return round(sats_amount)
        return self.discounted_price

    @property
    def public_discount_rate(self):
        """공개 할인율"""
        if not self.is_discounted or not self.discounted_price:
            return 0
        
        original = self.public_price
        discounted = self.public_discounted_price
        
        if original and discounted:
            return round((original - discounted) / original * 100)
        return 0

    @property
    def krw_price_display(self):
        """원화 표시용 가격"""
        if self.price_display == 'krw' and self.price_krw is not None:
            return f"{self.price_krw:,}원"
        return None

    @property
    def krw_discounted_price_display(self):
        """원화 표시용 할인가"""
        if self.price_display == 'krw' and self.is_discounted and self.discounted_price_krw is not None:
            return f"{self.discounted_price_krw:,}원"
        return None

    def clean(self):
        """모델 유효성 검사"""
        from django.core.exceptions import ValidationError
        
        if self.is_discounted and self.discounted_price:
            if self.discounted_price >= self.price:
                raise ValidationError('할인가는 정가보다 낮아야 합니다.')


class MenuImage(models.Model):
    """메뉴 이미지 모델"""
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='images')
    
    # 이미지 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')  # S3 URL은 길 수 있음
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='파일 크기 (bytes)')
    
    # 이미지 크기 정보
    width = models.PositiveIntegerField(default=500, verbose_name='이미지 너비')
    height = models.PositiveIntegerField(default=500, verbose_name='이미지 높이')  # 1:1 비율
    
    # 순서 정보 (이미지 정렬용)
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name='업로드 사용자')
    
    class Meta:
        verbose_name = '메뉴 이미지'
        verbose_name_plural = '메뉴 이미지들'
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['menu', 'order']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.menu.name} - {self.original_name}"
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return "크기 정보 없음"
        
        size = self.file_size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MenuOption(models.Model):
    """메뉴 옵션 모델"""
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=50, verbose_name='옵션명')
    values = models.TextField(verbose_name='옵션값들 (JSON)')
    is_required = models.BooleanField(default=False, verbose_name='필수 선택')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        verbose_name = '메뉴 옵션'
        verbose_name_plural = '메뉴 옵션'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.menu.name} - {self.name}"

    @property
    def values_list(self):
        """옵션값 리스트 반환"""
        import json
        try:
            return json.loads(self.values) if self.values else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_values_list(self, values_list):
        """옵션값 리스트 설정"""
        import json
        self.values = json.dumps(values_list, ensure_ascii=False)

class MenuOrder(models.Model):
    """메뉴 주문 모델"""
    ORDER_STATUS_CHOICES = [
        ('pending', '주문 대기'),
        ('payment_pending', '결제 대기'),
        ('paid', '결제 완료'),
        ('cancelled', '주문 취소'),
        ('expired', '주문 만료'),
    ]
    
    # 주문 기본 정보
    order_number = models.CharField(max_length=50, unique=True, verbose_name='주문번호')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='menu_orders', verbose_name='스토어')
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, 
        default='pending', verbose_name='주문 상태'
    )
    
    # 결제 정보
    total_amount = models.PositiveIntegerField(verbose_name='총 금액', help_text='사토시 단위')
    payment_hash = models.CharField(max_length=100, blank=True, verbose_name='결제 해시')
    
    # 고객 정보 (비회원 가능)
    customer_info = models.JSONField(
        default=dict, blank=True,
        verbose_name='고객 정보',
        help_text='비회원 주문 시 고객 정보 저장'
    )
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='주문 시간')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='결제 시간')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시간')
    
    class Meta:
        verbose_name = '메뉴 주문'
        verbose_name_plural = '메뉴 주문들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['payment_hash']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.store.store_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """주문번호 생성"""
        import datetime
        import random
        now = datetime.datetime.now()
        return f"MENU{now.strftime('%Y%m%d')}{random.randint(100000, 999999)}"


class MenuOrderItem(models.Model):
    """메뉴 주문 아이템 모델"""
    order = models.ForeignKey(MenuOrder, on_delete=models.CASCADE, related_name='items', verbose_name='주문')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, verbose_name='메뉴')
    
    # 주문 당시의 메뉴 정보 (메뉴가 변경되어도 주문 내역은 유지)
    menu_name = models.CharField(max_length=100, verbose_name='메뉴명')
    menu_price = models.PositiveIntegerField(verbose_name='메뉴 가격')
    quantity = models.PositiveIntegerField(verbose_name='수량')
    
    # 선택된 옵션들 (JSON 필드로 저장)
    selected_options = models.JSONField(
        default=dict, blank=True,
        verbose_name='선택된 옵션들',
        help_text='옵션명: 선택값 형태로 저장'
    )
    options_price = models.PositiveIntegerField(default=0, verbose_name='옵션 가격')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    
    class Meta:
        verbose_name = '메뉴 주문 아이템'
        verbose_name_plural = '메뉴 주문 아이템들'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['menu']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.menu_name} x{self.quantity}"
    
    @property
    def unit_price(self):
        """개당 가격 (메뉴가격 + 옵션가격)"""
        return (self.menu_price or 0) + (self.options_price or 0)
    
    @property
    def total_price(self):
        """총 가격 (개당가격 * 수량)"""
        return self.unit_price * (self.quantity or 0)
