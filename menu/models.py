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
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name='가격')
    price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name='원화 가격')
    is_discounted = models.BooleanField(default=False, verbose_name='할인 적용')
    discounted_price = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name='할인가')
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
