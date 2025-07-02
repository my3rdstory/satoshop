from django.core.management.base import BaseCommand
from django.utils import timezone
from meetup.services import cancel_expired_reservations


class Command(BaseCommand):
    help = '만료된 밋업 예약을 자동으로 정리합니다.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 실행하지 않고 결과만 미리 보기',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세한 로그 출력',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write('=' * 50)
        self.stdout.write('밋업 예약 정리 작업 시작')
        self.stdout.write('=' * 50)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN 모드: 실제 변경은 이루어지지 않습니다.')
            )
        
        # 현재 시간
        now = timezone.now()
        self.stdout.write(f'현재 시간: {now.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 만료된 예약 확인
        from meetup.models import MeetupOrder
        
        expired_orders = MeetupOrder.objects.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__lt=now
        ).select_related('meetup', 'user')
        
        expired_count = expired_orders.count()
        
        if expired_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ 정리할 만료된 예약이 없습니다.')
            )
            return
        
        self.stdout.write(f'📋 만료된 예약 {expired_count}개를 발견했습니다.')
        
        if verbose:
            self.stdout.write('\n📝 상세 내역:')
            for order in expired_orders:
                expired_minutes = int((now - order.reservation_expires_at).total_seconds() / 60)
                self.stdout.write(
                    f'  - {order.order_number}: {order.participant_name} '
                    f'({order.meetup.name}) - {expired_minutes}분 전 만료'
                )
        
        if not dry_run:
            # 실제 정리 실행
            cancelled_count = cancel_expired_reservations()
            
            if cancelled_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {cancelled_count}개의 만료된 예약이 정리되었습니다.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️ 정리 과정에서 문제가 발생했습니다.')
                )
        else:
            self.stdout.write(
                self.style.WARNING(f'🔄 DRY RUN: {expired_count}개의 예약이 정리될 예정입니다.')
            )
        
        # 통계 정보
        self.stdout.write('\n📊 현재 예약 통계:')
        
        # 활성 임시 예약 수
        active_reservations = MeetupOrder.objects.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__gt=now
        ).count()
        
        # 확정된 주문 수
        confirmed_orders = MeetupOrder.objects.filter(
            status__in=['confirmed', 'completed']
        ).count()
        
        # 취소된 주문 수
        cancelled_orders = MeetupOrder.objects.filter(
            status='cancelled'
        ).count()
        
        self.stdout.write(f'  - 활성 임시 예약: {active_reservations}개')
        self.stdout.write(f'  - 확정된 주문: {confirmed_orders}개')
        self.stdout.write(f'  - 취소된 주문: {cancelled_orders}개')
        
        # 곧 만료될 예약 경고
        soon_expire_orders = MeetupOrder.objects.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__gt=now,
            reservation_expires_at__lt=now + timezone.timedelta(minutes=5)
        ).count()
        
        if soon_expire_orders > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️ 5분 이내에 만료될 예약: {soon_expire_orders}개')
            )
        
        self.stdout.write('=' * 50)
        self.stdout.write('✨ 밋업 예약 정리 작업 완료')
        self.stdout.write('=' * 50) 