from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from stores.models import Store
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice, MeetupOrder, MeetupOrderOption
from .forms import MeetupForm
import json
import logging
from django.core.paginator import Paginator
from django.db import models
from ln_payment.models import PaymentTransaction
from ln_payment.services import PaymentStage

logger = logging.getLogger(__name__)

TRANSACTION_STATUS_DESCRIPTIONS = {
    PaymentTransaction.STATUS_PENDING: '대기: 결제 절차가 아직 시작되지 않았습니다.',
    PaymentTransaction.STATUS_PROCESSING: '진행 중: 인보이스 발행과 결제 확인을 처리 중입니다.',
    PaymentTransaction.STATUS_COMPLETED: '완료: 결제와 참가 확정이 정상적으로 마무리되었습니다.',
    PaymentTransaction.STATUS_FAILED: '실패: 결제 과정에서 오류가 발생했거나 취소되었습니다.',
}

TRANSACTION_STAGE_LABELS = {
    PaymentStage.PREPARE: '1단계 · 참가 정보 확인',
    PaymentStage.INVOICE: '2단계 · 인보이스 발행',
    PaymentStage.USER_PAYMENT: '3단계 · 결제 확인',
    PaymentStage.MERCHANT_SETTLEMENT: '4단계 · 입금 검증',
    PaymentStage.ORDER_FINALIZE: '5단계 · 참가 확정',
}

def check_admin_access(request, store):
    """수퍼어드민 특별 접근 확인 및 메시지 표시"""
    admin_access = request.GET.get('admin_access', '').lower() == 'true'
    is_superuser = request.user.is_superuser
    is_owner = store.owner == request.user
    
    # 스토어 소유자이거나 수퍼어드민이 admin_access 파라미터를 사용한 경우 접근 허용
    if is_owner or (is_superuser and admin_access):
        # 수퍼어드민이 다른 스토어에 접근하는 경우 알림 메시지 표시
        if is_superuser and admin_access and not is_owner:
            messages.info(request, f'관리자 권한으로 "{store.store_name}" 스토어에 접근 중입니다.')
        return True
    return False

def get_store_with_admin_check(request, store_id, require_auth=True):
    """스토어 조회 및 관리자 권한 확인"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    if require_auth and request.user.is_authenticated:
        if not check_admin_access(request, store):
            is_superuser = request.user.is_superuser
            if is_superuser:
                # 수퍼어드민인 경우 admin_access 파라미터 사용법 안내
                messages.error(request, 
                    '스토어 소유자만 접근할 수 있습니다. '
                    '관리자 권한으로 접근하려면 URL에 "?admin_access=true" 파라미터를 추가하세요.')
            else:
                messages.error(request, '스토어 소유자만 접근할 수 있습니다.')
            return None
    
    return store

def meetup_list(request, store_id):
    """밋업 목록 (공개/관리자 뷰)"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        raise Http404("스토어를 찾을 수 없습니다.")
    
    # 스토어 소유자인지 확인하여 관리자/공개 뷰 결정 (수퍼어드민 접근 포함)
    is_public_view = not (request.user.is_authenticated and check_admin_access(request, store))
    
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
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
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
    is_owner_or_admin = request.user.is_authenticated and check_admin_access(request, store)
    if not is_owner_or_admin:
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
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
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
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
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
    """밋업 체크아웃 라우팅 - 무료/유료에 따라 적절한 뷰로 리다이렉트"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True,
        is_active=True
    )
    
    # 무료 밋업인 경우 무료 체크아웃으로 리다이렉트
    if meetup.is_free:
        from .views_free import meetup_free_checkout
        return meetup_free_checkout(request, store_id, meetup_id)
    else:
        # 유료 밋업인 경우 유료 체크아웃으로 리다이렉트
        from .views_paid import meetup_checkout as paid_checkout
        return paid_checkout(request, store_id, meetup_id)

# 유료 밋업 결제 관련 뷰들은 views_paid.py로 분리됨

def meetup_checkout_complete(request, store_id, meetup_id, order_id):
    """밋업 결제 완료"""
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
            status__in=['confirmed', 'completed']  # 🔄 확정된 주문만 결제 완료 페이지 접근 가능
        )
        
        # 결제가 완료되지 않은 경우 결제 페이지로 리다이렉트
        if not order.paid_at:
            messages.warning(request, '결제를 완료해주세요.')
            return redirect('meetup:meetup_checkout_payment', store_id=store_id, meetup_id=meetup_id)
        
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
    
    except Exception:
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
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
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
def meetup_payment_transactions(request, store_id):
    """밋업 결제 트랜잭션 현황"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')

    status_filter = request.GET.get('status')
    stage_filter = request.GET.get('stage')

    transactions_qs = PaymentTransaction.objects.filter(
        store=store,
        meetup_order__isnull=False,
    )

    if status_filter in {
        PaymentTransaction.STATUS_PENDING,
        PaymentTransaction.STATUS_PROCESSING,
        PaymentTransaction.STATUS_FAILED,
        PaymentTransaction.STATUS_COMPLETED,
    }:
        transactions_qs = transactions_qs.filter(status=status_filter)

    if stage_filter and stage_filter.isdigit():
        transactions_qs = transactions_qs.filter(current_stage=int(stage_filter))

    paginator = Paginator(
        transactions_qs.select_related(
            'user',
            'meetup_order',
            'meetup_order__meetup',
        ).order_by('-created_at'),
        5,
    )
    page_number = request.GET.get('page')
    transactions_page = paginator.get_page(page_number)

    for tx in transactions_page:
        metadata = tx.metadata if isinstance(tx.metadata, dict) else {}
        participant_info = metadata.get('participant') or {}
        order = tx.meetup_order
        meetup = order.meetup if order else None
        user = order.user if order else tx.user

        tx.meetup_title = meetup.name if meetup else metadata.get('meetup_name', '밋업')
        tx.order_number = order.order_number if order else None
        tx.meetup_id = meetup.id if meetup else None
        tx.meetup_order_id = order.id if order else None
        tx.participant_name = (
            participant_info.get('participant_name')
            or (getattr(user, 'get_full_name', lambda: '')() or getattr(user, 'username', ''))
            or '미상'
        )
        tx.participant_email = participant_info.get('participant_email') or getattr(user, 'email', '')
        tx.status_description = TRANSACTION_STATUS_DESCRIPTIONS.get(tx.status, '')
        stage_label = TRANSACTION_STAGE_LABELS.get(tx.current_stage)
        tx.stage_label = stage_label or f'{tx.current_stage}단계'
        tx.manual_restore_enabled = tx.status != PaymentTransaction.STATUS_COMPLETED
        tx.reservation_expires_at = getattr(order, 'reservation_expires_at', None)
        if isinstance(metadata, dict):
            tx.manual_restored = bool(
                metadata.get('manual_restored')
                or (metadata.get('manual_restore_history') or [])
            )

    base_qs = PaymentTransaction.objects.filter(
        store=store,
        meetup_order__isnull=False,
    )
    summary = {
        'total': base_qs.count(),
        'pending': base_qs.filter(status=PaymentTransaction.STATUS_PENDING).count(),
        'processing': base_qs.filter(status=PaymentTransaction.STATUS_PROCESSING).count(),
        'completed': base_qs.filter(status=PaymentTransaction.STATUS_COMPLETED).count(),
        'failed': base_qs.filter(status=PaymentTransaction.STATUS_FAILED).count(),
        'total_amount': base_qs.aggregate(total=models.Sum('amount_sats'))['total'] or 0,
    }

    admin_access_query = '?admin_access=true' if request.GET.get('admin_access', '').lower() == 'true' else ''

    context = {
        'store': store,
        'transactions': transactions_page,
        'paginator': paginator,
        'page_obj': transactions_page,
        'status_filter': status_filter or '',
        'stage_filter': stage_filter or '',
        'summary': summary,
        'admin_access_query': admin_access_query,
    }

    return render(request, 'meetup/meetup_payment_transactions.html', context)


@login_required
def meetup_payment_transaction_detail(request, store_id, transaction_id):
    """밋업 결제 트랜잭션 상세 (orders 상세 화면 재사용)"""
    from orders.views import payment_transaction_detail  # 순환 참조 방지용 지연 임포트

    return payment_transaction_detail(request, store_id, transaction_id, source='meetup')


@login_required
def meetup_status_detail(request, store_id, meetup_id):
    """밋업별 참가 현황 상세 페이지"""
    from stores.decorators import store_owner_required
    from django.core.paginator import Paginator
    from django.db import models
    
    # 스토어 소유자 권한 확인
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
    
    # 해당 밋업의 주문들 (확정된 것, 취소된 것 포함)
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
def export_meetup_participants_csv(request, store_id, meetup_id):
    """프론트엔드용 밋업 참가자 정보 CSV 내보내기"""
    import csv
    from django.http import HttpResponse
    from django.utils import timezone
    
    # 스토어 소유자 권한 확인
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
    
    # 참가자 목록 (확정된 주문만)
    participants = MeetupOrder.objects.filter(
        meetup=meetup,
        status__in=['confirmed', 'completed']
    ).select_related('user').prefetch_related('selected_options__option', 'selected_options__choice').order_by('-created_at')
    
    # CSV 응답 생성
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    generated_at = timezone.localtime(timezone.now())
    response['Content-Disposition'] = f'attachment; filename="{meetup.name}_participants_{generated_at.strftime("%Y%m%d_%H%M")}.csv"'
    response.write('\ufeff'.encode('utf8'))  # BOM for Excel
    
    writer = csv.writer(response)
    
    # 헤더 작성
    headers = [
        '밋업명', '스토어명', '참가자명', '이메일', '연락처', '주문번호',
        '상태', '기본참가비', '옵션금액', '총참가비', '원가격', '할인율', '조기등록여부',
        '결제해시', '결제일시', '참가신청일시', '참석여부', '참석체크일시',
        '선택옵션'
    ]
    writer.writerow(headers)
    
    # 데이터 작성
    for participant in participants:
        # 선택 옵션 정보 수집
        selected_options = []
        for selected_option in participant.selected_options.all():
            option_text = f"{selected_option.option.name}: {selected_option.choice.name}"
            if selected_option.additional_price > 0:
                option_text += f" (+{selected_option.additional_price:,} sats)"
            selected_options.append(option_text)
        
        options_text = " | ".join(selected_options) if selected_options else "없음"
        
        # 상태 텍스트 변환
        status_text = {
            'confirmed': '참가확정',
            'completed': '밋업완료',
            'pending': '결제대기',
            'cancelled': '참가취소'
        }.get(participant.status, participant.status)
        
        row = [
            meetup.name,
            meetup.store.store_name,
            participant.participant_name,
            participant.participant_email,
            participant.participant_phone or '',
            participant.order_number,
            status_text,
            f"{participant.base_price:,}",
            f"{participant.options_price:,}",
            f"{participant.total_price:,}",
            f"{participant.original_price:,}" if participant.original_price else '',
            f"{participant.discount_rate}%" if participant.discount_rate else '',
            "예" if participant.is_early_bird else "아니오",
            participant.payment_hash or '',
            timezone.localtime(participant.paid_at).strftime('%Y-%m-%d %H:%M:%S') if participant.paid_at else '',
            timezone.localtime(participant.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            "참석" if participant.attended else "미참석",
            timezone.localtime(participant.attended_at).strftime('%Y-%m-%d %H:%M:%S') if participant.attended_at else '',
            options_text
        ]
        writer.writerow(row)
    
    return response

@login_required
@require_POST
@csrf_exempt
def update_attendance(request, store_id, meetup_id):
    """참석 여부 업데이트"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
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
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
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
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
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

@login_required
@require_POST
@csrf_exempt
def delete_meetup(request, store_id, meetup_id):
    """밋업 삭제 (soft delete)"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
        
        # 참가자가 있는 경우 삭제 불가
        if meetup.current_participants > 0:
            return JsonResponse({
                'success': False,
                'error': '참가자가 있는 밋업은 삭제할 수 없습니다. 먼저 모든 참가자를 취소해주세요.'
            })
        
        # Soft delete 처리
        meetup.deleted_at = timezone.now()
        meetup.save()
        
        logger.info(f"밋업 삭제: {meetup.name} (사용자: {request.user.username})")
        
        return JsonResponse({
            'success': True,
            'message': f'"{meetup.name}" 밋업이 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"밋업 삭제 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '밋업 삭제 중 오류가 발생했습니다.'
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
        is_owner_or_admin = request.user.is_authenticated and check_admin_access(request, store)
        if not is_owner_or_admin:
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

# 무료 밋업 체크아웃 뷰는 views_free.py로 분리됨

@login_required
def meetup_checker(request, store_id, meetup_id):
    """밋업체커 - QR 스캔 및 수동 참석 확인"""
    # 스토어 소유자 권한 확인
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, '권한이 없습니다.')
        return redirect('stores:store_detail', store_id=store_id)
    
    # 밋업 조회
    meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
    
    # 통계 계산
    total_participants = MeetupOrder.objects.filter(
        meetup=meetup,
        status__in=['confirmed', 'completed']
    ).count()
    
    attended_count = MeetupOrder.objects.filter(
        meetup=meetup,
        status__in=['confirmed', 'completed'],
        attended=True
    ).count()
    
    attendance_rate = (attended_count / total_participants * 100) if total_participants > 0 else 0
    
    # 티켓 prefix 계산 (스토어id-ticket-YYYYMMDD- 형태)
    if meetup.date_time:
        date_str = timezone.localtime(meetup.date_time).strftime('%Y%m%d')
    else:
        date_str = timezone.localtime(timezone.now()).strftime('%Y%m%d')
    
    ticket_prefix = f"{store.store_id}-ticket-{date_str}-"
    
    context = {
        'store': store,
        'meetup': meetup,
        'total_participants': total_participants,
        'attended_count': attended_count,
        'attendance_rate': attendance_rate,
        'ticket_prefix': ticket_prefix,
    }
    
    # Permissions Policy 헤더로 카메라 접근 허용
    response = render(request, 'meetup/meetup_checker.html', context)
    response['Permissions-Policy'] = 'camera=*, microphone=()'
    # 추가적인 헤더 설정
    response['Feature-Policy'] = 'camera *; microphone ()'
    return response

@login_required
@require_POST
@csrf_exempt
def check_attendance(request, store_id, meetup_id):
    """QR 코드 또는 주문번호로 참석 확인"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        
        # 밋업 조회
        meetup = get_object_or_404(Meetup, id=meetup_id, store=store, deleted_at__isnull=True)
        
        # 요청 데이터 파싱
        data = json.loads(request.body)
        order_number = data.get('order_number', '').strip()
        source = data.get('source', 'unknown')  # 'qr' 또는 'manual'
        
        if not order_number:
            return JsonResponse({
                'success': False,
                'error': '주문번호가 필요합니다.'
            })
        
        # 주문 조회
        try:
            order = MeetupOrder.objects.get(
                order_number=order_number,
                meetup=meetup,
                status__in=['confirmed', 'completed']
            )
        except MeetupOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '해당 주문번호를 찾을 수 없거나 이 밋업의 참가자가 아닙니다.',
                'error_type': 'not_found'
            })
        
        # 이미 참석 확인된 경우
        if order.attended:
            return JsonResponse({
                'success': False,
                'error': (
                    f'{order.participant_name}님은 이미 참석 확인되었습니다. '
                    f'(확인시간: {timezone.localtime(order.attended_at).strftime("%m/%d %H:%M")})'
                ),
                'error_type': 'already_attended',
                'participant': {
                    'name': order.participant_name,
                    'email': order.participant_email,
                    'phone': order.participant_phone,
                    'order_number': order.order_number,
                    'attended_at': order.attended_at.isoformat()
                }
            })
        
        # 참석 확인 처리
        order.attended = True
        order.attended_at = timezone.now()
        order.save()
        
        # 현재 통계 재계산
        total_participants = MeetupOrder.objects.filter(
            meetup=meetup,
            status__in=['confirmed', 'completed']
        ).count()
        
        attended_count = MeetupOrder.objects.filter(
            meetup=meetup,
            status__in=['confirmed', 'completed'],
            attended=True
        ).count()
        
        attendance_rate = (attended_count / total_participants * 100) if total_participants > 0 else 0
        
        logger.info(f"참석 확인 완료 - 밋업: {meetup.name}, 참가자: {order.participant_name}, 주문: {order_number}, 방법: {source}")
        
        return JsonResponse({
            'success': True,
            'message': '참석 확인이 완료되었습니다.',
            'participant': {
                'name': order.participant_name,
                'email': order.participant_email,
                'phone': order.participant_phone,
                'order_number': order.order_number,
                'attended_at': order.attended_at.isoformat()
            },
            'stats': {
                'total_participants': total_participants,
                'attended_count': attended_count,
                'attendance_rate': attendance_rate
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"참석 확인 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '참석 확인 중 오류가 발생했습니다.'
        })
