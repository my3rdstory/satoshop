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
def meetup_free_participant_info(request, store_id, meetup_id):
    """무료 밋업 참가자 정보 입력 페이지"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store)
        
        # 활성화된 밋업인지 확인
        if not meetup.is_active:
            messages.error(request, '비활성화된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 임시 중단된 밋업인지 확인
        if meetup.is_temporarily_closed:
            messages.error(request, '일시적으로 참가 신청이 중단된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 무료 밋업인지 확인
        if not meetup.is_free:
            messages.error(request, '이 밋업은 유료 밋업입니다. 일반 신청 페이지를 이용해주세요.')
            return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)
        
        # 정원 확인
        if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
            messages.error(request, '밋업 신청이 마감되었습니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 무료 밋업은 중복 참가 허용 - 기존 참가 이력 확인만
        existing_orders = MeetupOrder.objects.filter(
            meetup=meetup,
            user=request.user,
            status__in=['confirmed', 'completed']
        ).order_by('-created_at')
        
        # POST 요청 처리 (참가자 정보 입력 후 바로 주문 생성 및 완료)
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # 정원 재확인 (동시성 이슈 방지)
                    if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
                        messages.error(request, '죄송합니다. 방금 전에 밋업 신청이 마감되었습니다.')
                        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
                    
                    # 참가자 정보 수집
                    participant_name = request.POST.get('participant_name', '').strip()
                    participant_email = request.POST.get('participant_email', '').strip()
                    participant_phone = request.POST.get('participant_phone', '').strip()
                    
                    # 필수 정보 검증
                    if not participant_name:
                        messages.error(request, '참가자 이름을 입력해주세요.')
                        return render(request, 'meetup/meetup_free_participant_info.html', {
                            'store': store,
                            'meetup': meetup,
                            'error_occurred': True
                        })
                    
                    if not participant_email:
                        messages.error(request, '이메일을 입력해주세요.')
                        return render(request, 'meetup/meetup_free_participant_info.html', {
                            'store': store,
                            'meetup': meetup,
                            'error_occurred': True
                        })
                    
                    # 바로 주문 생성 및 확정
                    order = MeetupOrder.objects.create(
                        meetup=meetup,
                        user=request.user,
                        participant_name=participant_name,
                        participant_email=participant_email,
                        participant_phone=participant_phone,
                        base_price=0,
                        options_price=0,
                        total_price=0,
                        status='confirmed',
                        is_temporary_reserved=False,
                        confirmed_at=timezone.now(),
                        paid_at=timezone.now()
                    )
                    
                    # 이메일 발송
                    try:
                        from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                        
                        # 주인장에게 알림 이메일
                        send_meetup_notification_email(order)
                        
                        # 참가자에게 확인 이메일
                        send_meetup_participant_confirmation_email(order)
                            
                    except Exception:
                        pass  # 이메일 발송 실패는 무시하고 진행
                    
                    messages.success(request, f'"{meetup.name}" 밋업 참가 신청이 완료되었습니다!')
                    return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=order.id)
                    
            except Exception:
                messages.error(request, '참가 신청 처리 중 오류가 발생했습니다.')
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # GET 요청 처리 (페이지 표시)
        context = {
            'store': store,
            'meetup': meetup,
            'existing_orders': existing_orders,
        }
        
        return render(request, 'meetup/meetup_free_participant_info.html', context)
        
    except Store.DoesNotExist:
        messages.error(request, '존재하지 않는 스토어입니다.')
        return redirect('store:store_list')
    except Exception as e:
        messages.error(request, '페이지 로드 중 오류가 발생했습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)

@login_required
def meetup_free_checkout(request, store_id, meetup_id):
    """무료 밋업 전용 체크아웃 페이지 - 바로 확정"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store)
        
        # 활성화된 밋업인지 확인
        if not meetup.is_active:
            messages.error(request, '비활성화된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 임시 중단된 밋업인지 확인
        if meetup.is_temporarily_closed:
            messages.error(request, '일시적으로 참가 신청이 중단된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 무료 밋업인지 확인
        if not meetup.is_free:
            messages.error(request, '이 밋업은 유료 밋업입니다. 일반 결제 페이지를 이용해주세요.')
            return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)
        
        # 정원 확인
        if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
            messages.error(request, '밋업 신청이 마감되었습니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
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
        
        # 세션에서 참가자 정보 가져오기
        participant_info = request.session.get(f'free_participant_info_{meetup_id}')
        if not participant_info:
            messages.warning(request, '참가자 정보를 먼저 입력해주세요.')
            return redirect('meetup:meetup_free_participant_info', store_id=store_id, meetup_id=meetup_id)

        # POST 요청 처리 (무료 참가 신청 완료 - 바로 확정)
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # 정원 재확인 (동시성 이슈 방지)
                    if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
                        messages.error(request, '죄송합니다. 방금 전에 밋업 신청이 마감되었습니다.')
                        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
                    
                    # 세션의 참가자 정보로 주문 생성
                    order = MeetupOrder.objects.create(
                        meetup=meetup,
                        user=request.user,
                        participant_name=participant_info['participant_name'],
                        participant_email=participant_info['participant_email'],
                        participant_phone=participant_info.get('participant_phone', ''),
                        base_price=0,
                        options_price=0,
                        total_price=0,
                        status='confirmed',
                        is_temporary_reserved=False,
                        confirmed_at=timezone.now(),
                        paid_at=timezone.now()
                    )
                    
                    # 세션에서 참가자 정보 삭제 (더 이상 필요 없음)
                    if f'free_participant_info_{meetup_id}' in request.session:
                        del request.session[f'free_participant_info_{meetup_id}']
                    
                    # 이메일 발송
                    try:
                        from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                        
                        # 주인장에게 알림 이메일
                        send_meetup_notification_email(order)
                        
                        # 참가자에게 확인 이메일
                        send_meetup_participant_confirmation_email(order)
                            
                    except Exception:
                        pass  # 이메일 발송 실패는 무시하고 진행
                    
                    messages.success(request, f'"{meetup.name}" 밋업 참가 신청이 완료되었습니다!')
                    return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=order.id)
                    
            except Exception:
                messages.error(request, '참가 신청 처리 중 오류가 발생했습니다.')
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # GET 요청 처리 (페이지 표시)
        context = {
            'store': store,
            'meetup': meetup,
            'participant_info': participant_info,
        }
        
        return render(request, 'meetup/meetup_free_checkout.html', context)
        
    except Store.DoesNotExist:
        messages.error(request, '존재하지 않는 스토어입니다.')
        return redirect('store:store_list')
    except Exception:
        messages.error(request, '페이지 로드 중 오류가 발생했습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id) 