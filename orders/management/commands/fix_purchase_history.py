from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import Order, PurchaseHistory


class Command(BaseCommand):
    help = '누락된 PurchaseHistory 레코드를 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 생성하지 않고 누락된 레코드만 확인합니다.',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='특정 사용자의 PurchaseHistory만 생성합니다 (username).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        username = options.get('user')
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('PurchaseHistory 누락 확인 및 생성'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # 쿼리 준비
        paid_orders = Order.objects.filter(status='paid')
        
        if username:
            paid_orders = paid_orders.filter(user__username=username)
            self.stdout.write(f'사용자 {username}의 주문만 처리합니다.')
        
        total_orders = paid_orders.count()
        missing_count = 0
        created_count = 0
        errors = []
        
        self.stdout.write(f'총 결제 완료 주문: {total_orders}건')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN 모드 - 실제로 생성하지 않습니다.'))
        
        with transaction.atomic():
            for order in paid_orders:
                # PurchaseHistory 존재 확인
                if not PurchaseHistory.objects.filter(order=order).exists():
                    missing_count += 1
                    
                    if dry_run:
                        self.stdout.write(
                            f'  - {order.order_number} (User: {order.user.username}, '
                            f'Store: {order.store.store_name})'
                        )
                    else:
                        try:
                            PurchaseHistory.objects.create(
                                user=order.user,
                                order=order,
                                store_name=order.store.store_name,
                                total_amount=order.total_amount,
                                purchase_date=order.paid_at or order.created_at
                            )
                            created_count += 1
                            
                            if created_count % 10 == 0:
                                self.stdout.write(f'진행 중: {created_count}건 생성...')
                                
                        except Exception as e:
                            error_msg = f'오류 - {order.order_number}: {str(e)}'
                            errors.append(error_msg)
                            self.stdout.write(self.style.ERROR(error_msg))
        
        # 결과 출력
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'누락된 PurchaseHistory: {missing_count}건')
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'성공적으로 생성: {created_count}건'))
            if errors:
                self.stdout.write(self.style.ERROR(f'실패: {len(errors)}건'))
                for error in errors[:5]:  # 처음 5개만 표시
                    self.stdout.write(self.style.ERROR(f'  {error}'))
                if len(errors) > 5:
                    self.stdout.write(self.style.ERROR(f'  ... 외 {len(errors) - 5}건'))
        
        # 최종 통계
        total_ph = PurchaseHistory.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n현재 총 PurchaseHistory: {total_ph}건'))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n실제로 생성하려면 --dry-run 옵션 없이 다시 실행하세요.'
                )
            )