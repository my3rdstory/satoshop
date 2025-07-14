from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db import transaction
from datetime import timedelta
import json
import logging
import os
import mimetypes

from stores.models import Store
from .models import DigitalFile, FileOrder, FileDownloadLog
from .forms import DigitalFileForm
from .services import (
    send_file_purchase_notification_email,
    send_file_buyer_confirmation_email
)

logger = logging.getLogger(__name__)


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
    """파일 추가"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    if request.method == 'POST':
        form = DigitalFileForm(request.POST, request.FILES)
        if form.is_valid():
            digital_file = form.save(commit=False)
            digital_file.store = store
            digital_file.save()
            
            messages.success(request, f"파일 '{digital_file.name}'이(가) 성공적으로 등록되었습니다.")
            return redirect('file:file_manage', store_id=store.id)
    else:
        form = DigitalFileForm()
    
    context = {
        'store': store,
        'form': form,
        'is_owner': True,
    }
    return render(request, 'file/add_file.html', context)


@login_required
def edit_file(request, store_id, file_id):
    """파일 수정"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    digital_file = get_object_or_404(DigitalFile, id=file_id, store=store, deleted_at__isnull=True)
    
    if request.method == 'POST':
        form = DigitalFileForm(request.POST, request.FILES, instance=digital_file)
        if form.is_valid():
            form.save()
            messages.success(request, f"파일 '{digital_file.name}'이(가) 성공적으로 수정되었습니다.")
            return redirect('file:file_manage', store_id=store.id)
    else:
        form = DigitalFileForm(instance=digital_file)
    
    context = {
        'store': store,
        'form': form,
        'digital_file': digital_file,
        'is_owner': True,
    }
    return render(request, 'file/edit_file.html', context)


@login_required
def delete_file(request, store_id, file_id):
    """파일 삭제 (소프트 삭제)"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        messages.error(request, "스토어에 접근할 권한이 없습니다.")
        return redirect('stores:store_detail', store_id=store_id)
    
    digital_file = get_object_or_404(DigitalFile, id=file_id, store=store, deleted_at__isnull=True)
    
    if request.method == 'POST':
        digital_file.deleted_at = timezone.now()
        digital_file.is_active = False
        digital_file.save()
        messages.success(request, f"파일 '{digital_file.name}'이(가) 삭제되었습니다.")
        return redirect('file:file_manage', store_id=store.id)
    
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
    
    # 페이지네이션
    paginator = Paginator(queryset, 12)
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
    digital_file = get_object_or_404(DigitalFile, id=file_id, store=store, deleted_at__isnull=True)
    
    is_owner = request.user.is_authenticated and (request.user == store.owner or request.user.is_staff)
    
    # 일반 사용자는 활성화된 파일만 볼 수 있음
    if not is_owner and (not digital_file.is_active or digital_file.is_temporarily_closed):
        raise Http404("파일을 찾을 수 없습니다.")
    
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
    
    context = {
        'store': store,
        'file': digital_file,
        'is_owner': is_owner,
        'has_purchased': has_purchased,
        'can_download': can_download,
        'user_order': user_order,
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
        download_count=Count('orders__download_logs')
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
def file_checkout(request, store_id, file_id):
    """파일 구매 체크아웃"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    digital_file = get_object_or_404(
        DigitalFile, 
        id=file_id, 
        store=store, 
        deleted_at__isnull=True,
        is_active=True,
        is_temporarily_closed=False
    )
    
    # 이미 구매했는지 확인
    existing_order = FileOrder.objects.filter(
        digital_file=digital_file,
        user=request.user,
        status='confirmed'
    ).first()
    
    if existing_order:
        messages.info(request, "이미 구매하신 파일입니다.")
        return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)
    
    # 매진 확인
    if digital_file.is_sold_out:
        messages.error(request, "죄송합니다. 매진되었습니다.")
        return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)
    
    # 무료 파일인 경우 즉시 확정
    if digital_file.price_display == 'free':
        with transaction.atomic():
            order = FileOrder.objects.create(
                digital_file=digital_file,
                user=request.user,
                price=0,
                status='confirmed',
                is_temporary_reserved=False,
                confirmed_at=timezone.now()
            )
            
            # 이메일 발송
            try:
                send_file_buyer_confirmation_email(order)
                send_file_purchase_notification_email(order)
            except Exception as e:
                logger.error(f"이메일 발송 실패: {e}")
            
            messages.success(request, "무료 파일이 다운로드 가능합니다.")
            return redirect('file:file_complete', order_id=order.id)
    
    # 유료 파일 체크아웃
    context = {
        'store': store,
        'file': digital_file,
        'price_sats': digital_file.current_price_sats,
    }
    return render(request, 'file/file_checkout.html', context)


@login_required
@require_POST
@csrf_exempt
def create_file_invoice(request):
    """파일 구매 인보이스 생성"""
    import requests
    from django.conf import settings
    
    try:
        data = json.loads(request.body)
        file_id = data.get('file_id')
        
        if not file_id:
            return JsonResponse({
                'success': False,
                'error': '파일 ID가 필요합니다.'
            })
        
        digital_file = get_object_or_404(
            DigitalFile,
            id=file_id,
            deleted_at__isnull=True,
            is_active=True,
            is_temporarily_closed=False
        )
        
        # 이미 구매했는지 확인
        existing_order = FileOrder.objects.filter(
            digital_file=digital_file,
            user=request.user,
            status='confirmed'
        ).first()
        
        if existing_order:
            return JsonResponse({
                'success': False,
                'error': '이미 구매하신 파일입니다.'
            })
        
        # 매진 확인
        if digital_file.is_sold_out:
            return JsonResponse({
                'success': False,
                'error': '죄송합니다. 매진되었습니다.'
            })
        
        # 기존 pending 주문 취소
        FileOrder.objects.filter(
            digital_file=digital_file,
            user=request.user,
            status='pending'
        ).update(
            status='cancelled',
            auto_cancelled_reason='새로운 주문 생성으로 자동 취소'
        )
        
        # 현재 가격 계산
        current_price = digital_file.current_price_sats
        is_discounted = digital_file.is_discount_active
        
        # 주문 생성
        with transaction.atomic():
            order = FileOrder.objects.create(
                digital_file=digital_file,
                user=request.user,
                price=current_price,
                is_discounted=is_discounted,
                original_price=digital_file.price if is_discounted else None,
                discount_rate=round((1 - current_price / digital_file.price) * 100) if is_discounted and digital_file.price > 0 else 0
            )
            
            # Blink 인보이스 생성
            headers = {
                'X-API-KEY': settings.BLINK_API_KEY,
                'Content-Type': 'application/json'
            }
            
            invoice_data = {
                'amount': current_price,
                'memo': f"파일 구매: {digital_file.name} - {order.order_number}"
            }
            
            response = requests.post(
                f"{settings.BLINK_API_URL}/invoices",
                headers=headers,
                json=invoice_data,
                timeout=10
            )
            
            if response.status_code == 200:
                invoice_data = response.json()
                order.payment_hash = invoice_data.get('payment_hash', '')
                order.payment_request = invoice_data.get('payment_request', '')
                order.save()
                
                return JsonResponse({
                    'success': True,
                    'payment_request': order.payment_request,
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'expires_at': order.reservation_expires_at.isoformat()
                })
            else:
                order.delete()
                return JsonResponse({
                    'success': False,
                    'error': '결제 요청 생성에 실패했습니다.'
                })
                
    except Exception as e:
        logger.error(f"인보이스 생성 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '인보이스 생성 중 오류가 발생했습니다.'
        })


@login_required
@require_POST  
@csrf_exempt
def check_file_payment(request):
    """파일 구매 결제 상태 확인"""
    import requests
    from django.conf import settings
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({
                'success': False,
                'error': '주문 ID가 필요합니다.'
            })
        
        order = get_object_or_404(
            FileOrder,
            id=order_id,
            user=request.user,
            status='pending'
        )
        
        # 예약 만료 확인
        if order.reservation_expires_at and timezone.now() > order.reservation_expires_at:
            order.status = 'cancelled'
            order.auto_cancelled_reason = '예약 시간 만료'
            order.save()
            return JsonResponse({
                'success': False,
                'paid': False,
                'error': '예약 시간이 만료되었습니다.'
            })
        
        # Blink API로 결제 상태 확인
        headers = {
            'X-API-KEY': settings.BLINK_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{settings.BLINK_API_URL}/invoices/{order.payment_hash}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            invoice_data = response.json()
            is_paid = invoice_data.get('is_paid', False)
            
            if is_paid:
                with transaction.atomic():
                    order.status = 'confirmed'
                    order.paid_at = timezone.now()
                    order.confirmed_at = timezone.now()
                    order.is_temporary_reserved = False
                    order.save()
                    
                    # 이메일 발송
                    try:
                        send_file_buyer_confirmation_email(order)
                        send_file_purchase_notification_email(order)
                    except Exception as e:
                        logger.error(f"이메일 발송 실패: {e}")
                
                return JsonResponse({
                    'success': True,
                    'paid': True,
                    'redirect_url': reverse('file:file_complete', kwargs={'order_id': order.id})
                })
            else:
                return JsonResponse({
                    'success': True,
                    'paid': False
                })
        else:
            return JsonResponse({
                'success': False,
                'error': '결제 상태 확인에 실패했습니다.'
            })
            
    except Exception as e:
        logger.error(f"결제 상태 확인 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '결제 상태 확인 중 오류가 발생했습니다.'
        })


@login_required
@require_POST
@csrf_exempt
def cancel_file_payment(request):
    """파일 구매 취소"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({
                'success': False,
                'error': '주문 ID가 필요합니다.'
            })
        
        order = get_object_or_404(
            FileOrder,
            id=order_id,
            user=request.user,
            status='pending'
        )
        
        order.status = 'cancelled'
        order.auto_cancelled_reason = '사용자 취소'
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': '주문이 취소되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"주문 취소 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '주문 취소 중 오류가 발생했습니다.'
        })


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
        
        # 다운로드 로그 기록
        FileDownloadLog.objects.create(
            order=order,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    # 파일 전송
    try:
        file_path = digital_file.file.path
        if os.path.exists(file_path):
            # MIME 타입 추측
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{digital_file.original_filename}"'
            return response
        else:
            raise Http404("파일을 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"파일 다운로드 오류: {e}", exc_info=True)
        messages.error(request, "파일 다운로드 중 오류가 발생했습니다.")
        return redirect('file:file_detail', store_id=store.id, file_id=digital_file.id)


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