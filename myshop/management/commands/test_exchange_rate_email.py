from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from myshop.models import ExchangeRate
from myshop.services import UpbitExchangeService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '환율 이메일 알림 기능을 테스트합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='실제 환율 업데이트 없이 테스트 이메일만 전송합니다',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='테스트 이메일을 보낼 주소 (기본값: 설정된 알림 이메일)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 환율 이메일 알림 테스트 시작'))
        
        test_email = options.get('email') or getattr(settings, 'EXCHANGE_RATE_NOTIFICATION_EMAIL', 'satoshopkr@gmail.com')
        
        if options['test_only']:
            # 테스트 이메일만 전송
            self.send_test_email(test_email)
        else:
            # 실제 환율 업데이트 후 이메일 전송 테스트
            self.test_with_real_update(test_email)

    def send_test_email(self, email):
        """테스트 이메일 전송"""
        try:
            current_time = timezone.now()
            latest_rate = ExchangeRate.get_latest_rate()
            
            if latest_rate:
                rate_info = f"{latest_rate.btc_krw_rate:,} KRW"
                rate_time = latest_rate.created_at.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')
            else:
                rate_info = "데이터 없음"
                rate_time = "N/A"
            
            subject = f'[Satoshop] 환율 이메일 알림 테스트 - {current_time.strftime("%Y-%m-%d %H:%M:%S")}'
            
            message = f"""
안녕하세요, Satoshop 관리자님!

이것은 환율 이메일 알림 기능의 테스트 메일입니다.

📊 현재 환율 정보:
- BTC/KRW 환율: {rate_info}
- 마지막 업데이트: {rate_time}
- 테스트 시간: {current_time.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}

✅ 이메일 알림 시스템이 정상적으로 작동하고 있습니다.

---
이 메일은 테스트용으로 발송된 알림입니다.
Satoshop 시스템에서 발송됨
            """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ 테스트 이메일 전송 성공: {email}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 테스트 이메일 전송 실패: {str(e)}')
            )

    def test_with_real_update(self, email):
        """실제 환율 업데이트 후 이메일 전송 테스트"""
        try:
            self.stdout.write('📡 업비트 API에서 환율 데이터 가져오는 중...')
            
            # 환율 업데이트 (이때 시그널이 발생하여 이메일이 자동 전송됨)
            exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
            
            if exchange_rate:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ 환율 업데이트 성공: 1 BTC = {exchange_rate.btc_krw_rate:,} KRW'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'📧 {email}로 자동 알림 이메일이 전송되었습니다.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ 환율 업데이트 실패: API에서 데이터를 가져올 수 없습니다.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 환율 업데이트 테스트 실패: {str(e)}')
            ) 