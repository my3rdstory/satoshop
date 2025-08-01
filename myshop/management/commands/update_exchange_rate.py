from django.core.management.base import BaseCommand
from django.utils import timezone
from myshop.services import UpbitExchangeService
from myshop.models import SiteSettings, ExchangeRate
import logging
import sys

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '업비트 API에서 BTC/KRW 환율을 가져와 업데이트합니다 (외부 서버 환율 업데이터 최적화)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='시간 간격에 관계없이 강제로 환율을 업데이트합니다',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세한 로그를 출력합니다',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        # 로깅 레벨 설정
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 [{start_time}] 환율 업데이트 시작 (외부 서버 환율 업데이터)')
        )

        try:
            # force 옵션이 없으면 안내 메시지만 출력
            if not options['force']:
                self.stdout.write(
                    self.style.WARNING('ℹ️  외부 서버에서 crontab으로 자동 업데이트됩니다. 수동 업데이트하려면 --force 옵션을 사용하세요.')
                )
                return

            # 현재 환율 상태 확인
            current_rate = ExchangeRate.get_latest_rate()
            if current_rate:
                self.stdout.write(f'📊 현재 환율: 1 BTC = {current_rate.btc_krw_rate:,} KRW')
            else:
                self.stdout.write('📊 저장된 환율 데이터가 없습니다.')

            # 환율 데이터 가져오기
            self.stdout.write('🌐 업비트 API에서 환율 데이터 가져오는 중...')
            exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
            
            if exchange_rate:
                # 성공 시 상세 정보 출력
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ 환율 업데이트 성공!\n'
                        f'   새로운 환율: 1 BTC = {exchange_rate.btc_krw_rate:,} KRW\n'
                        f'   업데이트 시간: {exchange_rate.created_at}'
                    )
                )
                
                # 환율 변화 확인
                if current_rate:
                    rate_change = exchange_rate.btc_krw_rate - current_rate.btc_krw_rate
                    change_percent = (rate_change / current_rate.btc_krw_rate) * 100
                    
                    if rate_change > 0:
                        self.stdout.write(f'📈 환율 상승: +{rate_change:,.0f} KRW ({change_percent:+.2f}%)')
                    elif rate_change < 0:
                        self.stdout.write(f'📉 환율 하락: {rate_change:,.0f} KRW ({change_percent:+.2f}%)')
                    else:
                        self.stdout.write('📊 환율 변화 없음')
                
                # 환율 데이터 개수 확인
                total_rates = ExchangeRate.objects.count()
                self.stdout.write(f'💾 저장된 환율 데이터: {total_rates}개')
                
                # 성공 로그
                logger.info(f'환율 업데이트 성공: 1 BTC = {exchange_rate.btc_krw_rate:,} KRW')
                
            else:
                error_msg = '❌ 환율 업데이트 실패: API에서 데이터를 가져올 수 없습니다'
                self.stdout.write(self.style.ERROR(error_msg))
                logger.error('환율 업데이트 실패: API 응답 없음')
                
                # 외부 서버에서 실패를 명확히 알 수 있도록 exit code 설정
                sys.exit(1)
                
        except Exception as e:
            error_msg = f'❌ 환율 업데이트 중 오류 발생: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(f'환율 업데이트 오류: {e}', exc_info=True)
            
            # 외부 서버에서 실패를 명확히 알 수 있도록 exit code 설정
            sys.exit(1)

        # 실행 시간 계산
        end_time = timezone.now()
        duration = end_time - start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🎉 [{end_time}] 환율 업데이트 완료\n'
                f'   실행 시간: {duration.total_seconds():.2f}초'
            )
        ) 