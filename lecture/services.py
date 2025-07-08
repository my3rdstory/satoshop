"""
라이브 강의 관련 서비스 모듈
"""
import logging
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMessage
from django.utils import timezone
from django.template.loader import render_to_string
from django.template import Context, Template

logger = logging.getLogger(__name__)


def send_live_lecture_notification_email(live_lecture_order):
    """
    라이브 강의 참가 확정 시 스토어 주인장에게 이메일 발송
    
    Args:
        live_lecture_order: LiveLectureOrder 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 🛡️ 중복 이메일 발송 방지: 주문번호 기반으로 확실하게 방지
        from django.core.cache import cache
        email_cache_key = f"live_lecture_owner_email_sent_{live_lecture_order.order_number}"
        
        if cache.get(email_cache_key):
            logger.debug(f"라이브 강의 주인장 이메일 {live_lecture_order.order_number}: 이미 발송됨")
            return False
        
        # 스토어 이메일 설정 확인
        store = live_lecture_order.live_lecture.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"라이브 강의 {live_lecture_order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"라이브 강의 {live_lecture_order.order_number}: Gmail 설정 불완전 (이메일: {bool(store.email_host_user)}, 비밀번호: {bool(store.email_host_password_encrypted)})")
            return False
            
        # 🔥 중요: 수신 이메일 주소 확인 (주인장 이메일)
        if not store.owner_email:
            logger.debug(f"라이브 강의 {live_lecture_order.order_number}: 스토어 주인장 이메일 주소가 설정되지 않음")
            return False
            
        # 스토어별 SMTP 설정
        backend = EmailBackend(
            host='smtp.gmail.com',
            port=587,
            username=store.email_host_user,
            password=store.get_email_host_password(),
            use_tls=True,
            fail_silently=False,
        )
        
        # 이메일 내용 생성 (템플릿 파일 사용)
        subject = f'[{store.store_name}] 새로운 라이브 강의 참가 신청 - {live_lecture_order.order_number}'
        
        # TXT 참가확인서 내용 생성 (단순한 문자열로 생성)
        lecture_content = f"""
▣ 라이브 강의 참가 확정 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
강의명: {live_lecture_order.live_lecture.name}
주문번호: {live_lecture_order.order_number}
참가자: {live_lecture_order.user.username} ({live_lecture_order.user.email})
참가 확정일시: {live_lecture_order.confirmed_at.strftime('%Y년 %m월 %d일 %H시 %M분') if live_lecture_order.confirmed_at else '미확정'}
"""
        
        if live_lecture_order.live_lecture.date_time:
            lecture_content += f"강의 일시: {live_lecture_order.live_lecture.date_time.strftime('%Y년 %m월 %d일 (%A) %H시 %M분')}\n"
        
        if live_lecture_order.price > 0:
            lecture_content += f"결제금액: {live_lecture_order.price:,.0f} sats\n"
        else:
            lecture_content += "참가비: 무료\n"
            
        if live_lecture_order.live_lecture.special_notes:
            lecture_content += f"특이사항: {live_lecture_order.live_lecture.special_notes}\n"
        
        # 템플릿 파일 읽기 및 렌더링
        try:
            with open('lecture/templates/lecture/email/live_lecture_owner_notification.txt', 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            context = Context({
                'store': store,
                'live_lecture': live_lecture_order.live_lecture,
                'lecture_content': lecture_content
            })
            message = template.render(context)
        except Exception as e:
            logger.warning(f"템플릿 파일 읽기 실패, 기본 메시지 사용: {str(e)}")
            # 템플릿 파일 실패 시 기본 메시지
            message = f"""안녕하세요, {store.owner_name}님!

{store.store_name}에서 주최하는 "{live_lecture_order.live_lecture.name}" 라이브 강의에 새로운 참가 신청이 접수되었습니다.

아래는 참가자 상세 정보입니다:

{lecture_content}

---
이 이메일은 {store.store_name}의 자동 알림 시스템에서 발송되었습니다.

감사합니다!
SatoShop 팀"""
        
        # 이메일 발송
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=f'{store.email_from_display} <{store.email_host_user}>',
            to=[store.owner_email],
            connection=backend
        )
        
        # TODO: QR코드 첨부 기능은 추후 구현 예정
        
        email.send()
        
        # 🛡️ 이메일 발송 성공 기록 (중복 방지용)
        from django.core.cache import cache
        email_cache_key = f"live_lecture_owner_email_sent_{live_lecture_order.order_number}"
        cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"라이브 강의 알림 이메일 발송 성공 - 주문: {live_lecture_order.order_number}, 수신: {store.owner_email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"라이브 강의 알림 이메일 발송 실패 - 주문: {live_lecture_order.order_number}, 오류: {str(e)}")
        return False


def send_live_lecture_participant_confirmation_email(live_lecture_order):
    """
    라이브 강의 참가 확정 시 참가자에게 확인 이메일 발송
    
    Args:
        live_lecture_order: LiveLectureOrder 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 참가자 이메일 주소 확인
        if not live_lecture_order.user.email:
            logger.debug(f"라이브 강의 {live_lecture_order.order_number}: 참가자 이메일 주소가 없음")
            return False
        
        # 🛡️ 중복 이메일 발송 방지: 주문번호 기반으로 확실하게 방지
        from django.core.cache import cache
        email_cache_key = f"live_lecture_participant_email_sent_{live_lecture_order.order_number}"
        
        if cache.get(email_cache_key):
            logger.debug(f"라이브 강의 참가자 이메일 {live_lecture_order.order_number}: 이미 발송됨")
            return False
        
        # 스토어 이메일 설정 확인
        store = live_lecture_order.live_lecture.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"라이브 강의 참가자 이메일 {live_lecture_order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"라이브 강의 참가자 이메일 {live_lecture_order.order_number}: Gmail 설정 불완전")
            return False
            
        # 스토어별 SMTP 설정
        backend = EmailBackend(
            host='smtp.gmail.com',
            port=587,
            username=store.email_host_user,
            password=store.get_email_host_password(),
            use_tls=True,
            fail_silently=False,
        )
        
        # 이메일 내용 생성 (템플릿 파일 사용)
        subject = f'[{store.store_name}] "{live_lecture_order.live_lecture.name}" 라이브 강의 참가 확정 - {live_lecture_order.order_number}'
        
        # 템플릿 파일 읽기 및 렌더링
        try:
            with open('lecture/templates/lecture/email/live_lecture_participant_confirmation.txt', 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            context = Context({
                'store': store,
                'live_lecture': live_lecture_order.live_lecture,
                'user': live_lecture_order.user,
                'confirmed_at': live_lecture_order.confirmed_at or timezone.now(),
                'order_number': live_lecture_order.order_number,
                'total_price': live_lecture_order.price
            })
            message = template.render(context)
        except Exception as e:
            logger.warning(f"참가자 템플릿 파일 읽기 실패, 기본 메시지 사용: {str(e)}")
            # 템플릿 파일 실패 시 기본 메시지
            message = f"""안녕하세요, {live_lecture_order.user.username}님!

"{live_lecture_order.live_lecture.name}" 라이브 강의 참가 신청이 성공적으로 완료되었습니다. 🎉

주문번호: {live_lecture_order.order_number}
강의명: {live_lecture_order.live_lecture.name}
주최: {store.store_name}

강의에서 뵙겠습니다!

감사합니다,
{store.store_name} & SatoShop 팀"""
        
        # 이메일 발송
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=f'{store.email_from_display} <{store.email_host_user}>',
            to=[live_lecture_order.user.email],
            connection=backend
        )
        
        # TODO: QR코드 첨부 기능은 추후 구현 예정
        
        email.send()
        
        # 🛡️ 이메일 발송 성공 기록 (중복 방지용)
        from django.core.cache import cache
        email_cache_key = f"live_lecture_participant_email_sent_{live_lecture_order.order_number}"
        cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"라이브 강의 참가자 확인 이메일 발송 성공 - 주문: {live_lecture_order.order_number}, 수신: {live_lecture_order.user.email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"라이브 강의 참가자 확인 이메일 발송 실패 - 주문: {live_lecture_order.order_number}, 오류: {str(e)}")
        return False 