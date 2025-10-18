from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.core.files.storage import default_storage
from datetime import timedelta
import json
import logging
import os
import mimetypes
import urllib.parse

from stores.models import Store
from .models import DigitalFile, FileOrder, FileDownloadLog
from .forms import DigitalFileForm
from .services import (
    send_file_purchase_notification_email,
    send_file_buyer_confirmation_email
)
from ln_payment.blink_service import get_blink_service_for_store
from ln_payment.models import PaymentTransaction
from ln_payment.services import LightningPaymentProcessor, PaymentStage

logger = logging.getLogger(__name__)

TRANSACTION_STATUS_DESCRIPTIONS = {
    PaymentTransaction.STATUS_PENDING: '대기: 결제 절차가 아직 시작되지 않았습니다.',
    PaymentTransaction.STATUS_PROCESSING: '진행 중: 인보이스 발행과 결제 확인을 처리하는 중입니다.',
    PaymentTransaction.STATUS_COMPLETED: '완료: 결제와 다운로드 권한 부여가 정상적으로 끝났습니다.',
    PaymentTransaction.STATUS_FAILED: '실패: 결제 과정에서 오류가 발생했거나 취소되었습니다.',
}

TRANSACTION_STAGE_LABELS = {
    PaymentStage.PREPARE: '1단계 · 판매 가능 확인',
    PaymentStage.INVOICE: '2단계 · 인보이스 발행',
    PaymentStage.USER_PAYMENT: '3단계 · 결제 확인',
    PaymentStage.MERCHANT_SETTLEMENT: '4단계 · 입금 검증',
    PaymentStage.ORDER_FINALIZE: '5단계 · 다운로드 권한',
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


@login_required
def add_file(request, store_id):
    """파일 추가 (다중 파일 지원)"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    if request.method == 'POST':
        # AJAX 요청 처리 (다중 파일)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return handle_multiple_file_upload(request, store)
        
        # 단일 파일 처리 (폴백)
        form = DigitalFileForm(request.POST, request.FILES)
        if form.is_valid():
            digital_file = form.save(commit=False)
            digital_file.store = store
            digital_file.save()
            
            return redirect('file:file_manage', store_id=store.store_id)
    else:
        form = DigitalFileForm()
    
    context = {
        'store': store,
        'form': form,
        'is_owner': True,
    }
    return render(request, 'file/add_file.html', context)


def handle_multiple_file_upload(request, store):
    """다중 파일 업로드 AJAX 처리"""
    files = request.FILES.getlist('files[]')
    
    if len(files) > 10:
        return JsonResponse({
            'success': False,
            'error': '최대 10개의 파일만 업로드할 수 있습니다.'
        }, status=400)
    
    results = []
    success_count = 0
    
    for file in files:
        try:
            # 각 파일에 대한 폼 데이터 준비
            post_data = request.POST.copy()
            post_data['name'] = file.name.rsplit('.', 1)[0]
            
            # 파일 크기 검증
            if file.size > 100 * 1024 * 1024:  # 100MB
                results.append({
                    'name': file.name,
                    'success': False,
                    'error': '파일 크기가 100MB를 초과합니다.'
                })
                continue
            
            form = DigitalFileForm(post_data, {'file': file})
            if form.is_valid():
                digital_file = form.save(commit=False)
                digital_file.store = store
                digital_file.save()
                success_count += 1
                results.append({
                    'name': file.name,
                    'success': True,
                    'id': digital_file.id
                })
            else:
                results.append({
                    'name': file.name,
                    'success': False,
                    'error': form.errors.as_text()
                })
        except Exception as e:
            results.append({
                'name': file.name,
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': success_count > 0,
        'success_count': success_count,
        'total_count': len(files),
        'results': results
    })


@login_required
def edit_file(request, store_id, file_id):
    """파일 수정 (다중 파일 지원)"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    digital_file = get_object_or_404(DigitalFile, id=file_id, store=store, deleted_at__isnull=True)
    
    # preview_image URL 접근 시 에러 방지 (GET/POST 모두에서 필요)
    preview_image_url = None
    if digital_file.preview_image:
        try:
            preview_image_url = digital_file.preview_image.url
        except Exception as e:
            logger.warning(f"Preview image URL error for file {file_id}: {e}")
    
    if request.method == 'POST':
        # 다중 파일 정보 확인 (새 파일 추가 기능)
        files_info = request.POST.get('files_info', '')
        if files_info:
            try:
                files_data = json.loads(files_info)
                if len(files_data) > 1:
                    messages.info(request, "수정 모드에서는 하나의 파일만 업로드할 수 있습니다. 첫 번째 파일만 처리됩니다.")
            except (json.JSONDecodeError, KeyError):
                pass
        
        form = DigitalFileForm(request.POST, request.FILES, instance=digital_file)
        if form.is_valid():
            # 파일 변경 시 기존 파일은 models.py의 save()에서 자동 삭제
            form.save()
            return redirect('file:file_manage', store_id=store.store_id)
    else:
        form = DigitalFileForm(instance=digital_file)
    
    context = {
        'store': store,
        'form': form,
        'digital_file': digital_file,
        'preview_image_url': preview_image_url,
        'is_owner': True,
    }
    return render(request, 'file/edit_file.html', context)


@login_required
def delete_file(request, store_id, file_id):
    """파일 삭제 (소프트 삭제 및 오브젝트 스토리지 삭제)"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    # DB에서 필요한 데이터만 가져오기 (FileField 접근 방지)
    file_info = DigitalFile.objects.filter(
        id=file_id, 
        store=store, 
        deleted_at__isnull=True
    ).values(
        'id', 'name', 'file', 'preview_image', 'file_size', 'created_at'
    ).first()
    
    if not file_info:
        raise Http404("파일을 찾을 수 없습니다.")
    
    if request.method == 'POST':
        # 오브젝트 스토리지에서 파일 삭제
        deletion_errors = []
        
        # 메인 파일 삭제
        if file_info.get('file'):
            try:
                from storage.backends import S3Storage
                storage = S3Storage()
                storage.delete(file_info['file'])
                logger.info(f"Deleted file from storage: {file_info['file']}")
            except Exception as e:
                logger.error(f"Error deleting file {file_info['file']}: {e}", exc_info=True)
                deletion_errors.append(f"파일: {str(e)}")
        
        # 미리보기 이미지 삭제
        if file_info.get('preview_image'):
            try:
                from storage.backends import S3Storage
                storage = S3Storage()
                storage.delete(file_info['preview_image'])
                logger.info(f"Deleted preview image from storage: {file_info['preview_image']}")
            except Exception as e:
                logger.error(f"Error deleting preview image {file_info['preview_image']}: {e}", exc_info=True)
                deletion_errors.append(f"미리보기: {str(e)}")
        
        # 에러가 있었다면 경고 메시지
        if deletion_errors:
            logger.warning(f"파일 삭제 중 일부 오류 발생: {deletion_errors}")
            messages.warning(request, "파일 삭제 중 일부 오류가 발생했지만, 파일은 삭제 처리되었습니다.")
        
        # DB에서 소프트 삭제 (update 사용으로 객체 로드 방지)
        DigitalFile.objects.filter(id=file_id).update(
            deleted_at=timezone.now(),
            is_active=False
        )
        messages.success(request, f"파일 '{file_info['name']}'이(가) 삭제되었습니다.")
        return redirect('file:file_manage', store_id=store.store_id)
    
    # GET 요청에서는 템플릿에서 사용할 데이터만 준비
    # 판매 수와 다운로드 수는 별도로 계산
    sales_count = FileOrder.objects.filter(
        digital_file_id=file_id,
        status='confirmed'
    ).count()
    
    download_count = FileDownloadLog.objects.filter(
        order__digital_file_id=file_id
    ).count()
    
    # 파일 크기 표시용 변환
    def format_file_size(size):
        if not size:
            return "알 수 없음"
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    # 템플릿용 가상 객체 생성
    class FileInfo:
        def __init__(self, data):
            self.name = data['name']
            self.created_at = data['created_at']
            self.sales_count = sales_count
            self.download_count = download_count
            self.file_size_display = format_file_size(data.get('file_size'))
        
        def get_file_size_display(self):
            return self.file_size_display
    
    digital_file = FileInfo(file_info)
    
    context = {
        'store': store,
        'digital_file': digital_file,
        'is_owner': True,
    }
    return render(request, 'file/delete_file.html', context)


def file_list(request, store_id):
    """스토어의 파일 목록"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    is_owner = request.user.is_authenticated and (request.user == store.owner or request.user.is_staff)
    
    # 기본 쿼리셋
    queryset = DigitalFile.objects.filter(
        store=store,
        deleted_at__isnull=True
    )
    
    # 일반 사용자는 활성화된 파일만 볼 수 있음
    if not is_owner:
        queryset = queryset.filter(is_active=True, is_temporarily_closed=False)
    
    # 정렬
    sort = request.GET.get('sort', '-created_at')
    if sort == 'name':
        queryset = queryset.order_by('name')
    elif sort == '-name':
        queryset = queryset.order_by('-name')
    elif sort == 'price':
        queryset = queryset.order_by('price')
    elif sort == '-price':
        queryset = queryset.order_by('-price')
    else:
        queryset = queryset.order_by('-created_at')
    
    # 페이지네이션 - 5열 레이아웃에 맞춰 20개씩 표시
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'store': store,
        'files': page_obj,
        'is_owner': is_owner,
        'sort': sort,
    }
    return render(request, 'file/file_list.html', context)


def file_detail(request, store_id, file_id):
    """파일 상세 페이지"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    try:
        digital_file = DigitalFile.objects.get(id=file_id, store=store, deleted_at__isnull=True)
    except DigitalFile.DoesNotExist:
        context = {
            'store': store,
            'is_owner': request.user.is_authenticated and (request.user == store.owner or request.user.is_staff),
        }
        return render(request, 'file/file_not_found.html', context, status=404)
    
    is_owner = request.user.is_authenticated and (request.user == store.owner or request.user.is_staff)
    
    # 일반 사용자는 활성화된 파일만 볼 수 있음
    if not is_owner and (not digital_file.is_active or digital_file.is_temporarily_closed):
        context = {
            'store': store,
            'is_owner': is_owner,
        }
        return render(request, 'file/file_not_found.html', context, status=404)
    
    # 사용자가 이미 구매했는지 확인
    has_purchased = False
    can_download = False
    user_order = None
    
    if request.user.is_authenticated:
        user_order = FileOrder.objects.filter(
            digital_file=digital_file,
            user=request.user,
            status='confirmed'
        ).first()
        
        if user_order:
            has_purchased = True
            can_download = user_order.can_download
    
    # 원화 연동 가격인 경우 현재 환율 정보 가져오기
    current_exchange_rate = None
    if digital_file.price_display == 'krw':
        from myshop.models import ExchangeRate
        try:
            current_exchange_rate = ExchangeRate.objects.latest('created_at')
        except ExchangeRate.DoesNotExist:
            pass
    
    context = {
        'store': store,
        'file': digital_file,
        'is_owner': is_owner,
        'has_purchased': has_purchased,
        'can_download': can_download,
        'user_order': user_order,
        'current_exchange_rate': current_exchange_rate,
    }
    return render(request, 'file/file_detail.html', context)


@login_required
def file_manage(request, store_id):
    """파일 관리 페이지 (스토어 주인장용)"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    # 파일 목록
    files = DigitalFile.objects.filter(
        store=store,
        deleted_at__isnull=True
    ).annotate(
        order_count=Count('orders', filter=Q(orders__status='confirmed')),
        total_download_count=Count('orders__download_logs')
    ).order_by('-created_at')
    
    # 통계
    stats = {
        'total_files': files.count(),
        'active_files': files.filter(is_active=True, is_temporarily_closed=False).count(),
        'total_sales': FileOrder.objects.filter(
            digital_file__store=store,
            status='confirmed'
        ).count(),
        'total_revenue': FileOrder.objects.filter(
            digital_file__store=store,
            status='confirmed'
        ).aggregate(total=Sum('price'))['total'] or 0,
    }
    
    context = {
        'store': store,
        'files': files,
        'stats': stats,
        'is_owner': True,
    }
    return render(request, 'file/file_manage.html', context)


@login_required
def file_orders(request, store_id):
    """파일 주문 현황 (스토어 주인장용)"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    # 필터링
    status = request.GET.get('status', 'all')
    file_id = request.GET.get('file_id', '')
    
    # 기본 쿼리셋
    queryset = FileOrder.objects.filter(
        digital_file__store=store
    ).select_related('digital_file', 'user')
    
    # 상태 필터
    if status != 'all':
        queryset = queryset.filter(status=status)
    
    # 파일 필터
    if file_id:
        queryset = queryset.filter(digital_file_id=file_id)
    
    # 정렬
    queryset = queryset.order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 파일 목록 (필터용)
    files = DigitalFile.objects.filter(
        store=store,
        deleted_at__isnull=True
    ).order_by('name')
    
    context = {
        'store': store,
        'orders': page_obj,
        'files': files,
        'status': status,
        'file_id': file_id,
        'is_owner': True,
    }
    return render(request, 'file/file_orders.html', context)


@login_required
def file_payment_transactions(request, store_id):
    """디지털 파일 결제 트랜잭션 현황"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('stores:store_detail', store_id=store_id)

    status_filter = request.GET.get('status')
    stage_filter = request.GET.get('stage')

    transactions_qs = PaymentTransaction.objects.filter(
        store=store,
        file_order__isnull=False,
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
            'file_order',
            'file_order__digital_file',
        ).order_by('-created_at'),
        5,
    )
    page_number = request.GET.get('page')
    transactions_page = paginator.get_page(page_number)

    for tx in transactions_page:
        metadata = tx.metadata if isinstance(tx.metadata, dict) else {}
        order = tx.file_order
        digital_file = order.digital_file if order else None
        user = order.user if order else tx.user

        tx.file_title = digital_file.name if digital_file else metadata.get('file_name', '디지털 파일')
        tx.order_number = order.order_number if order else None
        tx.file_id = digital_file.id if digital_file else None
        tx.file_order_id = order.id if order else None
        tx.buyer_name = getattr(user, 'username', '') or getattr(user, 'email', '') or '미상'
        tx.status_description = TRANSACTION_STATUS_DESCRIPTIONS.get(tx.status, '')
        tx.stage_label = TRANSACTION_STAGE_LABELS.get(tx.current_stage) or f'{tx.current_stage}단계'
        tx.manual_restore_enabled = tx.status != PaymentTransaction.STATUS_COMPLETED
        tx.reservation_expires_at = getattr(order, 'reservation_expires_at', None)

    base_qs = PaymentTransaction.objects.filter(
        store=store,
        file_order__isnull=False,
    )
    summary = {
        'total': base_qs.count(),
        'pending': base_qs.filter(status=PaymentTransaction.STATUS_PENDING).count(),
        'processing': base_qs.filter(status=PaymentTransaction.STATUS_PROCESSING).count(),
        'completed': base_qs.filter(status=PaymentTransaction.STATUS_COMPLETED).count(),
        'failed': base_qs.filter(status=PaymentTransaction.STATUS_FAILED).count(),
        'total_amount': base_qs.aggregate(total=Sum('amount_sats'))['total'] or 0,
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
    return render(request, 'file/file_payment_transactions.html', context)


@login_required
def file_payment_transaction_detail(request, store_id, transaction_id):
    """디지털 파일 결제 트랜잭션 상세 (orders 상세 화면 재사용)"""
    from orders.views import payment_transaction_detail  # 지연 임포트로 순환 방지

    return payment_transaction_detail(request, store_id, transaction_id, source='file')


@login_required
def file_checkout(request, store_id, file_id):
    """파일 구매 체크아웃"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    digital_file = get_object_or_404(
        DigitalFile,
        id=file_id,
        store=store,
        deleted_at__isnull=True,
        is_active=True,
        is_temporarily_closed=False,
    )

    existing_order = FileOrder.objects.filter(
        digital_file=digital_file,
        user=request.user,
        status='confirmed',
    ).first()

    if existing_order:
        messages.info(request, "이미 구매하신 파일입니다.")
        return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)

    if digital_file.is_sold_out:
        messages.error(request, "죄송합니다. 매진되었습니다.")
        return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)

    price_sats = digital_file.current_price_sats
    original_price = digital_file.price if digital_file.is_discount_active and digital_file.price else price_sats
    discount_amount = max(0, (original_price or 0) - price_sats) if digital_file.is_discount_active else 0
    session_key = _get_file_payment_session_key(file_id)

    if price_sats == 0:
        if request.method == 'POST':
            with transaction.atomic():
                locked_file = DigitalFile.objects.select_for_update().get(
                    id=digital_file.id,
                    store=store,
                    deleted_at__isnull=True,
                )
                if locked_file.is_temporarily_closed:
                    messages.error(request, '현재 파일 판매가 일시 중단되었습니다.')
                    return redirect('file:file_detail', store_id=store.id, file_id=locked_file.id)
                if locked_file.max_downloads:
                    confirmed_count = locked_file.orders.filter(status__in=['confirmed']).count()
                    if confirmed_count >= locked_file.max_downloads:
                        messages.error(request, '죄송합니다. 방금 전에 매진되었습니다.')
                        return redirect('file:file_detail', store_id=store.id, file_id=locked_file.id)

                order = FileOrder.objects.create(
                    digital_file=locked_file,
                    user=request.user,
                    price=0,
                    status='confirmed',
                    is_temporary_reserved=False,
                    confirmed_at=timezone.now(),
                    paid_at=timezone.now(),
                )

            try:
                send_file_buyer_confirmation_email(order)
                send_file_purchase_notification_email(order)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("파일 구매 이메일 발송 실패 - order_id=%s, error=%s", order.id, exc)

            request.session.pop(session_key, None)
            messages.success(request, "무료 파일이 다운로드 가능합니다.")
            return redirect('file:file_complete', order_id=order.id)

        context = {
            'store': store,
            'file': digital_file,
            'price_sats': price_sats,
            'total_price': price_sats,
            'original_price': original_price,
            'discount_amount': discount_amount,
            'payment_service_available': False,
            'countdown_seconds': 0,
            'is_free': True,
            'existing_transaction': None,
        }
        return render(request, 'file/file_checkout.html', context)

    payment_service_available = get_blink_service_for_store(store) is not None

    from myshop.models import SiteSettings

    site_settings = SiteSettings.get_settings()
    countdown_seconds = max(60, site_settings.meetup_countdown_seconds)
    placeholder_uuid = '11111111-1111-1111-1111-111111111111'

    session_data = request.session.get(session_key, {})
    existing_transaction = None
    transaction_payload = None
    transaction_id = session_data.get('transaction_id')

    if transaction_id:
        try:
            existing_transaction = PaymentTransaction.objects.select_related('file_order').get(
                id=transaction_id,
                user=request.user,
                store=store,
            )
            if existing_transaction.status == PaymentTransaction.STATUS_COMPLETED:
                request.session.pop(session_key, None)
            else:
                transaction_payload = serialize_file_transaction(existing_transaction)
        except (PaymentTransaction.DoesNotExist, ValueError):
            request.session.pop(session_key, None)

    context = {
        'store': store,
        'file': digital_file,
        'price_sats': price_sats,
        'total_price': price_sats,
        'original_price': original_price,
        'discount_amount': discount_amount,
        'payment_service_available': payment_service_available,
        'countdown_seconds': countdown_seconds,
        'workflow_start_url': reverse('file:file_start_payment_workflow', args=[store_id, file_id]),
        'workflow_status_url_template': reverse('file:file_payment_status', args=[store_id, file_id, placeholder_uuid]),
        'workflow_verify_url_template': reverse('file:file_verify_payment', args=[store_id, file_id, placeholder_uuid]),
        'workflow_cancel_url_template': reverse('file:file_cancel_payment', args=[store_id, file_id, placeholder_uuid]),
        'workflow_inventory_redirect_url': reverse('file:file_detail', args=[store_id, file_id]),
        'workflow_cart_url': reverse('file:file_detail', args=[store_id, file_id]),
        'placeholder_uuid': placeholder_uuid,
        'existing_transaction': transaction_payload,
        'is_free': False,
    }
    return render(request, 'file/file_checkout.html', context)


def _get_file_payment_session_key(file_id: int) -> str:
    return f'file_payment_state_{file_id}'


def build_file_invoice_memo(digital_file, order, user) -> str:
    payer_identifier = getattr(user, 'username', None) or getattr(user, 'email', None) or str(user.id)
    memo = f"파일 구매: {digital_file.name} / 주문 {order.order_number} / 결제자 {payer_identifier}"
    return memo[:620] + '…' if len(memo) > 620 else memo


def create_pending_file_order(digital_file, user, *, reservation_seconds: int) -> FileOrder:
    reservation_expires_at = timezone.now() + timedelta(seconds=reservation_seconds)
    current_price = digital_file.current_price_sats
    is_discounted = digital_file.is_discount_active
    original_price = digital_file.price if is_discounted else None
    discount_rate = 0
    if is_discounted and digital_file.price:
        try:
            discount_rate = max(0, round((1 - (current_price / digital_file.price)) * 100))
        except ZeroDivisionError:
            discount_rate = 0

    return FileOrder.objects.create(
        digital_file=digital_file,
        user=user,
        price=current_price,
        status='pending',
        is_temporary_reserved=True,
        reservation_expires_at=reservation_expires_at,
        is_discounted=is_discounted,
        original_price=original_price,
        discount_rate=discount_rate,
    )


def finalize_file_order_from_transaction(order: FileOrder, *, payment_hash: str = '', payment_request: str = '') -> FileOrder:
    now = timezone.now()
    order.payment_hash = payment_hash
    order.payment_request = payment_request
    order.status = 'confirmed'
    order.is_temporary_reserved = False
    order.auto_cancelled_reason = ''
    if not order.paid_at:
        order.paid_at = now
    if not order.confirmed_at:
        order.confirmed_at = now
    if order.digital_file.download_expiry_days:
        order.download_expires_at = now + timedelta(days=order.digital_file.download_expiry_days)

    order.save(update_fields=[
        'payment_hash',
        'payment_request',
        'status',
        'is_temporary_reserved',
        'auto_cancelled_reason',
        'paid_at',
        'confirmed_at',
        'download_expires_at',
        'updated_at',
    ])
    return order


def serialize_file_transaction(transaction: PaymentTransaction) -> dict:
    logs = [
        {
            'stage': log.stage,
            'status': log.status,
            'message': log.message,
            'detail': log.detail,
            'created_at': log.created_at.isoformat(),
        }
        for log in transaction.stage_logs.order_by('created_at')
    ]

    payload = {
        'id': str(transaction.id),
        'status': transaction.status,
        'current_stage': transaction.current_stage,
        'payment_hash': transaction.payment_hash,
        'invoice_expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        'logs': logs,
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
    }

    if transaction.file_order:
        payload['order_number'] = transaction.file_order.order_number

    return payload


@login_required
@require_POST
def file_start_payment_workflow(request, store_id, file_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    digital_file = get_object_or_404(
        DigitalFile,
        id=file_id,
        store=store,
        deleted_at__isnull=True,
        is_active=True,
        is_temporarily_closed=False,
    )

    if digital_file.is_sold_out:
        return JsonResponse({
            'success': False,
            'error': '죄송합니다. 현재 파일이 매진되었습니다.',
            'error_code': 'inventory_unavailable',
        })

    confirmed_exists = FileOrder.objects.filter(
        digital_file=digital_file,
        user=request.user,
        status='confirmed',
    ).exists()
    if confirmed_exists:
        return JsonResponse({'success': False, 'error': '이미 파일을 구매하셨습니다.'}, status=400)

    amount_sats = int(digital_file.current_price_sats or 0)
    if amount_sats <= 0:
        return JsonResponse({'success': False, 'error': '결제 가능한 금액이 아닙니다.'}, status=400)

    from myshop.models import SiteSettings

    site_settings = SiteSettings.get_settings()
    reservation_seconds = max(120, site_settings.meetup_countdown_seconds)
    soft_lock_minutes = max(1, (reservation_seconds + 59) // 60)

    session_key = _get_file_payment_session_key(file_id)
    session_data = request.session.get(session_key, {})

    processor = LightningPaymentProcessor(store)

    previous_transaction_id = session_data.get('transaction_id')
    if previous_transaction_id:
        try:
            previous_transaction = PaymentTransaction.objects.select_related('file_order').get(
                id=previous_transaction_id,
                user=request.user,
                store=store,
            )
            if previous_transaction.status != PaymentTransaction.STATUS_COMPLETED:
                processor.cancel_transaction(previous_transaction, '디지털 파일 결제 재시작', detail={'reason': 'restart'})
                if previous_transaction.file_order and previous_transaction.file_order.status == 'pending':
                    order = previous_transaction.file_order
                    order.status = 'cancelled'
                    order.is_temporary_reserved = False
                    order.auto_cancelled_reason = '디지털 파일 결제 재시작'
                    order.save(update_fields=[
                        'status',
                        'is_temporary_reserved',
                        'auto_cancelled_reason',
                        'updated_at',
                    ])
        except (PaymentTransaction.DoesNotExist, ValueError):
            pass
        session_data = {}

    try:
        now = timezone.now()
        with transaction.atomic():
            locked_file = DigitalFile.objects.select_for_update().get(
                id=digital_file.id,
                store=store,
                deleted_at__isnull=True,
            )
            if locked_file.is_temporarily_closed:
                return JsonResponse({
                    'success': False,
                    'error': '현재 파일 판매가 일시 중단되었습니다.',
                    'error_code': 'inventory_unavailable',
                })

            active_reservations = []
            pending_reservations = (
                FileOrder.objects.select_for_update()
                .filter(
                    digital_file=locked_file,
                    status='pending',
                    is_temporary_reserved=True,
                )
            )
            for reservation in pending_reservations:
                expires_at = reservation.reservation_expires_at
                if expires_at and expires_at <= now:
                    reservation.status = 'cancelled'
                    reservation.is_temporary_reserved = False
                    reservation.auto_cancelled_reason = '예약 만료'
                    reservation.save(update_fields=[
                        'status',
                        'is_temporary_reserved',
                        'auto_cancelled_reason',
                        'updated_at',
                    ])
                    continue
                active_reservations.append(reservation)

            confirmed_count = locked_file.orders.filter(status='confirmed').count()
            total_reserved = confirmed_count + len(active_reservations)
            if locked_file.max_downloads and total_reserved >= locked_file.max_downloads:
                return JsonResponse({
                    'success': False,
                    'error': '죄송합니다. 현재 파일이 매진되었습니다.',
                    'error_code': 'inventory_unavailable',
                })

            FileOrder.objects.filter(
                digital_file=locked_file,
                user=request.user,
                status='pending',
            ).update(
                status='cancelled',
                is_temporary_reserved=False,
                auto_cancelled_reason='새로운 결제 시도로 자동 취소',
                updated_at=timezone.now(),
            )

            pending_order = create_pending_file_order(
                locked_file,
                request.user,
                reservation_seconds=reservation_seconds,
            )
    except DigitalFile.DoesNotExist:
        return JsonResponse({'success': False, 'error': '파일 정보를 찾을 수 없습니다.'}, status=404)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('디지털 파일 결제 준비 중 오류')
        return JsonResponse({'success': False, 'error': '결제 준비 중 오류가 발생했습니다.'}, status=500)

    digital_file = pending_order.digital_file

    try:
        payment_tx = processor.create_transaction(
            user=request.user,
            amount_sats=amount_sats,
            currency='BTC',
            cart_items=None,
            soft_lock_ttl_minutes=soft_lock_minutes,
            metadata={
                'file_id': digital_file.id,
                'file_order_id': pending_order.id,
            },
            prepare_message='디지털 파일 구매 준비 완료',
            prepare_detail={
                'file_order_id': pending_order.id,
                'reservation_expires_at': pending_order.reservation_expires_at.isoformat() if pending_order.reservation_expires_at else None,
                'amount_sats': amount_sats,
            },
        )
        payment_tx.file_order = pending_order
        payment_tx.save(update_fields=['file_order', 'updated_at'])

        invoice = processor.issue_invoice(
            payment_tx,
            memo=build_file_invoice_memo(digital_file, pending_order, request.user),
            expires_in_minutes=max(1, min(soft_lock_minutes, 15)),
        )
    except ValueError as exc:
        logger.warning('디지털 파일 결제 준비 실패: %s', exc)
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except RuntimeError as exc:
        logger.warning('디지털 파일 인보이스 생성 실패: %s', exc)
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('디지털 파일 결제 플로우 중 오류')
        return JsonResponse({'success': False, 'error': '결제 요청 처리 중 문제가 발생했습니다.'}, status=500)

    session_data = {
        'transaction_id': str(payment_tx.id),
        'file_order_id': pending_order.id,
        'payment_hash': invoice['payment_hash'],
        'payment_request': invoice['invoice'],
    }
    request.session[session_key] = session_data

    return JsonResponse({
        'success': True,
        'transaction': serialize_file_transaction(payment_tx),
        'invoice': {
            'payment_hash': invoice['payment_hash'],
            'payment_request': invoice['invoice'],
            'expires_at': invoice.get('expires_at').isoformat() if invoice.get('expires_at') else None,
        },
        'reservation_expires_at': pending_order.reservation_expires_at.isoformat() if pending_order.reservation_expires_at else None,
    })


@login_required
@require_http_methods(['GET'])
def file_payment_status(request, store_id, file_id, transaction_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    digital_file = get_object_or_404(
        DigitalFile,
        id=file_id,
        store=store,
        deleted_at__isnull=True,
    )

    try:
        transaction = PaymentTransaction.objects.select_related('file_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    payload = serialize_file_transaction(transaction)
    payload['file_id'] = digital_file.id

    return JsonResponse({'success': True, 'transaction': payload})


@login_required
@require_POST
def file_verify_payment(request, store_id, file_id, transaction_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    digital_file = get_object_or_404(
        DigitalFile,
        id=file_id,
        store=store,
        deleted_at__isnull=True,
    )

    try:
        transaction = PaymentTransaction.objects.select_related('file_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    processor = LightningPaymentProcessor(store)

    try:
        status_result = processor.check_user_payment(transaction)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('파일 결제 상태 확인 실패 transaction=%s', transaction_id)
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)

    status_value = status_result.get('status')
    session_key = _get_file_payment_session_key(file_id)
    session_data = request.session.get(session_key, {})

    if status_value == 'expired':
        processor.cancel_transaction(transaction, '인보이스 만료', detail=status_result)
        if transaction.file_order and transaction.file_order.status == 'pending':
            order = transaction.file_order
            order.status = 'cancelled'
            order.is_temporary_reserved = False
            order.auto_cancelled_reason = '인보이스 만료'
            order.save(update_fields=[
                'status',
                'is_temporary_reserved',
                'auto_cancelled_reason',
                'updated_at',
            ])
        session_data.pop('transaction_id', None)
        session_data.pop('payment_hash', None)
        session_data.pop('payment_request', None)
        session_data.pop('file_order_id', None)
        request.session[session_key] = session_data
        return JsonResponse({'success': False, 'error': '인보이스가 만료되었습니다.', 'transaction': serialize_file_transaction(transaction)}, status=400)

    if status_value != 'paid':
        return JsonResponse({'success': True, 'status': status_value, 'transaction': serialize_file_transaction(transaction)})

    file_order = transaction.file_order
    if not file_order and isinstance(transaction.metadata, dict):
        file_order_id = transaction.metadata.get('file_order_id')
        if file_order_id:
            file_order = FileOrder.objects.filter(id=file_order_id, user=request.user).first()

    if not file_order:
        return JsonResponse({'success': False, 'error': '주문 정보를 찾을 수 없습니다.'}, status=500)

    finalize_file_order_from_transaction(
        file_order,
        payment_hash=transaction.payment_hash,
        payment_request=transaction.payment_request,
    )

    settlement_payload = {'status': status_result.get('raw_status'), 'provider': 'blink'}
    processor.mark_settlement(transaction, tx_payload=settlement_payload)
    processor.finalize_file_order(transaction, file_order)

    try:
        send_file_buyer_confirmation_email(file_order)
        send_file_purchase_notification_email(file_order)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error('파일 결제 이메일 발송 실패 - order_id=%s, error=%s', file_order.id, exc)

    request.session.pop(session_key, None)

    redirect_url = reverse('file:file_complete', args=[file_order.id])

    payload = serialize_file_transaction(transaction)
    payload['redirect_url'] = redirect_url

    return JsonResponse({
        'success': True,
        'status': status_value,
        'transaction': payload,
        'order': {
            'id': file_order.id,
            'order_number': file_order.order_number,
            'price': file_order.price,
        },
        'redirect_url': redirect_url,
    })


@login_required
@require_POST
def file_cancel_payment(request, store_id, file_id, transaction_id):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)

    try:
        transaction = PaymentTransaction.objects.select_related('file_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    processor = LightningPaymentProcessor(store)
    processor.cancel_transaction(transaction, '사용자 취소', detail=payload)

    if transaction.file_order and transaction.file_order.status == 'pending':
        order = transaction.file_order
        order.status = 'cancelled'
        order.is_temporary_reserved = False
        order.auto_cancelled_reason = '사용자 취소'
        order.save(update_fields=[
            'status',
            'is_temporary_reserved',
            'auto_cancelled_reason',
            'updated_at',
        ])

    session_key = _get_file_payment_session_key(file_id)
    request.session.pop(session_key, None)

    return JsonResponse({'success': True, 'transaction': serialize_file_transaction(transaction)})


@login_required
def download_file(request, store_id, file_id):
    """파일 다운로드"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    digital_file = get_object_or_404(
        DigitalFile,
        id=file_id,
        store=store,
        deleted_at__isnull=True
    )
    
    # 권한 확인
    is_owner = request.user == store.owner or request.user.is_staff
    
    if not is_owner:
        # 구매 확인
        order = FileOrder.objects.filter(
            digital_file=digital_file,
            user=request.user,
            status='confirmed'
        ).first()
        
        if not order:
            messages.error(request, "파일을 구매하지 않으셨습니다.")
            return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)
        
        if not order.can_download:
            if order.is_download_expired:
                messages.error(request, "다운로드 기간이 만료되었습니다.")
            else:
                messages.error(request, "파일을 다운로드할 수 없습니다.")
            return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)
        
        # 다운로드 클릭 추적 업데이트
        if not order.download_clicked:
            order.download_clicked = True
            order.download_clicked_at = timezone.now()
        order.download_click_count += 1
        order.save(update_fields=['download_clicked', 'download_clicked_at', 'download_click_count'])
        
        # 다운로드 로그 기록
        FileDownloadLog.objects.create(
            order=order,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    # 파일 전송
    try:
        # S3 Storage를 사용하는 경우
        if hasattr(digital_file.file.storage, 'client'):
            # S3에서 파일 다운로드
            try:
                file_obj = digital_file.file.storage._open(digital_file.file.name)
                
                # MIME 타입 추측
                content_type, _ = mimetypes.guess_type(digital_file.original_filename)
                if content_type is None:
                    content_type = 'application/octet-stream'
                
                # PNG 등 이미지 파일도 다운로드되도록 설정
                if digital_file.original_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    content_type = 'application/octet-stream'
                
                response = FileResponse(
                    file_obj,
                    content_type=content_type
                )
                
                # 파일명 처리 - ASCII가 아닌 문자가 있는지 확인
                try:
                    digital_file.original_filename.encode('ascii')
                    # ASCII 파일명인 경우
                    response['Content-Disposition'] = f'attachment; filename="{digital_file.original_filename}"'
                except UnicodeEncodeError:
                    # 한글 등 non-ASCII 파일명인 경우
                    encoded_filename = urllib.parse.quote(digital_file.original_filename)
                    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'
                
                return response
            except Exception as e:
                logger.error(f"S3 파일 다운로드 오류: {e}", exc_info=True)
                raise Http404("파일을 찾을 수 없습니다.")
        else:
            # 로컬 파일 시스템 사용
            file_path = digital_file.file.path
            if os.path.exists(file_path):
                # MIME 타입 추측
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = 'application/octet-stream'
                
                # PNG 등 이미지 파일도 다운로드되도록 설정
                if digital_file.original_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    content_type = 'application/octet-stream'
                
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=content_type
                )
                
                # 파일명 처리 - ASCII가 아닌 문자가 있는지 확인
                try:
                    digital_file.original_filename.encode('ascii')
                    # ASCII 파일명인 경우
                    response['Content-Disposition'] = f'attachment; filename="{digital_file.original_filename}"'
                except UnicodeEncodeError:
                    # 한글 등 non-ASCII 파일명인 경우
                    encoded_filename = urllib.parse.quote(digital_file.original_filename)
                    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'
                
                return response
            else:
                raise Http404("파일을 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"파일 다운로드 오류: {e}", exc_info=True)
        messages.error(request, "파일 다운로드 중 오류가 발생했습니다.")
        return redirect('file:file_detail', store_id=store.store_id, file_id=digital_file.id)


@login_required
@require_POST
@csrf_exempt
def toggle_file_temporary_closure(request, store_id, file_id):
    """파일 일시중단 토글"""
    try:
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        
        digital_file = get_object_or_404(
            DigitalFile,
            id=file_id,
            store=store,
            deleted_at__isnull=True
        )
        
        # 일시중단 상태 토글
        digital_file.is_temporarily_closed = not digital_file.is_temporarily_closed
        digital_file.save()
        
        return JsonResponse({
            'success': True,
            'is_temporarily_closed': digital_file.is_temporarily_closed,
            'message': '일시중단되었습니다.' if digital_file.is_temporarily_closed else '판매가 재개되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"파일 일시중단 토글 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '상태 변경 중 오류가 발생했습니다.'
        })


@login_required
def file_complete(request, order_id):
    """파일 구매 완료 페이지"""
    order = get_object_or_404(
        FileOrder,
        id=order_id,
        user=request.user,
        status='confirmed'
    )
    
    context = {
        'order': order,
        'store': order.digital_file.store,
        'file': order.digital_file,
    }
    return render(request, 'file/file_complete.html', context)
