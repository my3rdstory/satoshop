from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from orders.models import Order, OrderItem
from products.models import Product
from stores.models import Store
import random
import datetime
from faker import Faker
from dateutil.relativedelta import relativedelta

fake = Faker('ko_KR')


class Command(BaseCommand):
    help = '특정 상품에 대한 테스트 주문 데이터를 생성합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-id',
            type=int,
            default=47,
            help='주문 데이터를 생성할 상품 ID (기본값: 47)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='생성할 주문 수 (기본값: 100)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='기존 주문 데이터를 먼저 삭제',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 생성하지 않고 미리보기만 표시',
        )

    def handle(self, *args, **options):
        product_id = options['product_id']
        count = options['count']
        clear = options['clear']
        dry_run = options['dry_run']

        self.stdout.write('=' * 60)
        self.stdout.write('🛒 테스트 주문 데이터 생성기')
        self.stdout.write('=' * 60)

        # 상품 확인
        try:
            product = Product.objects.get(id=product_id)
            self.stdout.write(f'📦 대상 상품: {product.title} (ID: {product.id})')
            self.stdout.write(f'🏪 스토어: {product.store.store_name}')
        except Product.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 상품 ID {product_id}를 찾을 수 없습니다.')
            )
            return

        # 기존 데이터 확인
        existing_orders = OrderItem.objects.filter(product=product).count()
        self.stdout.write(f'📊 기존 주문 건수: {existing_orders}개')

        if clear and existing_orders > 0:
            if not dry_run:
                self.stdout.write('🗑️ 기존 주문 데이터를 삭제합니다...')
                # OrderItem을 먼저 삭제하고, 연결된 Order들 중 다른 OrderItem이 없는 것들을 삭제
                orders_to_check = set()
                order_items = OrderItem.objects.filter(product=product)
                for item in order_items:
                    orders_to_check.add(item.order.id)
                
                # OrderItem 삭제
                deleted_items = order_items.delete()[0]
                
                # 빈 Order들 삭제
                deleted_orders = 0
                for order_id in orders_to_check:
                    try:
                        order = Order.objects.get(id=order_id)
                        if not order.items.exists():
                            order.delete()
                            deleted_orders += 1
                    except Order.DoesNotExist:
                        pass
                
                self.stdout.write(f'   ✅ {deleted_items}개 주문 아이템, {deleted_orders}개 주문 삭제 완료')
            else:
                self.stdout.write(f'🔍 DRY RUN: {existing_orders}개의 기존 주문이 삭제될 예정입니다.')

        if dry_run:
            self.stdout.write(f'🔍 DRY RUN: {count}개의 테스트 주문을 생성할 예정입니다.')
            self.stdout.write('실제 생성을 원하면 --dry-run 옵션을 제거하고 다시 실행하세요.')
            return

        # 사용자 목록 준비 (기존 사용자들 사용)
        users = list(User.objects.all()[:50])  # 최대 50명의 사용자 사용
        if not users:
            self.stdout.write(
                self.style.ERROR('❌ 사용자가 없습니다. 먼저 사용자를 생성해주세요.')
            )
            return

        self.stdout.write(f'👥 {len(users)}명의 사용자로 주문 생성')
        self.stdout.write(f'📅 주문 생성 기간: 2024년 12월 ~ 2025년 7월')
        self.stdout.write(f'🎯 생성할 주문 수: {count}개')

        # 주문 상태 선택지
        order_statuses = ['paid', 'paid', 'paid', 'paid', 'paid', 'shipped', 'delivered', 'cancelled']

        # 주문 생성
        created_count = 0
        errors = 0

        with transaction.atomic():
            for i in range(count):
                try:
                    # 랜덤 날짜 생성 (2024년 12월부터 2025년 7월까지)
                    start_date = datetime.datetime(2024, 12, 1, tzinfo=timezone.get_current_timezone())
                    end_date = datetime.datetime(2025, 7, 31, 23, 59, 59, tzinfo=timezone.get_current_timezone())
                    random_date = fake.date_time_between(
                        start_date=start_date,
                        end_date=end_date,
                        tzinfo=timezone.get_current_timezone()
                    )

                    # 랜덤 사용자 선택
                    user = random.choice(users)

                    # 주문번호 생성
                    order_number = f"ORD-{random_date.strftime('%Y%m%d')}-{random_date.strftime('%H%M%S')}"

                    # 수량 결정 (1-5개)
                    quantity = random.randint(1, 5)

                    # 가격 설정 (상품 가격 기준으로 약간의 변동)
                    base_price = product.public_price or 10000
                    product_price = base_price + random.randint(-1000, 1000)
                    if product_price < 1000:
                        product_price = 1000

                    # 옵션 가격 (0-5000 sats)
                    options_price = random.randint(0, 5000)

                    # 배송비 (2000-5000원)
                    shipping_fee = random.randint(2000, 5000)
                    store = product.store
                    store.shipping_fee_mode = 'flat'
                    store.shipping_fee_sats = shipping_fee
                    store.shipping_fee_krw = 0
                    store.free_shipping_threshold_krw = None
                    store.free_shipping_threshold_sats = None
                    store.save(update_fields=[
                        'shipping_fee_mode',
                        'shipping_fee_sats',
                        'shipping_fee_krw',
                        'free_shipping_threshold_krw',
                        'free_shipping_threshold_sats'
                    ])

                    # 총액 계산
                    subtotal = (product_price + options_price) * quantity
                    total_amount = subtotal + shipping_fee

                    # 주문 상태 결정
                    status = random.choice(order_statuses)

                    # 결제 시간 설정
                    if status != 'cancelled':
                        paid_at = random_date + timezone.timedelta(minutes=random.randint(1, 30))
                    else:
                        paid_at = None

                    # 주문 생성
                    order = Order.objects.create(
                        order_number=order_number,
                        user=user,
                        store=product.store,
                        status=status,
                        buyer_name=fake.name(),
                        buyer_phone=fake.phone_number(),
                        buyer_email=fake.email(),
                        shipping_postal_code=fake.postcode(),
                        shipping_address=fake.address(),
                        shipping_detail_address=fake.building_number() + '호' if random.random() < 0.7 else '',
                        order_memo=fake.text(max_nb_chars=100) if random.random() < 0.3 else '',
                        subtotal=subtotal,
                        shipping_fee=shipping_fee,
                        total_amount=total_amount,
                        payment_id=f"payment_{random.randint(100000, 999999)}" if status != 'cancelled' else '',
                        paid_at=paid_at,
                    )
                    
                    # auto_now_add, auto_now 필드는 수동 설정이 불가능하므로 
                    # 생성 후 직접 업데이트
                    Order.objects.filter(id=order.id).update(
                        created_at=random_date,
                        updated_at=random_date
                    )

                    # 선택된 옵션 생성 (랜덤)
                    selected_options = {}
                    if random.random() < 0.6:  # 60% 확률로 옵션 선택
                        option_names = ['색상', '사이즈', '재질', '스타일']
                        option_choices = {
                            '색상': ['빨강', '파랑', '검정', '흰색', '회색'],
                            '사이즈': ['S', 'M', 'L', 'XL'],
                            '재질': ['면', '폴리에스터', '혼방'],
                            '스타일': ['클래식', '모던', '캐주얼']
                        }
                        
                        num_options = random.randint(1, 2)
                        chosen_options = random.sample(option_names, num_options)
                        
                        for option_name in chosen_options:
                            choice = random.choice(option_choices[option_name])
                            selected_options[option_name] = choice

                    # 주문 아이템 생성
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_title=product.title,
                        product_price=product_price,
                        quantity=quantity,
                        selected_options=selected_options,
                        options_price=options_price,
                    )
                    
                    # OrderItem의 created_at도 수동 설정
                    OrderItem.objects.filter(id=order_item.id).update(
                        created_at=random_date
                    )

                    created_count += 1

                    # 진행률 표시
                    if (i + 1) % 10 == 0:
                        self.stdout.write(f'⏳ {i + 1}/{count} 주문 생성 중... ({(i + 1)/count*100:.1f}%)')

                except Exception as e:
                    errors += 1
                    if errors <= 5:  # 처음 5개 오류만 표시
                        self.stdout.write(f'❌ 주문 생성 오류 #{errors}: {str(e)}')

        # 결과 요약
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('📊 테스트 데이터 생성 완료')
        self.stdout.write('=' * 60)
        self.stdout.write(f'✅ 성공적으로 생성된 주문: {created_count}개')
        if errors > 0:
            self.stdout.write(f'❌ 오류 발생: {errors}개')

        # 생성된 데이터 통계
        self.stdout.write('\n📈 생성된 데이터 통계:')
        
        # 월별 통계
        total_orders = OrderItem.objects.filter(product=product)
        self.stdout.write(f'   총 주문 건수: {total_orders.count()}개')

        # 상태별 통계
        status_stats = {}
        for item in total_orders:
            status = item.order.status
            status_stats[status] = status_stats.get(status, 0) + 1

        self.stdout.write('   상태별 분포:')
        for status, count in status_stats.items():
            status_display = dict(Order.ORDER_STATUS_CHOICES).get(status, status)
            self.stdout.write(f'     - {status_display}: {count}개')

        # 최근 주문들
        recent_orders = total_orders.order_by('-order__created_at')[:5]
        self.stdout.write('\n🕐 최근 주문 5건:')
        for item in recent_orders:
            order = item.order
            self.stdout.write(
                f'   - {order.order_number}: {order.buyer_name} '
                f'({item.quantity}개, {order.get_status_display()}, '
                f'{order.created_at.strftime("%Y-%m-%d %H:%M")})'
            )

        self.stdout.write('\n🎉 테스트 데이터 생성이 완료되었습니다!')
        self.stdout.write('이제 필터 기능을 테스트해보세요.') 
