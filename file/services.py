"""
파일 관련 서비스 모듈
"""
import logging
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMessage
from django.utils import timezone
from django.template.loader import render_to_string
from django.template import Context, Template

logger = logging.getLogger(__name__)


def send_file_purchase_notification_email(file_order):
    """
    파일 구매 확정 시 스토어 주인장에게 이메일 발송
    
    Args:
        file_order: FileOrder 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 중복 이메일 발송 방지
        from django.core.cache import cache
        email_cache_key = f"file_owner_email_sent_{file_order.order_number}"
        
        if cache.get(email_cache_key):
            logger.debug(f"파일 주인장 이메일 {file_order.order_number}: 이미 발송됨")
            return False
        
        # 스토어 이메일 설정 확인
        store = file_order.digital_file.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"파일 {file_order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"파일 {file_order.order_number}: Gmail 설정 불완전")
            return False
            
        # 수신 이메일 주소 확인
        recipient_email = store.owner_email
        
        if not recipient_email:
            logger.debug(f"파일 {file_order.order_number}: 스토어 주인장 이메일이 설정되지 않음")
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
        
        # 이메일 내용 생성
        subject = f'[{store.store_name}] 새로운 파일 구매 - {file_order.order_number}'
        
        # 구매 내역 생성
        purchase_content = f"""
▣ 파일 구매 확정 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
파일명: {file_order.digital_file.name}
주문번호: {file_order.order_number}
구매자: {file_order.user.username} ({file_order.user.email})
구매 확정일시: {file_order.confirmed_at.strftime('%Y년 %m월 %d일 %H시 %M분') if file_order.confirmed_at else '미확정'}
"""
        
        if file_order.price > 0:
            purchase_content += f"결제금액: {file_order.price:,.0f} sats\n"
            if file_order.is_discounted:
                purchase_content += f"할인율: {file_order.discount_rate}%\n"
        else:
            purchase_content += "가격: 무료\n"
        
        message = f"""안녕하세요, {store.owner_name}님!

{store.store_name}에서 판매 중인 "{file_order.digital_file.name}" 파일이 새로 구매되었습니다.

아래는 구매자 상세 정보입니다:

{purchase_content}

---
이 이메일은 {store.store_name}의 자동 알림 시스템에서 발송되었습니다.

감사합니다!
SatoShop 팀"""
        
        # 이메일 발송
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=f'{store.email_from_display} <{store.email_host_user}>',
            to=[recipient_email],
            connection=backend
        )
        
        email.send()
        
        # 이메일 발송 성공 기록 (중복 방지용)
        cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"파일 구매 알림 이메일 발송 성공 - 주문: {file_order.order_number}, 수신: {recipient_email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"파일 구매 알림 이메일 발송 실패 - 주문: {file_order.order_number}, 오류: {str(e)}")
        return False


def send_file_buyer_confirmation_email(file_order):
    """
    파일 구매 확정 시 구매자에게 확인 이메일 발송
    
    Args:
        file_order: FileOrder 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 구매자 이메일 주소 확인
        if not file_order.user.email:
            logger.debug(f"파일 {file_order.order_number}: 구매자 이메일 주소가 없음")
            return False
        
        # 중복 이메일 발송 방지
        from django.core.cache import cache
        email_cache_key = f"file_buyer_email_sent_{file_order.order_number}"
        
        if cache.get(email_cache_key):
            logger.debug(f"파일 구매자 이메일 {file_order.order_number}: 이미 발송됨")
            return False
        
        # 스토어 이메일 설정 확인
        store = file_order.digital_file.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"파일 구매자 이메일 {file_order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"파일 구매자 이메일 {file_order.order_number}: Gmail 설정 불완전")
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
        
        # 이메일 내용 생성
        subject = f'[{store.store_name}] "{file_order.digital_file.name}" 파일 구매 확정 - {file_order.order_number}'
        
        # 다운로드 정보
        download_info = ""
        if file_order.digital_file.download_expiry_days:
            download_info = f"\n⚠️ 다운로드 유효기간: 구매일로부터 {file_order.digital_file.download_expiry_days}일"
        
        # 구매 완료 메시지
        custom_message = ""
        if file_order.digital_file.purchase_message:
            custom_message = f"\n\n▣ 판매자 안내사항\n{file_order.digital_file.purchase_message}"
        
        message = f"""안녕하세요, {file_order.user.username}님!

"{file_order.digital_file.name}" 파일 구매가 성공적으로 완료되었습니다. 🎉

▣ 구매 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
주문번호: {file_order.order_number}
파일명: {file_order.digital_file.name}
판매자: {store.store_name}
구매일시: {file_order.confirmed_at.strftime('%Y년 %m월 %d일 %H시 %M분') if file_order.confirmed_at else ''}
{download_info}

▣ 다운로드 방법
마이페이지에서 구매한 파일을 다운로드하실 수 있습니다.
{custom_message}

감사합니다,
{store.store_name} & SatoShop 팀"""
        
        # 이메일 발송
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=f'{store.email_from_display} <{store.email_host_user}>',
            to=[file_order.user.email],
            connection=backend
        )
        
        email.send()
        
        # 이메일 발송 성공 기록 (중복 방지용)
        cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"파일 구매자 확인 이메일 발송 성공 - 주문: {file_order.order_number}, 수신: {file_order.user.email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"파일 구매자 확인 이메일 발송 실패 - 주문: {file_order.order_number}, 오류: {str(e)}")
        return False