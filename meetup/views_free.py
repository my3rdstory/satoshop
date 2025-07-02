from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from stores.models import Store
from .models import Meetup, MeetupOrder
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@login_required
def meetup_free_checkout(request, store_id, meetup_id):
    """무료 밋업 전용 체크아웃 페이지"""
    logger.info(f"무료 체크아웃 접근: store_id={store_id}, meetup_id={meetup_id}, user={request.user.id}")
    
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store)
        
        logger.info(f"Store와 Meetup 조회 성공: store={store.store_name}, meetup={meetup.name}, is_free={meetup.is_free}")
        
        # 활성화된 밋업인지 확인
        if not meetup.is_active:
            logger.warning(f"비활성화된 밋업 접근: {meetup_id}")
            messages.error(request, '비활성화된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 임시 중단된 밋업인지 확인
        if meetup.is_temporarily_closed:
            logger.warning(f"임시 중단된 밋업 접근: {meetup_id}")
            messages.error(request, '일시적으로 참가 신청이 중단된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 무료 밋업인지 확인
        if not meetup.is_free:
            logger.warning(f"유료 밋업에 무료 체크아웃 접근 시도 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            messages.error(request, '이 밋업은 유료 밋업입니다. 일반 결제 페이지를 이용해주세요.')
            return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)
        
        logger.info(f"모든 검증 통과 - 무료 밋업 체크아웃 진행")
        
        # 기존 주문 확인
        existing_order = MeetupOrder.objects.filter(
            meetup=meetup,
            user=request.user,
            status__in=['pending', 'confirmed', 'completed']
        ).first()
        
        # 기존 주문이 없으면 새로 생성 (GET 요청 시)
        if not existing_order and request.method == 'GET':
            logger.info(f"무료 밋업 새 주문 생성 시작 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            
            try:
                # 사이트 설정에서 카운트다운 시간 가져오기
                from myshop.models import SiteSettings
                site_settings = SiteSettings.get_settings()
                
                # 새 주문 생성
                reservation_expires_at = timezone.now() + timedelta(seconds=site_settings.meetup_countdown_seconds)
                
                existing_order = MeetupOrder.objects.create(
                    meetup=meetup,
                    user=request.user,
                    participant_name=request.user.get_full_name() or request.user.username,
                    participant_email=request.user.email,
                    base_price=0,
                    options_price=0,
                    total_price=0,
                    status='pending',
                    is_temporary_reserved=True,
                    reservation_expires_at=reservation_expires_at
                )
                
                logger.info(f"무료 밋업 새 주문 생성 완료 - 주문: {existing_order.order_number}")
                
            except Exception as e:
                logger.error(f"무료 밋업 주문 생성 오류: {str(e)}", exc_info=True)
                messages.error(request, '주문 생성 중 오류가 발생했습니다.')
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        elif not existing_order:
            logger.warning(f"무료 체크아웃 페이지 접근했지만 주문이 없음 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            messages.error(request, '주문 정보를 찾을 수 없습니다. 다시 참가 신청을 해주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 이미 확정된 주문인 경우
        if existing_order.status in ['confirmed', 'completed']:
            messages.info(request, '이미 참가 신청이 완료된 밋업입니다.')
            return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=existing_order.id)
        
        # POST 요청 처리 (무료 참가 신청 완료)
        if request.method == 'POST':
            logger.info(f"무료 밋업 참가 확정 시작 - 주문: {existing_order.order_number}")
            
            from .services import confirm_reservation
            confirm_success = confirm_reservation(existing_order)
            
            if not confirm_success:
                logger.error(f"무료 밋업 참가 확정 실패 - 주문: {existing_order.order_number}")
                messages.error(request, '참가 확정 처리 중 오류가 발생했습니다.')
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
            
            logger.info(f"무료 밋업 참가 확정 성공 - 주문: {existing_order.order_number}")
            
            # 이메일 발송
            try:
                from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                
                # 주인장에게 알림 이메일
                owner_email_sent = send_meetup_notification_email(existing_order)
                if owner_email_sent:
                    logger.info(f"[MEETUP_EMAIL] 무료 밋업 주인장 알림 이메일 발송 성공: {existing_order.order_number}")
                
                # 참가자에게 확인 이메일
                participant_email_sent = send_meetup_participant_confirmation_email(existing_order)
                if participant_email_sent:
                    logger.info(f"[MEETUP_EMAIL] 무료 밋업 참가자 확인 이메일 발송 성공: {existing_order.order_number}")
                    
            except Exception as e:
                logger.error(f"[MEETUP_EMAIL] 무료 밋업 이메일 발송 오류: {existing_order.order_number}, {str(e)}")
            
            messages.success(request, f'"{meetup.name}" 밋업 참가 신청이 완료되었습니다!')
            return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=existing_order.id)
        
        # GET 요청 처리 (페이지 표시)
        # 사이트 설정에서 카운트다운 시간 가져오기
        from myshop.models import SiteSettings
        site_settings = SiteSettings.get_settings()
        
        # 예약 만료 시간 계산
        reservation_expires_at = None
        countdown_seconds = 0
        
        if existing_order.reservation_expires_at:
            if timezone.now() < existing_order.reservation_expires_at:
                reservation_expires_at = existing_order.reservation_expires_at.isoformat()
                countdown_seconds = int((existing_order.reservation_expires_at - timezone.now()).total_seconds())
            else:
                # 예약 시간 만료
                logger.info(f"무료 밋업 예약 시간 만료 - 주문: {existing_order.order_number}")
                messages.error(request, '예약 시간이 만료되었습니다. 다시 참가 신청을 해주세요.')
                existing_order.delete()
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        context = {
            'store': store,
            'meetup': meetup,
            'order': existing_order,
            'countdown_seconds': countdown_seconds,
            'reservation_expires_at': reservation_expires_at,
            'site_countdown_seconds': site_settings.meetup_countdown_seconds,
        }
        
        logger.info(f"무료 체크아웃 템플릿 렌더링: meetup_free_checkout.html")
        return render(request, 'meetup/meetup_free_checkout.html', context)
        
    except Store.DoesNotExist:
        logger.error(f"존재하지 않는 스토어 접근 시도 - store_id: {store_id}")
        messages.error(request, '존재하지 않는 스토어입니다.')
        return redirect('store:store_list')
    except Exception as e:
        logger.error(f"무료 밋업 체크아웃 페이지 오류: {str(e)}")
        messages.error(request, '페이지 로드 중 오류가 발생했습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id) 