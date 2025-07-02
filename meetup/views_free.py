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
    """무료 밋업 전용 체크아웃 페이지 - 바로 확정"""
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
        
        # 정원 확인
        if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
            logger.warning(f"무료 밋업 정원 마감 - 밋업: {meetup_id}")
            messages.error(request, '밋업 신청이 마감되었습니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        logger.info(f"모든 검증 통과 - 무료 밋업 체크아웃 진행")
        
        # 기존 주문 확인
        existing_order = MeetupOrder.objects.filter(
            meetup=meetup,
            user=request.user,
            status__in=['confirmed', 'completed']
        ).first()
        
        # 이미 확정된 주문인 경우
        if existing_order:
            messages.info(request, '이미 참가 신청이 완료된 밋업입니다.')
            return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=existing_order.id)
        
        # POST 요청 처리 (무료 참가 신청 완료 - 바로 확정)
        if request.method == 'POST':
            logger.info(f"무료 밋업 참가 확정 시작 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            
            try:
                with transaction.atomic():
                    # 정원 재확인 (동시성 이슈 방지)
                    if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
                        logger.warning(f"무료 밋업 정원 마감 (재확인) - 밋업: {meetup_id}")
                        messages.error(request, '죄송합니다. 방금 전에 밋업 신청이 마감되었습니다.')
                        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
                    
                    # 바로 확정된 주문 생성
                    order = MeetupOrder.objects.create(
                        meetup=meetup,
                        user=request.user,
                        participant_name=request.user.get_full_name() or request.user.username,
                        participant_email=request.user.email,
                        base_price=0,
                        options_price=0,
                        total_price=0,
                        status='confirmed',
                        is_temporary_reserved=False,
                        confirmed_at=timezone.now(),
                        paid_at=timezone.now()
                    )
                    
                    logger.info(f"무료 밋업 참가 확정 성공 - 주문: {order.order_number}")
                    
                    # 이메일 발송
                    try:
                        from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                        
                        # 주인장에게 알림 이메일
                        owner_email_sent = send_meetup_notification_email(order)
                        if owner_email_sent:
                            logger.info(f"[MEETUP_EMAIL] 무료 밋업 주인장 알림 이메일 발송 성공: {order.order_number}")
                        
                        # 참가자에게 확인 이메일
                        participant_email_sent = send_meetup_participant_confirmation_email(order)
                        if participant_email_sent:
                            logger.info(f"[MEETUP_EMAIL] 무료 밋업 참가자 확인 이메일 발송 성공: {order.order_number}")
                            
                    except Exception as e:
                        logger.error(f"[MEETUP_EMAIL] 무료 밋업 이메일 발송 오류: {order.order_number}, {str(e)}")
                    
                    messages.success(request, f'"{meetup.name}" 밋업 참가 신청이 완료되었습니다!')
                    return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=order.id)
                    
            except Exception as e:
                logger.error(f"무료 밋업 주문 생성 오류: {str(e)}", exc_info=True)
                messages.error(request, '참가 신청 처리 중 오류가 발생했습니다.')
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # GET 요청 처리 (페이지 표시)
        context = {
            'store': store,
            'meetup': meetup,
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