from django.db import models
from django.core.validators import MinValueValidator
from stores.models import Store
import uuid

class MenuCategory(models.Model):
    """메뉴 카테고리 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='menu_categories')
    name = models.CharField(max_length=50, verbose_name='카테고리명')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '메뉴 카테고리'
        verbose_name_plural = '메뉴 카테고리'
        unique_together = ['store', 'name']  # 같은 스토어 내에서 카테고리명 중복 방지
        ordering = ['name']

    def __str__(self):
        return f"{self.store.store_name} - {self.name}"

class Menu(models.Model):
    """메뉴 모델"""
    PRICE_DISPLAY_CHOICES = [
        ('sats', '사토시 고정'),
        ('krw', '원화 비율 연동'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='menus')
    categories = models.ManyToManyField(MenuCategory, blank=True, related_name='menus', verbose_name='카테고리')
    
    # 기본 정보
    name = models.CharField(max_length=100, verbose_name='메뉴명')
    description = models.TextField(verbose_name='메뉴 설명')
    image = models.ImageField(upload_to='menu_images/%Y/%m/%d/', blank=True, null=True, verbose_name='메뉴 이미지')
    
    # 가격 정보
    price_display = models.CharField(max_length=10, choices=PRICE_DISPLAY_CHOICES, default='sats', verbose_name='가격 표시 방식')
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name='가격')
    is_discounted = models.BooleanField(default=False, verbose_name='할인 적용')
    discounted_price = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name='할인가')
    
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
        """공개 가격 (사토시 단위)"""
        if self.price_display == 'krw':
            # 원화 연동의 경우 실시간 환율로 계산 (임시로 고정값 사용)
            # 실제로는 환율 API를 통해 동적으로 계산해야 함
            return self.price * 100  # 임시 환율
        return self.price

    @property
    def public_discounted_price(self):
        """공개 할인가 (사토시 단위)"""
        if not self.is_discounted or not self.discounted_price:
            return None
        
        if self.price_display == 'krw':
            # 원화 연동의 경우 실시간 환율로 계산
            return self.discounted_price * 100  # 임시 환율
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
        if self.price_display == 'krw':
            return f"{self.price:,}원"
        return None

    @property
    def krw_discounted_price_display(self):
        """원화 표시용 할인가"""
        if self.price_display == 'krw' and self.is_discounted and self.discounted_price:
            return f"{self.discounted_price:,}원"
        return None

    def clean(self):
        """모델 유효성 검사"""
        from django.core.exceptions import ValidationError
        
        if self.is_discounted and self.discounted_price:
            if self.discounted_price >= self.price:
                raise ValidationError('할인가는 정가보다 낮아야 합니다.')



class MenuOption(models.Model):
    """메뉴 옵션 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
