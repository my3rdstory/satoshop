from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache
import requests
from decimal import Decimal


class Product(models.Model):
    """상품 모델"""
    PRICE_DISPLAY_CHOICES = [
        ('sats', '사토시'),
        ('krw', '원화'),
    ]
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')
    
    # 기본 정보
    title = models.CharField(max_length=200, verbose_name='제목')
    description = models.TextField(verbose_name='설명', help_text='마크다운 형식')
    price = models.PositiveIntegerField(verbose_name='가격', help_text='사토시 단위')
    price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name='원화 가격', help_text='원화 단위')
    price_display = models.CharField(
        max_length=4,
        choices=PRICE_DISPLAY_CHOICES,
        default='sats',
        verbose_name='가격 표시 방식'
    )
    
    # 할인 정보
    is_discounted = models.BooleanField(default=False, verbose_name='할인 여부')
    discounted_price = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='할인가격', help_text='사토시 단위'
    )
    discounted_price_krw = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='원화 할인가격', help_text='원화 단위'
    )
    
    # 배송비
    shipping_fee = models.PositiveIntegerField(default=0, verbose_name='배송비', help_text='가격표시방식에 따라 원 또는 사토시 단위')
    shipping_fee_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name='원화 배송비', help_text='원화 단위')
    
    # 결제완료 안내 메시지
    completion_message = models.TextField(
        blank=True, verbose_name='결제완료 안내메시지', 
        help_text='결제 완료 후 보여줄 메시지'
    )
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name='판매 중')
    # 재고 관리
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='재고 수량')
    is_temporarily_out_of_stock = models.BooleanField(default=False, verbose_name='일시품절')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '상품'
        verbose_name_plural = '상품들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['store']),          # 스토어별 상품 조회용
            models.Index(fields=['is_active']),      # 관리자 필터링용
            models.Index(fields=['is_discounted']),  # 관리자 필터링용
            models.Index(fields=['price_display']),  # 관리자 필터링용
            models.Index(fields=['updated_at']),     # 관리자 정렬용
            models.Index(fields=['store', 'is_active', 'created_at']),  # 스토어 상품 목록용
            models.Index(fields=['is_active', 'created_at']),           # 전체 활성 상품 목록용
            models.Index(fields=['store', 'created_at']),               # 관리자용 스토어별 상품
        ]
    
    def __str__(self):
        return f"{self.store.store_name} - {self.title}"
    
    @property
    def final_price(self):
        """최종 가격 (할인가가 있으면 할인가, 없으면 정가)"""
        if self.is_discounted and self.discounted_price:
            return self.discounted_price
        return self.price
    
    @property
    def discount_rate(self):
        """할인율 계산 (소수점 첫째자리까지) - 표시 가격 기준"""
        if not self.is_discounted or not self.display_discounted_price:
            return 0
        original_price = self.display_price
        discounted_price = self.display_discounted_price
        if original_price <= 0:
            return 0
        return round((original_price - discounted_price) / original_price * 100, 1)
    
    def format_price(self, price):
        """가격을 천 단위 콤마로 포맷팅"""
        return f"{price:,}"
    
    @classmethod
    def get_btc_krw_rate(cls):
        """업비트 BTC/KRW 환율 조회 (캐시 60초)"""
        cache_key = 'btc_krw_rate'
        rate = cache.get(cache_key)
        
        if rate is None:
            try:
                response = requests.get('https://api.upbit.com/v1/ticker?markets=KRW-BTC')
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        rate = Decimal(str(data[0]['trade_price']))
                        cache.set(cache_key, rate, 60)  # 60초 캐시
            except Exception as e:
                print(f"환율 조회 실패: {e}")
                rate = Decimal('0')
        
        return rate
    
    @property
    def display_price(self):
        """표시 가격 - 가격 표시 방식에 따라 원화 또는 사토시 반환"""
        if self.price_display == 'krw' and self.price_krw is not None:
            return self.price_krw
        return self.price

    @property
    def display_discounted_price(self):
        """표시 할인 가격 - 가격 표시 방식에 따라 원화 또는 사토시 반환"""
        if not self.is_discounted:
            return None
        if self.price_display == 'krw' and self.discounted_price_krw is not None:
            return self.discounted_price_krw
        return self.discounted_price

    @property
    def display_shipping_fee(self):
        """표시 배송비 - 가격 표시 방식에 따라 원화 또는 사토시 반환"""
        if self.price_display == 'krw' and self.shipping_fee_krw is not None:
            return self.shipping_fee_krw
        return self.shipping_fee

    @property
    def price_unit(self):
        """가격 단위 반환"""
        return '원' if self.price_display == 'krw' else 'sats'

    @property
    def public_price(self):
        """사용자용 가격 (항상 사토시) - 원화 연동 시 최신 환율 반영"""
        if self.price_display == 'krw' and self.price_krw is not None:
            # 원화 연동 상품: 최신 환율로 사토시 가격 계산
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                # 원화를 사토시로 변환
                btc_amount = self.price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return int(sats_amount)
        return self.price

    @property
    def public_discounted_price(self):
        """사용자용 할인가 (항상 사토시) - 원화 연동 시 최신 환율 반영"""
        if not self.is_discounted:
            return None
        
        if self.price_display == 'krw' and self.discounted_price_krw is not None:
            # 원화 연동 상품: 최신 환율로 사토시 할인가 계산
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                # 원화를 사토시로 변환
                btc_amount = self.discounted_price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return int(sats_amount)
        return self.discounted_price

    @property
    def public_shipping_fee(self):
        """사용자용 배송비 (항상 사토시) - 원화 연동 시 최신 환율 반영"""
        if self.price_display == 'krw' and self.shipping_fee_krw is not None:
            # 원화 연동 상품: 최신 환율로 사토시 배송비 계산
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                # 원화를 사토시로 변환
                if self.shipping_fee_krw == 0:
                    return 0
                btc_amount = self.shipping_fee_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return int(sats_amount)
        return self.shipping_fee

    @property
    def public_discount_rate(self):
        """사용자용 할인율 (사토시 기준) - 원화 연동 시 최신 환율 반영"""
        if not self.is_discounted or not self.public_discounted_price:
            return 0
        
        public_price = self.public_price
        public_discounted_price = self.public_discounted_price
        
        if public_price <= 0:
            return 0
        return round((public_price - public_discounted_price) / public_price * 100, 1)

    @property
    def krw_price_display(self):
        """원화 가격 표시 (원화 연동 상품용)"""
        if self.price_display == 'krw' and self.price_krw is not None:
            return f"{self.price_krw:,}원"
        return None

    @property
    def krw_discounted_price_display(self):
        """원화 할인가 표시 (원화 연동 상품용)"""
        if self.price_display == 'krw' and self.is_discounted and self.discounted_price_krw is not None:
            return f"{self.discounted_price_krw:,}원"
        return None

    @property
    def current_exchange_rate(self):
        """현재 환율 정보"""
        from myshop.models import ExchangeRate
        return ExchangeRate.get_latest_rate()

    @property
    def shipping_fee_display(self):
        """배송비 표시 텍스트 (0원일 때 '배송비 무료')"""
        if self.shipping_fee == 0:
            return '배송비 무료'
        
        if self.price_display == 'krw':
            return f"{self.shipping_fee:,}원"
        else:
            return f"{self.shipping_fee:,} sats"

    @property
    def shipping_fee_display_simple(self):
        """간단한 배송비 표시 (단위만)"""
        if self.shipping_fee == 0:
            return '무료'
        
        if self.price_display == 'krw':
            return f"{self.shipping_fee:,}원"
        else:
            return f"{self.shipping_fee:,} sats"

    @property
    def is_in_stock(self):
        """재고가 있는지 확인 (일시품절 고려)"""
        if self.is_temporarily_out_of_stock:
            return False
        return self.stock_quantity > 0

    @property
    def stock_status(self):
        """재고 상태 텍스트 (일시품절 고려)"""
        if self.is_temporarily_out_of_stock:
            return '일시 품절'
        elif self.stock_quantity == 0:
            return '품절'
        elif self.stock_quantity <= 5:
            return f'재고 {self.stock_quantity}개'
        else:
            return '재고 있음'

    def decrease_stock(self, quantity):
        """재고 감소"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save()
            return True
        return False

    def increase_stock(self, quantity):
        """재고 증가"""
        self.stock_quantity += quantity
        self.save()

    def can_purchase(self, quantity):
        """구매 가능 여부 확인 (일시품절 고려)"""
        if self.is_temporarily_out_of_stock:
            return False
        return self.is_active and self.stock_quantity >= quantity


class ProductImage(models.Model):
    """상품 이미지 모델"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    
    # 이미지 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='파일 크기 (bytes)')
    
    # 이미지 크기 정보 (1:1 비율)
    width = models.PositiveIntegerField(default=500, verbose_name='이미지 너비')
    height = models.PositiveIntegerField(default=500, verbose_name='이미지 높이')
    
    # 순서 정보
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = '상품 이미지'
        verbose_name_plural = '상품 이미지들'
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['product', 'order']),
        ]
    
    def __str__(self):
        return f"{self.product.title} - {self.original_name}"
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return '0 B'
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class ProductOption(models.Model):
    """상품 옵션 모델"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options')
    
    # 옵션 정보
    name = models.CharField(max_length=100, verbose_name='옵션명')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '상품 옵션'
        verbose_name_plural = '상품 옵션들'
        ordering = ['order', 'created_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['product']),        # 상품별 옵션 조회용
            models.Index(fields=['order']),          # 정렬용
            models.Index(fields=['created_at']),     # 관리자 필터링용
            models.Index(fields=['product', 'order']), # 상품 옵션 정렬 조회용
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'name'],
                name='unique_option_per_product'
            )
        ]
    
    def __str__(self):
        return f"{self.product.title} - {self.name}"


class ProductOptionChoice(models.Model):
    """상품 옵션 선택지 모델"""
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE, related_name='choices')
    
    # 선택지 정보
    name = models.CharField(max_length=100, verbose_name='옵션 종류명')
    price = models.IntegerField(default=0, verbose_name='추가 가격', help_text='사토시 단위')
    price_krw = models.IntegerField(null=True, blank=True, verbose_name='원화 추가 가격', help_text='원화 단위')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '상품 옵션 선택지'
        verbose_name_plural = '상품 옵션 선택지들'
        ordering = ['order', 'created_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['option']),         # 옵션별 선택지 조회용
            models.Index(fields=['order']),          # 정렬용
            models.Index(fields=['created_at']),     # 관리자 필터링용
            models.Index(fields=['option', 'order']), # 옵션 선택지 정렬 조회용
            models.Index(fields=['price']),          # 가격 기반 조회용
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['option', 'name'],
                name='unique_choice_per_option'
            )
        ]
    
    def __str__(self):
        return f"{self.option.name} - {self.name}"
    
    @property
    def display_price(self):
        """표시 가격 - 상품의 가격 표시 방식에 따라 원화 또는 사토시 반환"""
        if self.option.product.price_display == 'krw' and self.price_krw is not None:
            return self.price_krw
        return self.price

    @property
    def public_price(self):
        """사용자용 추가 가격 (항상 사토시) - 원화 연동 시 최신 환율 반영"""
        if self.option.product.price_display == 'krw' and self.price_krw is not None:
            # 원화 연동 상품: 최신 환율로 사토시 가격 계산
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                # 원화를 사토시로 변환
                if self.price_krw == 0:
                    return 0
                btc_amount = self.price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return int(sats_amount)
        return self.price

    @property
    def krw_price_display(self):
        """원화 추가 가격 표시 (원화 연동 상품용)"""
        if self.option.product.price_display == 'krw' and self.price_krw is not None:
            if self.price_krw == 0:
                return ""
            return f"+{self.price_krw:,}원"
        return None
