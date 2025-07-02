from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from stores.models import Store
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice, MeetupOrder, MeetupOrderOption
from .forms import MeetupForm
from ln_payment.blink_service import get_blink_service_for_store
import json
import logging
from django.core.paginator import Paginator
from django.db import models

logger = logging.getLogger(__name__)

def meetup_list(request, store_id):
    """밋업 목록 (공개/관리자 뷰)"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        raise Http404("스토어를 찾을 수 없습니다.")
    
    # 스토어 소유자인지 확인하여 관리자/공개 뷰 결정
    is_public_view = request.user != store.owner
    
    # 밋업 목록 조회
    meetups_queryset = Meetup.objects.filter(
        store=store, 
        deleted_at__isnull=True
    ).prefetch_related('images')
    
    # 공개 뷰에서는 활성화된 밋업만 표시
    if is_public_view:
        meetups_queryset = meetups_queryset.filter(
            is_active=True,
            is_temporarily_closed=False
        )
    
    meetups = meetups_queryset.order_by('-created_at')
    
    context = {
        'store': store,
        'meetups': meetups,
        'is_public_view': is_public_view,
    }
    
    return render(request, 'meetup/meetup_list.html', context)

def public_meetup_list(request, store_id):
    """일반 사용자용 밋업 목록"""
    try:
        store = Store.objects.get(store_id=store_id, is_active=True, deleted_at__isnull=True)
    except Store.DoesNotExist:
        # 스토어가 존재하지 않는 경우
        context = {
            'store_id': store_id,
            'error_type': 'store_not_found'
        }
        return render(request, 'meetup/store_not_found.html', context, status=404)
    
    meetups = Meetup.objects.filter(
        store=store, 
        is_active=True, 
        is_temporarily_closed=False,
        deleted_at__isnull=True
    ).prefetch_related('images').order_by('-created_at')
    
    context = {
        'store': store,
        'meetups': meetups,
        'is_public_view': True,
    }
    return render(request, 'meetup/meetup_list.html', context)

@login_required
def add_meetup(request, store_id):
    """밋업 추가"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        form = MeetupForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 밋업 생성
                    meetup = form.save(commit=False)
                    meetup.store = store
                    meetup.save()
                    
                    # 이미지 업로드 처리
                    images = request.FILES.getlist('images')
                    if images:
                        # 밋업당 1장만 허용
                        image_file = images[0]
                        try:
                            from storage.utils import upload_meetup_image
                            result = upload_meetup_image(image_file, meetup, request.user)
                            
                            if result['success']:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.info(f"밋업 이미지 업로드 성공: {image_file.name}")
                            else:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"밋업 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                                messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"밋업 이미지 처리 오류: {e}", exc_info=True)
                            messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                    
                    # 옵션 처리 (JavaScript에서 전송된 데이터)
                    options_data = request.POST.get('options_json')
                    if options_data:
                        try:
                            options = json.loads(options_data)
                            for option_data in options:
                                option = MeetupOption.objects.create(
                                    meetup=meetup,
                                    name=option_data.get('name', ''),
                                    is_required=option_data.get('is_required', False),
                                    order=option_data.get('order', 0)
                                )
                                
                                # 선택지 생성
                                for choice_data in option_data.get('choices', []):
                                    MeetupChoice.objects.create(
                                        option=option,
                                        name=choice_data.get('name', ''),
                                        additional_price=choice_data.get('additional_price', 0),
                                        order=choice_data.get('order', 0)
                                    )
                        except json.JSONDecodeError:
                            pass  # 옵션 데이터 파싱 오류는 무시하고 계속 진행
                    
                    messages.success(request, f'"{meetup.name}" 밋업이 성공적으로 추가되었습니다.')
                    return redirect('meetup:meetup_list', store_id=store_id)
                    
            except Exception as e:
                messages.error(request, '밋업 추가 중 오류가 발생했습니다. 다시 시도해주세요.')
                print(f"Error creating meetup: {e}")  # 디버그용
    else:
        form = MeetupForm()
    
    context = {
        'store': store,
        'form': form,
    }
    
    return render(request, 'meetup/meetup_add.html', context)

def meetup_detail(request, store_id, meetup_id):
    """밋업 상세"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    # 공개 뷰에서는 비활성화되거나 일시중단된 밋업만 접근 차단
    # 종료된 밋업이나 정원마감된 밋업은 상세 페이지 접근 허용
    if request.user != store.owner:
        if not meetup.is_active or meetup.is_temporarily_closed:
            raise Http404("밋업을 찾을 수 없습니다.")
    
    # 밋업 옵션 조회
    meetup_options = meetup.options.prefetch_related('choices').order_by('order')
    
    context = {
        'store': store,
        'meetup': meetup,
        'meetup_options': meetup_options,
        'meetup_id': meetup_id,
    }
    
    return render(request, 'meetup/meetup_detail.html', context)

@login_required
def edit_meetup_unified(request, store_id, meetup_id):
    """밋업 통합수정"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    if request.method == 'POST':
        form = MeetupForm(data=request.POST, files=request.FILES, instance=meetup)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 밋업 수정
                    meetup = form.save()
                    
                    # 새 이미지 업로드 처리
                    images = request.FILES.getlist('images')
                    if images:
                        # 기존 이미지가 있으면 삭제 (밋업당 1장만 허용)
                        existing_images = meetup.images.all()
                        if existing_images.exists():
                            for existing_image in existing_images:
                                # S3에서 파일 삭제
                                try:
                                    from storage.utils import delete_file_from_s3
                                    delete_file_from_s3(existing_image.file_path)
                                except Exception as e:
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.warning(f"S3 파일 삭제 실패: {e}")
                                # DB에서 삭제
                                existing_image.delete()
                        
                        # 새 이미지 업로드 (첫 번째 이미지만)
                        image_file = images[0]
                        try:
                            from storage.utils import upload_meetup_image
                            result = upload_meetup_image(image_file, meetup, request.user)
                            
                            if result['success']:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.info(f"밋업 이미지 업로드 성공: {image_file.name}")
                            else:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"밋업 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                                messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"밋업 이미지 처리 오류: {e}", exc_info=True)
                            messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                    
                    # 옵션 처리 (기존 옵션 삭제 후 재생성)
                    options_data = request.POST.get('options_json')
                    if options_data:
                        try:
                            # 기존 옵션 삭제
                            meetup.options.all().delete()
                            
                            options = json.loads(options_data)
                            for option_data in options:
                                option = MeetupOption.objects.create(
                                    meetup=meetup,
                                    name=option_data.get('name', ''),
                                    is_required=option_data.get('is_required', False),
                                    order=option_data.get('order', 0)
                                )
                                
                                # 선택지 생성
                                for choice_data in option_data.get('choices', []):
                                    MeetupChoice.objects.create(
                                        option=option,
                                        name=choice_data.get('name', ''),
                                        additional_price=choice_data.get('additional_price', 0),
                                        order=choice_data.get('order', 0)
                                    )
                        except json.JSONDecodeError:
                            pass  # 옵션 데이터 파싱 오류는 무시하고 계속 진행
                    
                    messages.success(request, f'"{meetup.name}" 밋업이 성공적으로 수정되었습니다.')
                    return redirect('meetup:meetup_list', store_id=store_id)
                    
            except Exception as e:
                messages.error(request, '밋업 수정 중 오류가 발생했습니다. 다시 시도해주세요.')
                print(f"Error updating meetup: {e}")  # 디버그용
    else:
        form = MeetupForm(instance=meetup)
    
    # 기존 옵션 데이터를 JSON으로 변환
    existing_options = []
    for option in meetup.options.all():
        option_data = {
            'name': option.name,
            'is_required': option.is_required,
            'order': option.order,
            'choices': []
        }
        for choice in option.choices.all():
            choice_data = {
                'name': choice.name,
                'additional_price': choice.additional_price,
                'order': choice.order
            }
            option_data['choices'].append(choice_data)
        existing_options.append(option_data)
    
    context = {
        'store': store,
        'meetup': meetup,
        'form': form,
        'existing_options': json.dumps(existing_options),
        'is_edit': True,
    }
    
    return render(request, 'meetup/meetup_edit.html', context)

@login_required
def manage_meetup(request, store_id, meetup_id):
    """밋업 관리"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    context = {
        'store': store,
        'meetup': meetup,
        'meetup_id': meetup_id,
    }
    
    return render(request, 'meetup/meetup_manage.html', context)

def meetup_checkout(request, store_id, meetup_id):
    """밋업 체크아웃 - 바로 주문 생성하고 결제 페이지로"""
    import json
    
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True,
        is_active=True
    )
    
    # 참가 신청이 불가능한 밋업은 체크아웃 불가
    if not meetup.can_participate:
        if meetup.is_expired:
            messages.error(request, '이미 종료된 밋업입니다.')
        elif meetup.is_temporarily_closed:
            messages.error(request, '일시중단된 밋업입니다.')
        elif meetup.is_full:
            messages.error(request, '정원이 마감된 밋업입니다.')
        else:
            messages.error(request, '현재 참가 신청이 불가능한 밋업입니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
    # GET 요청인 경우 참가자 정보 입력 페이지 표시
    if request.method == 'GET':
        # URL 파라미터에서 선택된 옵션 정보 가져오기
        selected_options_param = request.GET.get('selected_options')
        selected_options = {}
        
        if selected_options_param:
            try:
                selected_options = json.loads(selected_options_param)
            except (json.JSONDecodeError, ValueError):
                # 잘못된 JSON이면 빈 딕셔너리로 초기화
                selected_options = {}
        
        # 필수 옵션 정보 수집
        required_option_ids = list(meetup.options.filter(is_required=True).values_list('id', flat=True))
        
        # 할인 금액 계산 (조기등록 할인)
        discount_amount = 0
        if meetup.is_early_bird_active:
            discount_amount = meetup.price - meetup.current_price
        
        context = {
            'store': store,
            'meetup': meetup,
            'selected_options_json': json.dumps(selected_options) if selected_options else '{}',
            'required_option_ids': json.dumps(required_option_ids) if required_option_ids else '[]',
            'discount_amount': discount_amount,
        }
        return render(request, 'meetup/meetup_participant_info.html', context)
    
    # POST 요청인 경우 주문 생성 처리
    # 로그인한 사용자의 경우 기존 대기중인 주문 확인
    existing_order = None
    if request.user.is_authenticated:
        existing_order = MeetupOrder.objects.filter(
            meetup=meetup,
            user=request.user,
            status__in=['pending', 'cancelled']  # 취소된 주문도 포함
        ).first()
    
    if existing_order:
        # 기존 주문이 30분 이내인 경우 해당 주문으로 이동
        from datetime import timedelta
        if timezone.now() - existing_order.created_at < timedelta(minutes=30):
            # 취소된 주문은 pending 상태로 복원
            if existing_order.status == 'cancelled':
                existing_order.status = 'pending'
                existing_order.payment_hash = ''
                existing_order.payment_request = ''
                existing_order.save()
            
            # 무료 밋업인 경우 바로 참가 확정 처리
            if existing_order.total_price == 0:
                existing_order.status = 'confirmed'
                existing_order.paid_at = timezone.now()
                existing_order.confirmed_at = timezone.now()
                existing_order.save()
                
                # 🎉 무료 밋업 참가 확정 이메일 발송 (주인장에게 + 참가자에게)
                try:
                    from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                    
                    # 주인장에게 알림 이메일
                    owner_email_sent = send_meetup_notification_email(existing_order)
                    if owner_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 주인장 알림 이메일 발송 성공: {existing_order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 주인장 알림 이메일 발송 조건 미충족: {existing_order.order_number}")
                    
                    # 참가자에게 확인 이메일
                    participant_email_sent = send_meetup_participant_confirmation_email(existing_order)
                    if participant_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 참가자 확인 이메일 발송 성공: {existing_order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 참가자 확인 이메일 발송 조건 미충족: {existing_order.order_number}")
                        
                except Exception as e:
                    # 이메일 발송 실패해도 주문 처리는 계속 진행
                    logger.error(f"[MEETUP_EMAIL] 무료 밋업 이메일 발송 오류: {existing_order.order_number}, {str(e)}")
                    pass
                
                messages.success(request, f'"{meetup.name}" 밋업 참가 신청이 완료되었습니다!')
                return redirect('meetup:meetup_checkout_complete', 
                              store_id=store_id, meetup_id=meetup_id, order_id=existing_order.id)
            
            # 유료 밋업인 경우 결제 페이지로
            # 블링크 서비스 연결 확인
            blink_service = get_blink_service_for_store(store)
            payment_service_available = blink_service is not None
            
            context = {
                'store': store,
                'meetup': meetup,
                'order': existing_order,
                'payment_service_available': payment_service_available,
            }
            
            return render(request, 'meetup/meetup_checkout.html', context)
        else:
            # 만료된 주문은 취소
            existing_order.status = 'cancelled'
            existing_order.save()
    
    # 새 주문 생성
    try:
        with transaction.atomic():
            # 기본 가격 계산
            base_price = meetup.current_price
            options_price = 0
            
            # 선택한 옵션 처리 (POST 데이터에서)
            options_data = request.POST.get('selected_options')
            selected_option_choices = []
            
            if options_data:
                try:
                    selected_options = json.loads(options_data)
                    
                    # 각 옵션의 선택지 가격 계산
                    for option_id, choice_info in selected_options.items():
                        choice_id = choice_info.get('choiceId')
                        choice_price = choice_info.get('price', 0)
                        
                        # 실제 옵션 선택지 검증
                        try:
                            choice = MeetupChoice.objects.get(
                                id=choice_id,
                                option__meetup=meetup,
                                option__id=option_id
                            )
                            # 가격 검증 (보안을 위해)
                            if choice.additional_price == choice_price:
                                options_price += choice_price
                                selected_option_choices.append(choice)
                        except MeetupChoice.DoesNotExist:
                            # 잘못된 선택지는 무시
                            pass
                            
                except (json.JSONDecodeError, KeyError, ValueError):
                    # 잘못된 옵션 데이터는 무시
                    pass
            
            total_price = base_price + options_price
            
            # 할인 정보
            is_early_bird = meetup.is_discounted and meetup.is_early_bird_active
            discount_rate = meetup.public_discount_rate if is_early_bird else 0
            original_price = meetup.price if is_early_bird else None
            
            # 참가자 정보 가져오기
            if request.user.is_authenticated:
                # 로그인한 사용자: 사용자 정보 우선, POST 데이터로 덮어쓰기 가능
                participant_name = request.POST.get('participant_name') or request.user.get_full_name() or request.user.username
                participant_email = request.POST.get('participant_email') or request.user.email
            else:
                # 비회원: POST 데이터에서 필수로 가져오기
                participant_name = request.POST.get('participant_name', '').strip()
                participant_email = request.POST.get('participant_email', '').strip()
                
                if not participant_name or not participant_email:
                    messages.error(request, '참가자 이름과 이메일을 입력해주세요.')
                    return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)
            
            participant_phone = request.POST.get('participant_phone', '').strip()
            
            # 주문 생성
            order = MeetupOrder.objects.create(
                meetup=meetup,
                user=request.user if request.user.is_authenticated else None,
                participant_name=participant_name,
                participant_email=participant_email,
                participant_phone=participant_phone,
                base_price=base_price,
                options_price=options_price,
                total_price=total_price,
                is_early_bird=is_early_bird,
                discount_rate=discount_rate,
                original_price=original_price,
                status='pending'
            )
            
            # 선택한 옵션들을 주문에 연결
            for choice in selected_option_choices:
                MeetupOrderOption.objects.create(
                    order=order,
                    option=choice.option,
                    choice=choice,
                    additional_price=choice.additional_price
                )
            
            # 무료 밋업인 경우 바로 참가 확정 처리
            if total_price == 0:
                order.status = 'confirmed'
                order.paid_at = timezone.now()
                order.confirmed_at = timezone.now()
                order.save()
                
                # 🎉 무료 밋업 참가 확정 이메일 발송 (주인장에게 + 참가자에게)
                try:
                    from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                    
                    # 주인장에게 알림 이메일
                    owner_email_sent = send_meetup_notification_email(order)
                    if owner_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 주인장 알림 이메일 발송 성공: {order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 주인장 알림 이메일 발송 조건 미충족: {order.order_number}")
                    
                    # 참가자에게 확인 이메일
                    participant_email_sent = send_meetup_participant_confirmation_email(order)
                    if participant_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 참가자 확인 이메일 발송 성공: {order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 무료 밋업 참가자 확인 이메일 발송 조건 미충족: {order.order_number}")
                        
                except Exception as e:
                    # 이메일 발송 실패해도 주문 처리는 계속 진행
                    logger.error(f"[MEETUP_EMAIL] 무료 밋업 이메일 발송 오류: {order.order_number}, {str(e)}")
                    pass
                
                messages.success(request, f'"{meetup.name}" 밋업 참가 신청이 완료되었습니다!')
                return redirect('meetup:meetup_checkout_complete', 
                              store_id=store_id, meetup_id=meetup_id, order_id=order.id)
            
            # 유료 밋업인 경우 결제 페이지로
            # 블링크 서비스 연결 확인
            blink_service = get_blink_service_for_store(store)
            payment_service_available = blink_service is not None
            
            context = {
                'store': store,
                'meetup': meetup,
                'order': order,
                'payment_service_available': payment_service_available,
            }
            
            return render(request, 'meetup/meetup_checkout.html', context)
            
    except Exception as e:
        logger.error(f"밋업 주문 생성 오류: {e}", exc_info=True)
        messages.error(request, '주문 생성 중 오류가 발생했습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)

def meetup_checkout_payment(request, store_id, meetup_id, order_id):
    """밋업 결제 페이지"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    order = get_object_or_404(
        MeetupOrder,
        id=order_id,
        meetup=meetup,
        status__in=['pending', 'cancelled']  # 취소된 주문도 포함
    )
    
    # 주문 생성 후 30분 경과 시 만료
    from datetime import timedelta
    if timezone.now() - order.created_at > timedelta(minutes=30):
        order.status = 'cancelled'
        order.save()
        messages.error(request, '주문이 만료되었습니다. 다시 신청해주세요.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
    # 블링크 서비스 연결 확인
    blink_service = get_blink_service_for_store(store)
    payment_service_available = blink_service is not None
    
    context = {
        'store': store,
        'meetup': meetup,
        'order': order,
        'payment_service_available': payment_service_available,
    }
    
    return render(request, 'meetup/meetup_checkout.html', context)

@require_POST
@csrf_exempt
def create_meetup_invoice(request, store_id, meetup_id, order_id):
    """밋업 결제 인보이스 생성"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            status__in=['pending', 'cancelled']  # 취소된 주문도 포함
        )
        
        # 취소된 주문은 pending 상태로 복원
        if order.status == 'cancelled':
            order.status = 'pending'
        
        # 블링크 서비스 가져오기
        blink_service = get_blink_service_for_store(store)
        if not blink_service:
            return JsonResponse({
                'success': False,
                'error': '결제 서비스가 설정되지 않았습니다.'
            })
        
        # 기존 결제 정보 초기화 (재생성 대비)
        order.payment_hash = ''
        order.payment_request = ''
        order.save()
        
        # 인보이스 생성
        amount_sats = order.total_price
        memo = f"{meetup.name}"
        
        result = blink_service.create_invoice(
            amount_sats=amount_sats,
            memo=memo,
            expires_in_minutes=15
        )
        
        if result['success']:
            # 주문에 인보이스 정보 저장
            order.payment_hash = result['payment_hash']
            order.payment_request = result['invoice']
            order.save()
            
            return JsonResponse({
                'success': True,
                'payment_hash': result['payment_hash'],
                'invoice': result['invoice'],
                'amount_sats': order.total_price,
                'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '인보이스 생성에 실패했습니다.')
            })
            
    except Exception as e:
        logger.error(f"밋업 인보이스 생성 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '인보이스 생성 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def check_meetup_payment_status(request, store_id, meetup_id, order_id):
    """밋업 결제 상태 확인"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup
        )
        
        if not order.payment_hash or order.payment_hash.strip() == '':
            return JsonResponse({
                'success': False,
                'error': '결제 정보가 없습니다.'
            })
        
        # 블링크 서비스 가져오기
        blink_service = get_blink_service_for_store(store)
        if not blink_service:
            return JsonResponse({
                'success': False,
                'error': '결제 서비스가 설정되지 않았습니다.'
            })
        
        # 결제 상태 확인
        result = blink_service.check_invoice_status(order.payment_hash)
        
        if result['success']:
            if result['status'] == 'paid':
                # 결제 완료 처리
                with transaction.atomic():
                    order.status = 'confirmed'
                    order.paid_at = timezone.now()
                    order.confirmed_at = timezone.now()
                    order.save()
                
                # 🎉 밋업 참가 확정 이메일 발송 (주인장에게 + 참가자에게)
                try:
                    from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                    
                    # 주인장에게 알림 이메일
                    owner_email_sent = send_meetup_notification_email(order)
                    if owner_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 밋업 알림 이메일 발송 성공: {order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 밋업 알림 이메일 발송 조건 미충족: {order.order_number}")
                    
                    # 참가자에게 확인 이메일
                    participant_email_sent = send_meetup_participant_confirmation_email(order)
                    if participant_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 밋업 참가자 확인 이메일 발송 성공: {order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 밋업 참가자 확인 이메일 발송 조건 미충족: {order.order_number}")
                        
                except Exception as e:
                    # 이메일 발송 실패해도 주문 처리는 계속 진행
                    logger.error(f"[MEETUP_EMAIL] 밋업 이메일 발송 오류: {order.order_number}, {str(e)}")
                    pass
                
                return JsonResponse({
                    'success': True,
                    'paid': True,
                    'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'paid': False
                })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '결제 상태 확인에 실패했습니다.')
            })
            
    except Exception as e:
        logger.error(f"밋업 결제 상태 확인 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '결제 상태 확인 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def cancel_meetup_invoice(request, store_id, meetup_id, order_id):
    """밋업 인보이스 취소"""
    try:
        data = json.loads(request.body)
        payment_hash = data.get('payment_hash')
        
        if not payment_hash:
            return JsonResponse({
                'success': False,
                'error': '결제 해시가 필요합니다.'
            })
        
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            payment_hash=payment_hash
        )
        
        # 주문 취소 및 결제 정보 초기화
        order.status = 'cancelled'
        order.payment_hash = ''
        order.payment_request = ''
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': '결제가 취소되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"밋업 인보이스 취소 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '취소 처리 중 오류가 발생했습니다.'
        })

def meetup_checkout_complete(request, store_id, meetup_id, order_id):
    """밋업 결제 완료"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    order = get_object_or_404(
        MeetupOrder,
        id=order_id,
        meetup=meetup,
        status__in=['confirmed', 'completed']
    )
    
    # 할인 금액 계산 (조기등록 할인)
    discount_amount = 0
    if order.is_early_bird and order.original_price:
        discount_amount = order.original_price - order.base_price
    
    context = {
        'store': store,
        'meetup': meetup,
        'order': order,
        'discount_amount': discount_amount,
    }
    
    return render(request, 'meetup/meetup_checkout_complete.html', context)

def meetup_orders(request, store_id):
    """밋업 주문 내역 (사용자별)"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    # 로그인된 사용자의 주문만 조회
    if request.user.is_authenticated:
        orders = MeetupOrder.objects.filter(
            meetup__store=store,
            user=request.user
        ).select_related('meetup').prefetch_related('selected_options').order_by('-created_at')
    else:
        orders = MeetupOrder.objects.none()
    
    context = {
        'store': store,
        'orders': orders,
    }
    
    return render(request, 'meetup/meetup_orders.html', context)

@login_required
def meetup_status(request, store_id):
    """밋업 현황 페이지"""
    from stores.decorators import store_owner_required
    from django.db import models
    
    # 스토어 소유자 권한 확인
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # 밋업별 참가 통계 계산
    meetups_with_orders = []
    meetups = Meetup.objects.filter(store=store, deleted_at__isnull=True).prefetch_related('images')
    
    for meetup in meetups:
        # 확정된 주문만 집계 (결제 완료된 참가자)
        confirmed_orders = MeetupOrder.objects.filter(
            meetup=meetup,
            status__in=['confirmed', 'completed']
        )
        
        total_participants = confirmed_orders.count()
        total_revenue = confirmed_orders.aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        
        # 통계 정보 추가
        meetup.total_participants = total_participants
        meetup.total_revenue = total_revenue
        meetups_with_orders.append(meetup)
    
    # 매출 순으로 정렬
    meetups_with_orders.sort(key=lambda x: x.total_revenue, reverse=True)
    
    # 전체 통계
    total_meetup_orders = MeetupOrder.objects.filter(
        meetup__store=store, 
        status__in=['confirmed', 'completed']
    ).count()
    total_meetup_revenue = MeetupOrder.objects.filter(
        meetup__store=store, 
        status__in=['confirmed', 'completed']
    ).aggregate(
        total=models.Sum('total_price')
    )['total'] or 0
    total_participants = MeetupOrder.objects.filter(
        meetup__store=store, 
        status__in=['confirmed', 'completed']
    ).count()
    
    context = {
        'store': store,
        'meetups_with_orders': meetups_with_orders,
        'total_meetup_orders': total_meetup_orders,
        'total_meetup_revenue': total_meetup_revenue,
        'total_participants': total_participants,
    }
    
    return render(request, 'meetup/meetup_status.html', context)

@login_required
def meetup_status_detail(request, store_id, meetup_id):
    """밋업별 참가 현황 상세 페이지"""
    from stores.decorators import store_owner_required
    from django.core.paginator import Paginator
    from django.db import models
    
    # 스토어 소유자 권한 확인
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
    
    # 해당 밋업의 주문들 (확정된 것만)
    orders = MeetupOrder.objects.filter(
        meetup=meetup,
        status__in=['confirmed', 'completed']
    ).select_related('user').prefetch_related('selected_options').order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 통계 계산
    total_participants = orders.count()
    total_revenue = orders.aggregate(
        total=models.Sum('total_price')
    )['total'] or 0
    
    # 참석자 통계 계산
    attended_count = orders.filter(attended=True).count()
    attendance_rate = 0
    if total_participants > 0:
        attendance_rate = (attended_count / total_participants) * 100
    
    # 평균 참가비 계산
    average_price = 0
    if total_participants > 0:
        average_price = total_revenue / total_participants
    
    context = {
        'store': store,
        'meetup': meetup,
        'page_obj': page_obj,
        'total_participants': total_participants,
        'total_revenue': total_revenue,
        'average_price': average_price,
        'attended_count': attended_count,
        'attendance_rate': attendance_rate,
    }
    
    return render(request, 'meetup/meetup_status_detail.html', context)

@login_required
@require_POST
@csrf_exempt
def update_attendance(request, store_id, meetup_id):
    """참석 여부 업데이트"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
        
        data = json.loads(request.body)
        order_id = data.get('order_id')
        attended = data.get('attended', False)
        
        if not order_id:
            return JsonResponse({
                'success': False,
                'error': '주문 ID가 필요합니다.'
            })
        
        # 해당 밋업의 주문인지 확인
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            status__in=['confirmed', 'completed']
        )
        
        # 참석 여부 업데이트
        order.attended = attended
        if attended:
            order.attended_at = timezone.now()
        else:
            order.attended_at = None
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': '참석 여부가 업데이트되었습니다.',
            'attended': order.attended,
            'attended_at': order.attended_at.isoformat() if order.attended_at else None
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"참석 여부 업데이트 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '참석 여부 업데이트 중 오류가 발생했습니다.'
        })
