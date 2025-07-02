"""
밋업 관련 서비스 모듈
"""
import logging
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMessage
from django.utils import timezone
from django.template.loader import render_to_string
from django.template import Context, Template

logger = logging.getLogger(__name__)


def send_meetup_notification_email(meetup_order):
    """
    밋업 참가 확정 시 스토어 주인장에게 이메일 발송
    
    Args:
        meetup_order: MeetupOrder 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 🛡️ 중복 이메일 발송 방지: 같은 payment_hash로 이미 이메일을 발송했는지 확인
        if meetup_order.payment_hash:
            from django.core.cache import cache
            email_cache_key = f"meetup_email_sent_{meetup_order.payment_hash}_{meetup_order.meetup.store.id}"
            
            if cache.get(email_cache_key):
                logger.debug(f"밋업 {meetup_order.order_number}: 같은 결제ID({meetup_order.payment_hash})로 이미 이메일 발송됨")
                return False
        
        # 스토어 이메일 설정 확인
        store = meetup_order.meetup.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"밋업 {meetup_order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"밋업 {meetup_order.order_number}: Gmail 설정 불완전 (이메일: {bool(store.email_host_user)}, 비밀번호: {bool(store.email_host_password_encrypted)})")
            return False
            
        # 🔥 중요: 수신 이메일 주소 확인 (주인장 이메일)
        if not store.owner_email:
            logger.debug(f"밋업 {meetup_order.order_number}: 스토어 주인장 이메일 주소가 설정되지 않음")
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
        subject = f'[{store.store_name}] 새로운 밋업 참가 신청 - {meetup_order.order_number}'
        
        # TXT 참가확인서 내용 생성
        from .formatters import MeetupTxtFormatter
        txt_formatter = MeetupTxtFormatter(meetup_order)
        meetup_content = txt_formatter.generate()
        
        # 템플릿 파일 읽기 및 렌더링
        try:
            with open('meetup/templates/meetup/email/owner_notification.txt', 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            context = Context({
                'store': store,
                'meetup': meetup_order.meetup,
                'meetup_content': meetup_content
            })
            message = template.render(context)
        except Exception as e:
            logger.warning(f"템플릿 파일 읽기 실패, 기본 메시지 사용: {str(e)}")
            # 템플릿 파일 실패 시 기본 메시지
            message = f"""안녕하세요, {store.owner_name}님!

{store.store_name}에서 주최하는 "{meetup_order.meetup.name}" 밋업에 새로운 참가 신청이 접수되었습니다.

아래는 참가자 상세 정보입니다:

{meetup_content}

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
        
        # PNG QR코드 첨부파일 추가
        try:
            from .formatters import MeetupEmailFormatter
            formatter = MeetupEmailFormatter(meetup_order)
            qr_image_data = formatter.generate_qr_code_image()
            
            if qr_image_data:  # QR코드 생성 성공 시만 첨부
                email.attach(
                    f'{meetup_order.order_number}.png',
                    qr_image_data,
                    'image/png'
                )
                logger.info(f"밋업 QR코드 첨부파일 추가: {meetup_order.order_number}.png")
            else:
                logger.warning(f"밋업 QR코드 생성 실패: {meetup_order.order_number}")
        except Exception as e:
            logger.warning(f"밋업 QR코드 첨부 실패: {meetup_order.order_number}, 오류: {str(e)}")
            # QR코드 첨부 실패해도 이메일은 계속 발송
        
        email.send()
        
        # 🛡️ 이메일 발송 성공 기록 (중복 방지용)
        if meetup_order.payment_hash:
            from django.core.cache import cache
            email_cache_key = f"meetup_email_sent_{meetup_order.payment_hash}_{meetup_order.meetup.store.id}"
            cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"밋업 알림 이메일 발송 성공 - 주문: {meetup_order.order_number}, 수신: {store.owner_email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"밋업 알림 이메일 발송 실패 - 주문: {meetup_order.order_number}, 오류: {str(e)}")
        return False


def send_meetup_participant_confirmation_email(meetup_order):
    """
    밋업 참가 확정 시 참가자에게 확인 이메일 발송
    
    Args:
        meetup_order: MeetupOrder 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 참가자 이메일 주소 확인
        if not meetup_order.participant_email:
            logger.debug(f"밋업 {meetup_order.order_number}: 참가자 이메일 주소가 없음")
            return False
        
        # 🛡️ 중복 이메일 발송 방지
        if meetup_order.payment_hash:
            from django.core.cache import cache
            email_cache_key = f"meetup_participant_email_sent_{meetup_order.payment_hash}_{meetup_order.id}"
            
            if cache.get(email_cache_key):
                logger.debug(f"밋업 참가자 이메일 {meetup_order.order_number}: 이미 발송됨")
                return False
        
        # 스토어 이메일 설정 확인
        store = meetup_order.meetup.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"밋업 참가자 이메일 {meetup_order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"밋업 참가자 이메일 {meetup_order.order_number}: Gmail 설정 불완전")
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
        subject = f'[{store.store_name}] "{meetup_order.meetup.name}" 밋업 참가 확정 - {meetup_order.order_number}'
        
        # 템플릿 파일 읽기 및 렌더링
        try:
            with open('meetup/templates/meetup/email/participant_confirmation.txt', 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            context = Context({
                'store': store,
                'meetup': meetup_order.meetup,
                'participant_name': meetup_order.participant_name,
                'confirmed_at': meetup_order.confirmed_at or timezone.now(),
                'order_number': meetup_order.order_number,
                'total_price': meetup_order.total_price
            })
            message = template.render(context)
        except Exception as e:
            logger.warning(f"참가자 템플릿 파일 읽기 실패, 기본 메시지 사용: {str(e)}")
            # 템플릿 파일 실패 시 기본 메시지
            message = f"""안녕하세요, {meetup_order.participant_name}님!

"{meetup_order.meetup.name}" 밋업 참가 신청이 성공적으로 완료되었습니다. 🎉

주문번호: {meetup_order.order_number}
밋업명: {meetup_order.meetup.name}
주최: {store.store_name}

밋업에서 뵙겠습니다!

감사합니다,
{store.store_name} & SatoShop 팀"""
        
        # 이메일 발송
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=f'{store.email_from_display} <{store.email_host_user}>',
            to=[meetup_order.participant_email],
            connection=backend
        )
        
        # PNG QR코드 첨부파일 추가
        try:
            from .formatters import MeetupEmailFormatter
            formatter = MeetupEmailFormatter(meetup_order)
            qr_image_data = formatter.generate_qr_code_image()
            
            if qr_image_data:  # QR코드 생성 성공 시만 첨부
                email.attach(
                    f'{meetup_order.order_number}.png',
                    qr_image_data,
                    'image/png'
                )
                logger.info(f"참가자 QR코드 첨부파일 추가: {meetup_order.order_number}.png")
        except Exception as e:
            logger.warning(f"참가자 QR코드 첨부 실패: {meetup_order.order_number}, 오류: {str(e)}")
            # QR코드 첨부 실패해도 이메일은 계속 발송
        
        email.send()
        
        # 🛡️ 이메일 발송 성공 기록 (중복 방지용)
        if meetup_order.payment_hash:
            from django.core.cache import cache
            email_cache_key = f"meetup_participant_email_sent_{meetup_order.payment_hash}_{meetup_order.id}"
            cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"밋업 참가자 확인 이메일 발송 성공 - 주문: {meetup_order.order_number}, 수신: {meetup_order.participant_email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"밋업 참가자 확인 이메일 발송 실패 - 주문: {meetup_order.order_number}, 오류: {str(e)}")
        return False


def create_temporary_reservation(meetup, user, countdown_seconds=None):
    """
    밋업 임시 예약 생성 (정원 차감)
    
    Args:
        meetup: Meetup 인스턴스
        user: User 인스턴스
        countdown_seconds: 예약 유효시간 (초), None이면 사이트 설정값 사용
    
    Returns:
        tuple: (success: bool, message: str, order: MeetupOrder or None)
    """
    from django.utils import timezone
    from django.db import transaction
    from .models import MeetupOrder
    from myshop.models import SiteSettings
    
    try:
        with transaction.atomic():
            # 기존 대기중인 주문 확인
            existing_order = MeetupOrder.objects.filter(
                meetup=meetup,
                user=user,
                status='pending'
            ).first()
            
            if existing_order:
                # 기존 주문이 아직 유효한지 확인
                if existing_order.reservation_expires_at and timezone.now() < existing_order.reservation_expires_at:
                    return True, "이미 진행 중인 신청이 있습니다.", existing_order
                else:
                    # 만료된 기존 주문은 취소
                    existing_order.status = 'cancelled'
                    existing_order.auto_cancelled_reason = '예약 시간 만료'
                    existing_order.is_temporary_reserved = False
                    existing_order.save()
            
            # 정원 확인 (임시 예약 포함) - 트랜잭션 내에서 최신 상태로 직접 계산
            if meetup.max_participants:
                now = timezone.now()
                # 확정된 주문 수
                confirmed_count = meetup.orders.filter(status__in=['confirmed', 'completed']).count()
                # 유효한 임시 예약 수
                temp_reserved_count = meetup.orders.filter(
                    status='pending',
                    is_temporary_reserved=True,
                    reservation_expires_at__gt=now
                ).count()
                
                current_reserved = confirmed_count + temp_reserved_count
                if current_reserved >= meetup.max_participants:
                    return False, "아쉽게도 조금 전에 밋업 신청이 마감되었습니다. 혹시 취소되는 신청 건이 있는지 추후에 확인해 주세요. 고맙습니다.", None
            
            # 카운트다운 시간 설정
            if countdown_seconds is None:
                site_settings = SiteSettings.get_settings()
                countdown_seconds = site_settings.meetup_countdown_seconds
            
            # 예약 만료 시간 설정
            expires_at = timezone.now() + timezone.timedelta(seconds=countdown_seconds)
            
            # 임시 주문 생성 (정원 차감)
            order = MeetupOrder.objects.create(
                meetup=meetup,
                user=user,
                participant_name=user.get_full_name() or user.username,
                participant_email=user.email or '',
                status='pending',
                is_temporary_reserved=True,
                reservation_expires_at=expires_at,
                base_price=meetup.current_price,
                total_price=meetup.current_price,
                is_early_bird=meetup.is_discounted and meetup.is_early_bird_active,
                discount_rate=meetup.public_discount_rate if meetup.is_early_bird_active else 0,
                original_price=meetup.price if meetup.is_early_bird_active else None,
            )
            
            logger.info(f"임시 예약 생성 성공 - 밋업: {meetup.name}, 사용자: {user.username}, 주문: {order.order_number}")
            return True, "임시 예약이 생성되었습니다.", order
            
    except Exception as e:
        logger.error(f"임시 예약 생성 실패 - 밋업: {meetup.name}, 사용자: {user.username}, 오류: {str(e)}")
        return False, "예약 처리 중 오류가 발생했습니다.", None


def extend_reservation(order, additional_seconds=None):
    """
    임시 예약 시간 연장
    
    Args:
        order: MeetupOrder 인스턴스
        additional_seconds: 추가 연장 시간 (초), None이면 사이트 설정값 사용
    
    Returns:
        bool: 연장 성공 여부
    """
    from django.utils import timezone
    from myshop.models import SiteSettings
    
    try:
        if not order.is_temporary_reserved or order.status != 'pending':
            return False
        
        if additional_seconds is None:
            site_settings = SiteSettings.get_settings()
            additional_seconds = site_settings.meetup_countdown_seconds
        
        # 예약 시간 연장
        order.reservation_expires_at = timezone.now() + timezone.timedelta(seconds=additional_seconds)
        order.save()
        
        logger.info(f"예약 시간 연장 - 주문: {order.order_number}, 새 만료시간: {order.reservation_expires_at}")
        return True
        
    except Exception as e:
        logger.error(f"예약 시간 연장 실패 - 주문: {order.order_number}, 오류: {str(e)}")
        return False


def cancel_expired_reservations():
    """
    만료된 임시 예약들을 자동 취소
    
    Returns:
        int: 취소된 예약 수
    """
    from django.utils import timezone
    from .models import MeetupOrder
    
    try:
        now = timezone.now()
        expired_orders = MeetupOrder.objects.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__lt=now
        )
        
        cancelled_count = 0
        for order in expired_orders:
            order.status = 'cancelled'
            order.auto_cancelled_reason = '예약 시간 만료'
            order.is_temporary_reserved = False
            order.save()
            cancelled_count += 1
            logger.info(f"만료된 예약 자동 취소 - 주문: {order.order_number}")
        
        if cancelled_count > 0:
            logger.info(f"총 {cancelled_count}개의 만료된 예약을 자동 취소했습니다.")
        
        return cancelled_count
        
    except Exception as e:
        logger.error(f"만료된 예약 자동 취소 실패 - 오류: {str(e)}")
        return 0


def confirm_reservation(order):
    """
    임시 예약을 확정 상태로 변경
    
    Args:
        order: MeetupOrder 인스턴스
    
    Returns:
        bool: 확정 성공 여부
    """
    from django.utils import timezone
    
    try:
        logger.info(f"예약 확정 시작 - 주문: {order.order_number}, 상태: {order.status}, 임시예약: {order.is_temporary_reserved}")
        
        if order.status != 'pending':
            logger.error(f"예약 확정 실패 - 잘못된 주문 상태: {order.status} (주문: {order.order_number})")
            return False
        
        if not order.is_temporary_reserved:
            logger.error(f"예약 확정 실패 - 임시예약 상태가 아님: {order.is_temporary_reserved} (주문: {order.order_number})")
            return False
        
        # 예약 확정
        order.status = 'confirmed'
        order.is_temporary_reserved = False
        order.confirmed_at = timezone.now()
        order.paid_at = timezone.now()
        order.reservation_expires_at = None  # 확정되면 만료시간 제거
        order.save()
        
        logger.info(f"예약 확정 완료 - 주문: {order.order_number}")
        return True
        
    except Exception as e:
        logger.error(f"예약 확정 실패 - 주문: {order.order_number}, 오류: {str(e)}", exc_info=True)
        return False


def release_reservation(order, reason="사용자 취소"):
    """
    임시 예약 해제 (정원 반납)
    
    Args:
        order: MeetupOrder 인스턴스
        reason: 취소 사유
    
    Returns:
        bool: 해제 성공 여부
    """
    try:
        if order.status != 'pending' or not order.is_temporary_reserved:
            return False
        
        # 예약 해제
        order.status = 'cancelled'
        order.auto_cancelled_reason = reason
        order.is_temporary_reserved = False
        order.reservation_expires_at = None
        order.save()
        
        logger.info(f"예약 해제 완료 - 주문: {order.order_number}, 사유: {reason}")
        return True
        
    except Exception as e:
        logger.error(f"예약 해제 실패 - 주문: {order.order_number}, 오류: {str(e)}")
        return False 