from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_http_methods
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
from datetime import timedelta
from decimal import Decimal, InvalidOperation

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

@login_required
def meetup_checkout(request, store_id, meetup_id):
    """밋업 체크아웃 - 임시 예약 생성 후 참가자 정보 입력 페이지로"""
    import json
    from .services import create_temporary_reservation, release_reservation
    
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True,
        is_active=True
    )
    
    # 기존 진행 중인 주문 확인
    existing_order = MeetupOrder.objects.filter(
        meetup=meetup,
        user=request.user,
        status='pending',
        is_temporary_reserved=True
    ).first()
    
    if existing_order:
        # 기존 예약이 아직 유효한지 확인
        from django.utils import timezone
        if existing_order.reservation_expires_at and timezone.now() < existing_order.reservation_expires_at:
            # 유효한 기존 예약이 있으면 해당 페이지로 진행
            pass
        else:
            # 만료된 예약은 취소
            release_reservation(existing_order, "예약 시간 만료")
            existing_order = None
    
    # 새로운 임시 예약 생성 (GET 요청인 경우)
    if request.method == 'GET' and not existing_order:
        success, message, order = create_temporary_reservation(meetup, request.user)
        
        if not success:
            # 정원이 마감된 경우 특별 메시지 표시
            if "마감되었습니다" in message:
                context = {
                    'store': store,
                    'meetup': meetup,
                    'is_full_message': True,
                    'message': message
                }
                return render(request, 'meetup/meetup_full.html', context)
            else:
                messages.error(request, message)
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        existing_order = order
    
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
        
        # 사이트 설정에서 카운트다운 시간 가져오기
        from myshop.models import SiteSettings
        site_settings = SiteSettings.get_settings()
        countdown_seconds = site_settings.meetup_countdown_seconds
        
        context = {
            'store': store,
            'meetup': meetup,
            'order': existing_order,
            'selected_options_json': json.dumps(selected_options) if selected_options else '{}',
            'required_option_ids': json.dumps(required_option_ids) if required_option_ids else '[]',
            'discount_amount': discount_amount,
            'countdown_seconds': countdown_seconds,
            'reservation_expires_at': existing_order.reservation_expires_at.isoformat() if existing_order and existing_order.reservation_expires_at else None,
        }
        return render(request, 'meetup/meetup_participant_info.html', context)
    
    # POST 요청인 경우 참가자 정보 업데이트 후 결제 페이지로
    if request.method == 'POST':
        # 유효한 임시 예약이 있는지 확인
        if not existing_order or not existing_order.is_temporary_reserved:
            messages.error(request, '유효한 예약이 없습니다. 다시 신청해 주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 예약 시간이 만료되었는지 확인
        from django.utils import timezone
        if existing_order.reservation_expires_at and timezone.now() > existing_order.reservation_expires_at:
            release_reservation(existing_order, "참가자 정보 입력 시간 초과")
            messages.error(request, '신청 시간이 초과되어 자동으로 취소되었습니다. 다시 신청해 주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
        # 기존 예약 주문 업데이트
        try:
            with transaction.atomic():
                # 기본 가격 재계산 (현재 가격 기준)
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
                
                # 참가자 정보 업데이트
                participant_name = request.POST.get('participant_name') or request.user.get_full_name() or request.user.username
                participant_email = request.POST.get('participant_email') or request.user.email
                participant_phone = request.POST.get('participant_phone', '').strip()
                
                # 기존 주문 정보 업데이트
                existing_order.participant_name = participant_name
                existing_order.participant_email = participant_email
                existing_order.participant_phone = participant_phone
                existing_order.base_price = base_price
                existing_order.options_price = options_price
                existing_order.total_price = total_price
                existing_order.is_early_bird = is_early_bird
                existing_order.discount_rate = discount_rate
                existing_order.original_price = original_price
                
                # 예약 시간을 다음 단계(결제)로 연장
                from .services import extend_reservation
                extend_reservation(existing_order)
                
                existing_order.save()
                
                # 기존 옵션 선택 삭제 후 새로 생성
                existing_order.selected_options.all().delete()
                for choice in selected_option_choices:
                    MeetupOrderOption.objects.create(
                        order=existing_order,
                        option=choice.option,
                        choice=choice,
                        additional_price=choice.additional_price
                    )
                
                # 무료 밋업인 경우 바로 참가 확정 처리
                if total_price == 0:
                    logger.info(f"무료 밋업 감지 - 무료 체크아웃 페이지로 리다이렉트: {existing_order.order_number}")
                    return redirect('meetup:meetup_free_checkout', store_id=store_id, meetup_id=meetup_id)
                
                # 유료 밋업인 경우 결제 페이지로
                # 블링크 서비스 연결 확인
                blink_service = get_blink_service_for_store(store)
                payment_service_available = blink_service is not None
                
                # 사이트 설정에서 카운트다운 시간 가져오기
                from myshop.models import SiteSettings
                site_settings = SiteSettings.get_settings()
                countdown_seconds = site_settings.meetup_countdown_seconds
                
                context = {
                    'store': store,
                    'meetup': meetup,
                    'order': existing_order,
                    'payment_service_available': payment_service_available,
                    'countdown_seconds': countdown_seconds,
                    'reservation_expires_at': existing_order.reservation_expires_at.isoformat() if existing_order.reservation_expires_at else None,
                }
                
                return render(request, 'meetup/meetup_checkout.html', context)
                
        except Exception as e:
            logger.error(f"밋업 주문 업데이트 오류: {e}", exc_info=True)
            
            # 예외 종류별 상세 처리
            import traceback
            logger.error(f"밋업 주문 업데이트 상세 오류: {traceback.format_exc()}")
            
            # 사용자에게 구체적인 오류 메시지 제공
            if "order_number" in str(e).lower():
                messages.error(request, '주문번호 생성 중 오류가 발생했습니다.')
            elif "confirm_reservation" in str(e).lower():
                messages.error(request, '참가 확정 처리 중 오류가 발생했습니다.')
            elif "email" in str(e).lower():
                messages.error(request, '이메일 발송 중 오류가 발생했지만 참가 신청은 완료되었습니다.')
            else:
                messages.error(request, '주문 처리 중 오류가 발생했습니다.')
            
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
    
    # 사이트 설정에서 카운트다운 시간 가져오기
    from myshop.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    countdown_seconds = site_settings.meetup_countdown_seconds
    
    context = {
        'store': store,
        'meetup': meetup,
        'order': order,
        'payment_service_available': payment_service_available,
        'countdown_seconds': countdown_seconds,
        'reservation_expires_at': order.reservation_expires_at.isoformat() if order.reservation_expires_at else None,
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
    logger.info(f"결제 완료 페이지 접근 - store_id: {store_id}, meetup_id: {meetup_id}, order_id: {order_id}")
    
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        logger.info(f"스토어 조회 성공 - {store.store_name}")
        
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        logger.info(f"밋업 조회 성공 - {meetup.name}")
        
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            status__in=['confirmed', 'completed']
        )
        logger.info(f"주문 조회 성공 - {order.order_number}, 상태: {order.status}")
        
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
        
        logger.info(f"결제 완료 페이지 렌더링 성공 - 주문: {order.order_number}")
        return render(request, 'meetup/meetup_checkout_complete.html', context)
    
    except Exception as e:
        logger.error(f"결제 완료 페이지 오류: {e}", exc_info=True)
        messages.error(request, '결제 완료 페이지를 불러오는 중 오류가 발생했습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)

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
    
    # 해당 밋업의 주문들 (확정된 것과 취소된 것 포함)
    orders = MeetupOrder.objects.filter(
        meetup=meetup,
        status__in=['confirmed', 'completed', 'cancelled']
    ).select_related('user').prefetch_related('selected_options').order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 통계 계산 (확정된 주문만)
    confirmed_orders = orders.filter(status__in=['confirmed', 'completed'])
    total_participants = confirmed_orders.count()
    total_revenue = confirmed_orders.aggregate(
        total=models.Sum('total_price')
    )['total'] or 0
    
    # 참석자 통계 계산
    attended_count = confirmed_orders.filter(attended=True).count()
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

@login_required
@require_POST
@csrf_exempt
def cancel_participation(request, store_id, meetup_id):
    """참가 취소"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
        
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({
                'success': False,
                'error': '주문 ID가 필요합니다.'
            })
        
        # 해당 밋업의 확정된 주문인지 확인
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            status='confirmed'
        )
        
        # 주문 상태를 취소로 변경 및 임시 예약 플래그 정리
        order.status = 'cancelled'
        order.is_temporary_reserved = False  # 임시 예약 해제
        order.reservation_expires_at = None  # 예약 만료 시간 제거
        order.auto_cancelled_reason = '관리자에 의한 참가 취소'  # 취소 사유 기록
        order.save()
        
        logger.info(f"밋업 참가 취소: {order.order_number} - {order.participant_name}")
        
        return JsonResponse({
            'success': True,
            'message': '참가가 성공적으로 취소되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"참가 취소 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '참가 취소 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def release_meetup_reservation(request, store_id, meetup_id):
    """밋업 임시 예약 해제 (사용자가 페이지를 벗어날 때)"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': '로그인이 필요합니다.'
            })
        
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        
        # 현재 사용자의 임시 예약 찾기
        order = MeetupOrder.objects.filter(
            meetup=meetup,
            user=request.user,
            status='pending',
            is_temporary_reserved=True
        ).first()
        
        if not order:
            return JsonResponse({
                'success': False,
                'error': '해제할 예약이 없습니다.'
            })
        
        # 예약 해제
        reason = request.POST.get('reason', '사용자 취소')
        from .services import release_reservation
        success = release_reservation(order, reason)
        
        if success:
            logger.info(f"사용자 요청으로 예약 해제 - 주문: {order.order_number}, 사유: {reason}")
            return JsonResponse({
                'success': True,
                'message': '예약이 해제되었습니다.'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '예약 해제에 실패했습니다.'
            })
            
    except Exception as e:
        logger.error(f"예약 해제 API 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '예약 해제 중 오류가 발생했습니다.'
        })

@login_required
@require_POST
@csrf_exempt
def toggle_temporary_closure(request, store_id, meetup_id):
    """밋업 일시중단 토글"""
    import json
    
    try:
        # 스토어 소유자 권한 확인
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
        
        # 현재 일시중단 상태 토글
        meetup.is_temporarily_closed = not meetup.is_temporarily_closed
        meetup.save()
        
        action = "일시중단" if meetup.is_temporarily_closed else "일시중단 해제"
        message = f'"{meetup.name}" 밋업이 {action}되었습니다.'
        
        logger.info(f"밋업 일시중단 상태 변경: {meetup.name} - {action} (사용자: {request.user.username})")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'is_temporarily_closed': meetup.is_temporarily_closed
        })
        
    except Exception as e:
        logger.error(f"밋업 일시중단 토글 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '일시중단 상태 변경 중 오류가 발생했습니다.'
        })

@require_http_methods(["GET"])
def meetup_capacity_status(request, store_id, meetup_id):
    """밋업 정원 상태 API (AJAX용)"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        
        # 공개 뷰에서는 비활성화되거나 일시중단된 밋업만 접근 차단
        if request.user != store.owner:
            if not meetup.is_active or meetup.is_temporarily_closed:
                return JsonResponse({'error': '밋업을 찾을 수 없습니다.'}, status=404)
        
        # 현재 정원 상태 계산
        data = {
            'current_participants': meetup.current_participants,
            'reserved_participants': meetup.reserved_participants,
            'max_participants': meetup.max_participants,
            'remaining_spots': meetup.remaining_spots,
            'is_full': meetup.is_full,
            'can_participate': meetup.can_participate,
            'is_expired': meetup.is_expired,
            'is_temporarily_closed': meetup.is_temporarily_closed,
            'status_display': meetup.status_display,
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': '정원 정보를 가져올 수 없습니다.'}, status=500)

@login_required
def meetup_free_checkout(request, store_id, meetup_id):
    """무료 밋업 전용 체크아웃 페이지"""
    from datetime import timedelta
    import logging
    logger = logging.getLogger(__name__)
    
    # 강제 로그 출력
    print(f"🚀🚀🚀 MEETUP_FREE_CHECKOUT 뷰 시작: store_id={store_id}, meetup_id={meetup_id}, user={request.user}")
    logger.error(f"🎯 무료 체크아웃 접근: store_id={store_id}, meetup_id={meetup_id}, user={request.user.id}")
    
    try:
        print(f"🔍 Store 조회 시작: store_id={store_id}")
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        print(f"✅ Store 조회 성공: {store.store_name}")
        
        print(f"🔍 Meetup 조회 시작: meetup_id={meetup_id}")
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store)
        print(f"✅ Meetup 조회 성공: {meetup.name}")
        
        logger.info(f"✅ Store와 Meetup 조회 성공: store={store.store_name}, meetup={meetup.name}, is_free={meetup.is_free}")
        
        print(f"🔍 밋업 검증 시작: is_active={meetup.is_active}, is_temporarily_closed={meetup.is_temporarily_closed}, is_free={meetup.is_free}")
        
        # 활성화된 밋업인지 확인
        if not meetup.is_active:
            print(f"❌ 비활성화된 밋업 접근: {meetup_id}")
            logger.warning(f"❌ 비활성화된 밋업 접근: {meetup_id}")
            messages.error(request, '비활성화된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 임시 중단된 밋업인지 확인
        if meetup.is_temporarily_closed:
            print(f"❌ 임시 중단된 밋업 접근: {meetup_id}")
            logger.warning(f"❌ 임시 중단된 밋업 접근: {meetup_id}")
            messages.error(request, '일시적으로 참가 신청이 중단된 밋업입니다.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 무료 밋업인지 확인
        if not meetup.is_free:
            print(f"❌ 유료 밋업에 무료 체크아웃 접근 시도 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            logger.warning(f"❌ 유료 밋업에 무료 체크아웃 접근 시도 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            messages.error(request, '이 밋업은 유료 밋업입니다. 일반 결제 페이지를 이용해주세요.')
            return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)
        
        print(f"✅ 모든 검증 통과 - 무료 밋업 체크아웃 진행")
        logger.info(f"✅ 모든 검증 통과 - 무료 밋업 체크아웃 진행")
        
        # 기존 주문 확인
        print(f"🔍 기존 주문 확인 시작 - 밋업ID: {meetup_id}, 사용자ID: {request.user.id}")
        existing_order = MeetupOrder.objects.filter(
            meetup=meetup,
            user=request.user,
            status__in=['pending', 'confirmed', 'completed']
        ).first()
        
        if existing_order:
            print(f"✅ 기존 주문 발견: {existing_order.order_number}, 상태: {existing_order.status}")
        else:
            print(f"🆕 기존 주문 없음 - 새 주문 생성 필요")
        
        # 기존 주문이 없으면 새로 생성 (GET 요청 시)
        if not existing_order and request.method == 'GET':
            print(f"🆕 새 주문 생성 시작 - GET 요청")
            logger.info(f"무료 밋업 새 주문 생성 시작 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            
            try:
                # 무료 밋업은 옵션 없이 기본 가격(0)만 사용
                total_price = 0
                
                # 사이트 설정에서 카운트다운 시간 가져오기
                from myshop.models import SiteSettings
                site_settings = SiteSettings.get_settings()
                countdown_minutes = site_settings.meetup_countdown_seconds // 60
                
                print(f"⏰ 카운트다운 시간: {countdown_minutes}분 ({site_settings.meetup_countdown_seconds}초)")
                
                # 새 주문 생성
                reservation_expires_at = timezone.now() + timedelta(seconds=site_settings.meetup_countdown_seconds)
                
                print(f"📝 새 주문 생성 중... (만료시간: {reservation_expires_at})")
                existing_order = MeetupOrder.objects.create(
                    meetup=meetup,
                    user=request.user,
                    participant_name=request.user.get_full_name() or request.user.username,
                    participant_email=request.user.email,
                    base_price=0,
                    options_price=0,
                    total_price=total_price,
                    status='pending',
                    is_temporary_reserved=True,  # 임시 예약 플래그 추가
                    reservation_expires_at=reservation_expires_at
                )
                
                print(f"✅ 새 주문 생성 완료: {existing_order.order_number}")
                logger.info(f"무료 밋업 새 주문 생성 완료 - 주문: {existing_order.order_number}")
                
            except Exception as e:
                print(f"❌ 주문 생성 오류: {str(e)}")
                logger.error(f"무료 밋업 주문 생성 오류: {str(e)}", exc_info=True)
                messages.error(request, '주문 생성 중 오류가 발생했습니다.')
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        elif not existing_order:
            print(f"❌ POST 요청이지만 주문 없음")
            logger.warning(f"무료 체크아웃 페이지 접근했지만 주문이 없음 - 밋업: {meetup_id}, 사용자: {request.user.id}")
            messages.error(request, '주문 정보를 찾을 수 없습니다. 다시 참가 신청을 해주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 이미 확정된 주문인 경우
        if existing_order.status in ['confirmed', 'completed']:
            print(f"✅ 이미 확정된 주문 - 완료 페이지로 이동: {existing_order.order_number}")
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
        print(f"🎨 GET 요청 - 페이지 렌더링 시작")
        
        # 사이트 설정에서 카운트다운 시간 가져오기
        from myshop.models import SiteSettings
        site_settings = SiteSettings.get_settings()
        
        # 예약 만료 시간 계산
        reservation_expires_at = None
        countdown_seconds = 0
        
        print(f"⏰ 예약 만료 시간 확인 - 주문 만료시간: {existing_order.reservation_expires_at}")
        if existing_order.reservation_expires_at:
            if timezone.now() < existing_order.reservation_expires_at:
                reservation_expires_at = existing_order.reservation_expires_at.isoformat()
                countdown_seconds = int((existing_order.reservation_expires_at - timezone.now()).total_seconds())
                print(f"✅ 예약 유효 - 남은 시간: {countdown_seconds}초")
            else:
                # 예약 시간 만료
                print(f"⏰ 예약 시간 만료 - 주문 삭제")
                logger.info(f"무료 밋업 예약 시간 만료 - 주문: {existing_order.order_number}")
                messages.error(request, '예약 시간이 만료되었습니다. 다시 참가 신청을 해주세요.')
                existing_order.delete()
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        print(f"📋 컨텍스트 준비 중...")
        context = {
            'store': store,
            'meetup': meetup,
            'order': existing_order,
            'countdown_seconds': countdown_seconds,
            'reservation_expires_at': reservation_expires_at,
            'site_countdown_seconds': site_settings.meetup_countdown_seconds,
        }
        
        print(f"🎨 템플릿 렌더링 시작: meetup/meetup_free_checkout.html")
        logger.info(f"🚀 무료 체크아웃 템플릿 렌더링: meetup_free_checkout.html")
        return render(request, 'meetup/meetup_free_checkout.html', context)
        
    except Store.DoesNotExist:
        print(f"🔥 Store.DoesNotExist 오류 발생: store_id={store_id}")
        logger.error(f"존재하지 않는 스토어 접근 시도 - store_id: {store_id}")
        messages.error(request, '존재하지 않는 스토어입니다.')
        return redirect('store:store_list')
    except Exception as e:
        print(f"🔥 예외 발생: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔥 Traceback: {traceback.format_exc()}")
        logger.error(f"무료 밋업 체크아웃 페이지 오류: {str(e)}")
        messages.error(request, '페이지 로드 중 오류가 발생했습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
