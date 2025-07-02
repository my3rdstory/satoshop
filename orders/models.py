from django.db import models
from django.contrib.auth.models import User


class Cart(models.Model):
    """장바구니 모델"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '장바구니'
        verbose_name_plural = '장바구니들'
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['user']),         # OneToOne 필드 최적화
            models.Index(fields=['created_at']),   # 관리자 필터링용
            models.Index(fields=['updated_at']),   # 관리자 필터링 및 정렬용
        ]
    
    def __str__(self):
        return f"{self.user.username}의 장바구니"
    
    @property
    def total_amount(self):
        """장바구니 총 금액"""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_items(self):
        """장바구니 총 상품 수"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """장바구니 아이템 모델"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name='수량')
    
    # 선택된 옵션들 (JSON 필드로 저장)
    selected_options = models.JSONField(
        default=dict, blank=True,
        verbose_name='선택된 옵션들',
        help_text='옵션ID: 선택지ID 형태로 저장'
    )
    
    # 환율 고정을 위한 필드들 (원화 연동 상품용)
    frozen_exchange_rate = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name='고정 환율',
        help_text='장바구니 추가 시점의 BTC/KRW 환율'
    )
    frozen_product_price_sats = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='고정 상품 가격(사토시)',
        help_text='장바구니 추가 시점의 사토시 가격'
    )
    frozen_options_price_sats = models.PositiveIntegerField(
        default=0,
        verbose_name='고정 옵션 가격(사토시)',
        help_text='장바구니 추가 시점의 옵션 사토시 가격'
    )
    
    # 메타 정보
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '장바구니 아이템'
        verbose_name_plural = '장바구니 아이템들'
        ordering = ['-added_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['cart']),         # 장바구니별 아이템 조회용
            models.Index(fields=['product']),      # 상품별 장바구니 조회용
            models.Index(fields=['added_at']),     # 정렬용
            models.Index(fields=['updated_at']),   # 관리자 정렬용
            models.Index(fields=['cart', 'added_at']), # 장바구니 아이템 목록용
            models.Index(fields=['cart', 'product']),  # 중복 체크용
        ]
    
    def __str__(self):
        return f"{self.cart.user.username} - {self.product.title} x{self.quantity}"
    
    @property
    def options_price(self):
        """선택된 옵션들의 총 가격 (환율 적용)"""
        total = 0
        for option_id, choice_id in self.selected_options.items():
            try:
                from products.models import ProductOptionChoice
                choice = ProductOptionChoice.objects.get(id=choice_id)
                total += choice.public_price
            except ProductOptionChoice.DoesNotExist:
                continue
        return total
    
    @property
    def unit_price(self):
        """개당 가격 (상품가격 + 옵션가격)"""
        # 고정된 가격이 있으면 사용 (환율 고정)
        if self.frozen_product_price_sats is not None:
            return self.frozen_product_price_sats + self.frozen_options_price_sats
        
        # 고정된 가격이 없으면 실시간 가격 사용 (할인 적용)
        # 할인 상품인 경우 할인가를 사용, 그렇지 않으면 정가 사용
        if self.product.is_discounted and self.product.public_discounted_price:
            base_price = self.product.public_discounted_price
        else:
            base_price = self.product.public_price
        
        # 옵션 가격도 환율 적용
        options_total = 0
        for option_id, choice_id in self.selected_options.items():
            try:
                from products.models import ProductOptionChoice
                choice = ProductOptionChoice.objects.get(id=choice_id)
                options_total += choice.public_price
            except ProductOptionChoice.DoesNotExist:
                continue
        
        return base_price + options_total
    
    @property
    def total_price(self):
        """총 가격 (개당가격 * 수량)"""
        quantity = self.quantity or 0
        return self.unit_price * quantity
    
    @property
    def options_display(self):
        """선택된 옵션들의 표시용 정보"""
        options_info = []
        for option_id, choice_id in self.selected_options.items():
            try:
                from products.models import ProductOption, ProductOptionChoice
                option = ProductOption.objects.get(id=option_id)
                choice = ProductOptionChoice.objects.get(id=choice_id)
                options_info.append({
                    'option_name': option.name,
                    'choice_name': choice.name,
                    'choice_price': choice.public_price
                })
            except (ProductOption.DoesNotExist, ProductOptionChoice.DoesNotExist):
                continue
        return options_info


class Order(models.Model):
    """주문 모델"""
    ORDER_STATUS_CHOICES = [
        ('pending', '주문 대기'),
        ('payment_pending', '결제 대기'),
        ('paid', '결제 완료'),
        ('shipped', '배송 중'),
        ('delivered', '배송 완료'),
        ('cancelled', '주문 취소'),
        ('refunded', '환불 완료'),
    ]
    
    # 주문 기본 정보
    order_number = models.CharField(max_length=50, unique=True, verbose_name='주문번호')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, 
        default='pending', verbose_name='주문 상태'
    )
    
    # 주문자 정보
    buyer_name = models.CharField(max_length=50, verbose_name='주문자 이름')
    buyer_phone = models.CharField(max_length=20, verbose_name='주문자 연락처')
    buyer_email = models.EmailField(verbose_name='주문자 이메일')
    
    # 배송 정보
    shipping_postal_code = models.CharField(max_length=10, verbose_name='우편번호')
    shipping_address = models.CharField(max_length=200, verbose_name='주소')
    shipping_detail_address = models.CharField(max_length=100, verbose_name='상세주소')
    order_memo = models.TextField(blank=True, verbose_name='주문 메모')
    
    # 가격 정보
    subtotal = models.PositiveIntegerField(verbose_name='상품 금액', help_text='사토시 단위')
    shipping_fee = models.PositiveIntegerField(verbose_name='배송비', help_text='원 단위')
    total_amount = models.PositiveIntegerField(verbose_name='총 금액', help_text='사토시 단위')
    
    # 결제 정보
    payment_id = models.CharField(max_length=100, blank=True, verbose_name='결제 ID')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='결제 시간')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 개인정보 자동 삭제를 위한 필드
    personal_info_deleted_at = models.DateTimeField(
        null=True, blank=True, 
        verbose_name='개인정보 삭제 시간',
        help_text='3개월 후 자동 삭제'
    )
    
    class Meta:
        verbose_name = '주문'
        verbose_name_plural = '주문들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['store', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.buyer_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """주문번호 생성"""
        import datetime
        import random
        now = datetime.datetime.now()
        return f"ORD{now.strftime('%Y%m%d')}{random.randint(100000, 999999)}"


class OrderItem(models.Model):
    """주문 아이템 모델"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    
    # 주문 당시의 상품 정보 (상품이 변경되어도 주문 내역은 유지)
    product_title = models.CharField(max_length=200, verbose_name='상품명')
    product_price = models.PositiveIntegerField(verbose_name='상품 가격')
    quantity = models.PositiveIntegerField(verbose_name='수량')
    
    # 선택된 옵션들 (JSON 필드로 저장)
    selected_options = models.JSONField(
        default=dict, blank=True,
        verbose_name='선택된 옵션들',
        help_text='옵션명: 선택지명 형태로 저장'
    )
    options_price = models.PositiveIntegerField(default=0, verbose_name='옵션 가격')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '주문 아이템'
        verbose_name_plural = '주문 아이템들'
        ordering = ['created_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['order']),        # 주문별 아이템 조회용
            models.Index(fields=['product']),      # 상품별 주문 조회용
            models.Index(fields=['created_at']),   # 정렬용
            models.Index(fields=['order', 'created_at']), # 주문 아이템 목록용
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.product_title} x{self.quantity}"
    
    @property
    def unit_price(self):
        """개당 가격 (상품가격 + 옵션가격)"""
        product_price = self.product_price or 0
        options_price = self.options_price or 0
        return product_price + options_price
    
    @property
    def total_price(self):
        """총 가격 (개당가격 * 수량)"""
        quantity = self.quantity or 0
        return self.unit_price * quantity


class PurchaseHistory(models.Model):
    """구매 내역 모델 (마이페이지용)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchase_history')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='purchase_history')
    
    # 구매 내역 요약 정보
    store_name = models.CharField(max_length=100, verbose_name='스토어명')
    total_amount = models.PositiveIntegerField(verbose_name='결제 금액')
    purchase_date = models.DateTimeField(verbose_name='구매 날짜')
    
    # 개인정보 보호를 위한 자동 삭제 필드
    auto_delete_at = models.DateTimeField(
        verbose_name='자동 삭제 예정일',
        help_text='구매 후 3개월 뒤 자동 삭제'
    )
    
    class Meta:
        verbose_name = '구매 내역'
        verbose_name_plural = '구매 내역들'
        ordering = ['-purchase_date']
        indexes = [
            models.Index(fields=['user', 'purchase_date']),
            models.Index(fields=['auto_delete_at']),
            models.Index(fields=['user']),           # 사용자별 구매내역 조회용
            models.Index(fields=['purchase_date']),  # 관리자 필터링용
            models.Index(fields=['order']),          # OneToOne 필드 최적화
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.store_name} ({self.purchase_date.date()})"
    
    def save(self, *args, **kwargs):
        if not self.auto_delete_at and self.purchase_date:
            # 구매 날짜로부터 3개월 뒤 자동 삭제 날짜 설정
            from datetime import timedelta
            self.auto_delete_at = self.purchase_date + timedelta(days=90)
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """인보이스 모델"""
    STATUS_CHOICES = [
        ('pending', '결제 대기'),
        ('paid', '결제 완료'),
        ('expired', '만료됨'),
        ('cancelled', '취소됨'),
    ]
    
    # 기본 정보
    payment_hash = models.CharField(max_length=100, unique=True, verbose_name='결제 해시')
    invoice_string = models.TextField(verbose_name='인보이스 문자열')
    amount_sats = models.PositiveIntegerField(verbose_name='금액(사토시)')
    memo = models.TextField(blank=True, verbose_name='메모')
    
    # 상태 정보
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name='상태'
    )
    
    # 사용자 및 관련 정보
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True, verbose_name='사용자')
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='invoices', verbose_name='스토어')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices', verbose_name='주문')
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    expires_at = models.DateTimeField(verbose_name='만료일시')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='결제일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '인보이스'
        verbose_name_plural = '인보이스들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_hash']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['store', 'status']),
        ]
    
    def __str__(self):
        user_display = self.user.username if self.user else '비회원'
        return f"{user_display} - {self.amount_sats} sats ({self.get_status_display()})"
    
    @property
    def is_expired(self):
        """만료 여부 확인"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def status_display_color(self):
        """상태별 색상 반환"""
        colors = {
            'pending': '#f59e0b',  # 주황색
            'paid': '#10b981',     # 초록색
            'expired': '#6b7280',  # 회색
            'cancelled': '#ef4444', # 빨간색
        }
        return colors.get(self.status, '#6b7280')
