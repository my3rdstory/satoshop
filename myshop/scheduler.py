import logging
import atexit
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .services import UpbitExchangeService
from .models import SiteSettings

logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
scheduler = None

def is_cloud_environment():
    """클라우드 환경 감지 (Render.com, Heroku 등)"""
    cloud_indicators = [
        'RENDER',  # Render.com
        'DYNO',    # Heroku
        'RAILWAY_ENVIRONMENT',  # Railway
        'VERCEL',  # Vercel
        'NETLIFY', # Netlify
    ]
    return any(os.environ.get(indicator) for indicator in cloud_indicators)

def is_primary_instance():
    """
    현재 인스턴스가 스케줄러를 실행해야 하는 주 인스턴스인지 확인
    클라우드 환경에서는 첫 번째 인스턴스만 스케줄러 실행
    """
    if not is_cloud_environment():
        return True
    
    # Render.com의 경우 RENDER_INSTANCE_ID 환경변수 확인
    instance_id = os.environ.get('RENDER_INSTANCE_ID', '')
    if instance_id:
        # 인스턴스 ID가 있으면 첫 번째 인스턴스인지 확인
        # 일반적으로 첫 번째 인스턴스는 ID가 가장 작음
        return instance_id.endswith('0') or instance_id.endswith('1')
    
    # Heroku의 경우 DYNO 환경변수 확인
    dyno = os.environ.get('DYNO', '')
    if dyno:
        # web.1이 주 인스턴스
        return dyno == 'web.1'
    
    # 기타 환경에서는 기본적으로 실행
    return True

def update_exchange_rate_job():
    """환율 업데이트 작업"""
    try:
        # 클라우드 환경에서 중복 실행 방지를 위한 추가 체크
        if is_cloud_environment():
            # 최근 30초 이내에 실행된 기록이 있으면 스킵
            recent_execution = DjangoJobExecution.objects.filter(
                job_id='update_exchange_rate',
                run_time__gte=timezone.now() - timedelta(seconds=30)
            ).first()
            
            if recent_execution:
                logger.debug("최근에 다른 인스턴스에서 환율 업데이트가 실행됨. 스킵.")
                return
        
        settings_obj = SiteSettings.get_settings()
        
        # 환율 업데이트가 필요한지 확인
        if settings_obj.should_update_exchange_rate():
            exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
            if exchange_rate:
                logger.info(f"스케줄러: 환율 업데이트 성공 - 1 BTC = {exchange_rate.btc_krw_rate:,} KRW")
            else:
                logger.error("스케줄러: 환율 업데이트 실패")
        else:
            logger.debug("스케줄러: 환율 업데이트 시간이 아직 되지 않음")
            
    except Exception as e:
        logger.error(f"스케줄러: 환율 업데이트 중 오류 발생 - {e}")

@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """일주일 이상 된 작업 실행 기록 삭제"""
    try:
        DjangoJobExecution.objects.delete_old_job_executions(max_age)
        logger.info("오래된 작업 실행 기록 정리 완료")
    except Exception as e:
        logger.error(f"작업 실행 기록 정리 실패: {e}")

def shutdown_scheduler():
    """스케줄러 종료"""
    global scheduler
    if scheduler and scheduler.running:
        logger.info("환율 업데이트 스케줄러 종료")
        try:
            scheduler.shutdown(wait=False)
        except Exception as e:
            logger.error(f"스케줄러 종료 중 오류: {e}")
        finally:
            scheduler = None

def start_scheduler():
    """스케줄러 시작"""
    global scheduler
    
    # 클라우드 환경에서 주 인스턴스가 아니면 스케줄러 시작하지 않음
    if is_cloud_environment() and not is_primary_instance():
        logger.info("클라우드 환경의 보조 인스턴스입니다. 스케줄러를 시작하지 않습니다.")
        return
    
    # 이미 실행 중인 스케줄러가 있으면 종료
    if scheduler and scheduler.running:
        logger.info("기존 스케줄러가 실행 중입니다. 종료 후 재시작합니다.")
        shutdown_scheduler()
    
    logger.info("환율 업데이트 스케줄러를 시작합니다.")
    
    if is_cloud_environment():
        logger.info(f"클라우드 환경 감지됨. 인스턴스 ID: {os.environ.get('RENDER_INSTANCE_ID', 'N/A')}")
    
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # 어드민 설정에서 업데이트 간격 가져오기
    try:
        settings_obj = SiteSettings.get_settings()
        update_interval = settings_obj.exchange_rate_update_interval
        logger.info(f"환율 업데이트 간격: {update_interval}분")
    except Exception as e:
        logger.warning(f"설정 로드 실패, 기본값 1분 사용: {e}")
        update_interval = 1
    
    # 환율 업데이트 작업 (어드민 설정 간격으로 실행)
    scheduler.add_job(
        update_exchange_rate_job,
        trigger=IntervalTrigger(minutes=update_interval),
        id='update_exchange_rate',
        max_instances=1,
        replace_existing=True,
        coalesce=True,  # 누적된 작업들을 하나로 합침
        misfire_grace_time=30,  # 30초 이내 지연은 허용
    )
    
    # 오래된 작업 실행 기록 삭제 (매일 자정)
    scheduler.add_job(
        delete_old_job_executions,
        trigger="cron",
        hour=0,
        minute=0,
        id='delete_old_job_executions',
        max_instances=1,
        replace_existing=True,
        coalesce=True,
    )
    
    try:
        logger.info("환율 업데이트 스케줄러 시작")
        scheduler.start()
        
        # 프로그램 종료 시 스케줄러 자동 종료 등록
        atexit.register(shutdown_scheduler)
        
        # 시작 후 즉시 한 번 실행 (클라우드 환경에서 초기 데이터 확보)
        if is_cloud_environment():
            logger.info("클라우드 환경에서 초기 환율 데이터 업데이트 실행")
            try:
                update_exchange_rate_job()
            except Exception as e:
                logger.error(f"초기 환율 업데이트 실패: {e}")
        
    except Exception as e:
        logger.error(f"스케줄러 시작 실패: {e}")
        scheduler = None 