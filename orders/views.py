from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import csv
import json
import logging

from stores.models import Store
from products.models import Product, ProductOption, ProductOptionChoice
from .models import Cart, CartItem, Order, OrderItem, PurchaseHistory, Invoice
from stores.decorators import store_owner_required
from ln_payment.blink_service import get_blink_service_for_store

logger = logging.getLogger(__name__)


@login_required
def cart_view(request):
    """장바구니 보기"""
    cart_items = []
    cart = None
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all().select_related('product', 'product__store')
        except Cart.DoesNotExist:
            pass
    
    # store_base.html을 위한 기본 store 설정
    # 장바구니에 상품이 있으면 첫 번째 상품의 스토어를 사용
    # 없으면 기본값 설정
    store = None
    if cart_items:
        store = cart_items[0].product.store
    else:
        # 기본 스토어 정보 (빈 장바구니일 때)
        class DummyStore:
            store_id = ''
            store_name = 'SatoShop'
            store_description = ''
            owner_name = ''
            owner_phone = ''
            owner_email = ''
            chat_channel = ''
        store = DummyStore()
    
    # 템플릿에서 사용할 추가 변수들 계산
    cart_items_count = len(cart_items) if cart_items else 0
    cart_total_amount = cart.total_amount if cart else 0
    
    context = {
        'cart_items': cart_items,
        'cart': cart,
        'store': store,
        'cart_items_count': cart_items_count,
        'cart_total_amount': cart_total_amount,
    }
    return render(request, 'orders/cart.html', context)


@login_required
def cart_api(request):
    """장바구니 내용을 JSON으로 반환하는 API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'GET 요청만 허용됩니다.'})
    
    try:
        cart_items = []
        cart = None
        
        if request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
                cart_items_qs = cart.items.all().select_related('product', 'product__store')
                
                # 스토어별로 그룹화
                stores_data = {}
                for item in cart_items_qs:
                    store_id = item.product.store.store_id
                    if store_id not in stores_data:
                        stores_data[store_id] = {
                            'store_name': item.product.store.store_name,
                            'store_id': store_id,
                            'items': []
                        }
                    
                    # 옵션 정보 처리 (템플릿과 동일한 구조로)
                    options_display = []
                    if item.selected_options:
                        for option_id, choice_id in item.selected_options.items():
                            try:
                                option = ProductOption.objects.get(id=option_id)
                                choice = ProductOptionChoice.objects.get(id=choice_id)
                                options_display.append({
                                    'option_name': option.name,
                                    'choice_name': choice.name,
                                    'choice_price': choice.price
                                })
                            except:
                                pass
                    
                    # 상품 이미지 URL 처리
                    product_image_url = None
                    if item.product.images.first():
                        product_image_url = item.product.images.first().file_url
                    
                    stores_data[store_id]['items'].append({
                        'id': item.id,
                        'product': {
                            'title': item.product.title,
                            'images': {'first': {'file_url': product_image_url} if product_image_url else None}
                        },
                        'quantity': item.quantity,
                        'total_price': item.total_price,
                        'options_display': options_display
                    })
                
                cart_items = list(stores_data.values())
            except Cart.DoesNotExist:
                pass
        
        # 총 개수 및 총 금액 계산
        total_items = sum(len(store['items']) for store in cart_items)
        total_amount = cart.total_amount if cart else 0
        
        return JsonResponse({
            'success': True,
            'cart_items': cart_items,
            'total_items': total_items,
            'total_amount': total_amount
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def add_to_cart(request):
    """장바구니에 상품 추가"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST 요청만 허용됩니다.'})
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        selected_options = data.get('selected_options', {})
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # 장바구니 가져오기 또는 생성
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # 항상 새 항목으로 추가 (개별 목록 표시를 위해)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            selected_options=selected_options
        )
        
        # 장바구니 총 개수 및 총 금액 계산
        total_items = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        total_amount = cart.total_amount
        
        return JsonResponse({
            'success': True,
            'message': '상품이 장바구니에 추가되었습니다.',
            'cart_count': total_items,
            'cart_total_amount': total_amount
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def remove_from_cart(request, item_id=None):
    """장바구니에서 상품 제거"""
    if request.method == 'POST':
        try:
            # JSON 요청 처리
            if request.content_type == 'application/json':
                import json
                data = json.loads(request.body)
                item_id = data.get('item_id')
            
            if not item_id:
                return JsonResponse({'success': False, 'error': '아이템 ID가 필요합니다.'})
            
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart_item.delete()
            
            return JsonResponse({
                'success': True,
                'message': '상품이 장바구니에서 제거되었습니다.'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET 요청 (기존 방식 유지)
    if item_id:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        messages.success(request, '상품이 장바구니에서 제거되었습니다.')
    
    return redirect('orders:cart_view')


@login_required
def update_cart_item(request, item_id):
    """장바구니 상품 수량 업데이트"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST 요청만 허용됩니다.'})
    
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@store_owner_required
def order_management(request, store_id):
    """주문 관리"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # 현재 월 파라미터 처리
    from datetime import datetime
    import calendar
    
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # 선택된 월의 시작과 끝
    month_start = timezone.datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
    if month == 12:
        month_end = timezone.datetime(year + 1, 1, 1, tzinfo=timezone.get_current_timezone())
    else:
        month_end = timezone.datetime(year, month + 1, 1, tzinfo=timezone.get_current_timezone())
    
    # 스토어 생성월 확인
    store_created = store.created_at
    store_year = store_created.year
    store_month = store_created.month
    
    # 현재 월 확인
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    
    # 이전/다음 월 계산
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    # 이전/다음 버튼 표시 여부
    show_prev = not (prev_year < store_year or (prev_year == store_year and prev_month < store_month))
    show_next = not (next_year > current_year or (next_year == current_year and next_month > current_month))
    
    # 선택된 월 통계
    monthly_orders = Order.objects.filter(
        items__product__store=store,
        created_at__gte=month_start,
        created_at__lt=month_end
    ).distinct()
    
    monthly_orders_count = monthly_orders.count()
    monthly_revenue = monthly_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # 상품별 판매 현황 (선택된 월 기준)
    from django.db.models import F
    products_with_orders = Product.objects.filter(
        store=store
    ).annotate(
        total_orders=Count('orderitem__order', distinct=True, filter=Q(
            orderitem__order__created_at__gte=month_start,
            orderitem__order__created_at__lt=month_end
        )),
        total_quantity=Sum('orderitem__quantity', filter=Q(
            orderitem__order__created_at__gte=month_start,
            orderitem__order__created_at__lt=month_end
        )),
        total_revenue=Sum(
            F('orderitem__quantity') * (F('orderitem__product_price') + F('orderitem__options_price')),
            filter=Q(
                orderitem__order__created_at__gte=month_start,
                orderitem__order__created_at__lt=month_end
            )
        )
    ).filter(total_orders__gt=0).order_by('-total_revenue')
    
    context = {
        'store': store,
        'monthly_orders_count': monthly_orders_count,
        'monthly_revenue': monthly_revenue,
        'products_with_orders': products_with_orders,
        'current_year': year,
        'current_month': month,
        'current_month_name': calendar.month_name[month],
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'show_prev': show_prev,
        'show_next': show_next,
    }
    return render(request, 'orders/order_management.html', context)


@login_required
@store_owner_required
def product_orders(request, store_id, product_id):
    """특정 상품의 주문 목록"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    order_items = OrderItem.objects.filter(
        product=product
    ).select_related('order').order_by('-order__created_at')
    
    paginator = Paginator(order_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'store': store,
        'product': product,
        'page_obj': page_obj,
    }
    return render(request, 'orders/product_orders.html', context)


@login_required
@store_owner_required
def export_orders_csv(request, store_id):
    """주문 데이터 엑셀 내보내기 (배송 정보 포함)"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        import io
        
        # 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "주문 목록"
        
        # 헤더 스타일
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # 헤더 작성
        headers = [
            '주문번호', '상품명', '수량', '단가', '총액', '주문일시', '상태',
            '주문자명', '연락처', '이메일', '우편번호', '주소', '상세주소', '요청사항'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 데이터 조회
        order_items = OrderItem.objects.filter(
            product__store=store
        ).select_related('order', 'product').order_by('-order__created_at')
        
        # 데이터 작성
        for row, item in enumerate(order_items, 2):
            order = item.order
            ws.cell(row=row, column=1, value=order.order_number)
            ws.cell(row=row, column=2, value=item.product_title)
            ws.cell(row=row, column=3, value=item.quantity)
            ws.cell(row=row, column=4, value=item.product_price)
            ws.cell(row=row, column=5, value=item.total_price)
            ws.cell(row=row, column=6, value=order.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            ws.cell(row=row, column=7, value=order.get_status_display())
            ws.cell(row=row, column=8, value=order.buyer_name)
            ws.cell(row=row, column=9, value=order.buyer_phone)
            ws.cell(row=row, column=10, value=order.buyer_email)
            ws.cell(row=row, column=11, value=order.shipping_postal_code)
            ws.cell(row=row, column=12, value=order.shipping_address)
            ws.cell(row=row, column=13, value=order.shipping_detail_address)
            ws.cell(row=row, column=14, value=order.order_memo)
        
        # 열 너비 자동 조정
        for col in range(1, len(headers) + 1):
            column_letter = get_column_letter(col)
            ws.column_dimensions[column_letter].width = 15
        
        # 메모리에 엑셀 파일 저장
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        # HTTP 응답 생성
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{store.store_id}_orders_with_shipping.xlsx"'
        
        return response
    
    except ImportError:
        # openpyxl이 없으면 기존 CSV 방식 사용
        logger.warning("openpyxl 라이브러리가 없어 CSV로 다운로드됩니다.")
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{store.store_id}_orders.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel
        
        writer = csv.writer(response)
        writer.writerow([
            '주문번호', '상품명', '수량', '단가', '총액', '주문일시', '상태',
            '주문자명', '연락처', '이메일', '우편번호', '주소', '상세주소', '요청사항'
        ])
        
        order_items = OrderItem.objects.filter(
            product__store=store
        ).select_related('order', 'product').order_by('-order__created_at')
        
        for item in order_items:
            order = item.order
            writer.writerow([
                order.order_number,
                item.product_title,
                item.quantity,
                item.product_price,
                item.total_price,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.get_status_display(),
                order.buyer_name,
                order.buyer_phone,
                order.buyer_email,
                order.shipping_postal_code,
                order.shipping_address,
                order.shipping_detail_address,
                order.order_memo,
            ])
        
        return response


@login_required
@store_owner_required
def export_product_orders_csv(request, store_id, product_id):
    """특정 상품의 주문 데이터 엑셀 내보내기 (배송 정보 포함)"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        import io
        
        # 워크북 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{product.title} 주문목록"
        
        # 헤더 스타일
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # 헤더 작성
        headers = [
            '주문번호', '주문자', '수량', '단가', '옵션가격', '총액', '주문일시', '상태', '선택옵션',
            '연락처', '이메일', '우편번호', '주소', '상세주소', '요청사항'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 데이터 조회
        order_items = OrderItem.objects.filter(
            product=product
        ).select_related('order').order_by('-order__created_at')
        
        # 데이터 작성
        for row, item in enumerate(order_items, 2):
            order = item.order
            
            # 선택된 옵션을 문자열로 변환
            options_str = ''
            if item.selected_options:
                options_list = []
                for key, value in item.selected_options.items():
                    options_list.append(f"{key}: {value}")
                options_str = ', '.join(options_list)
            
            ws.cell(row=row, column=1, value=order.order_number)
            ws.cell(row=row, column=2, value=order.buyer_name)
            ws.cell(row=row, column=3, value=item.quantity)
            ws.cell(row=row, column=4, value=item.product_price)
            ws.cell(row=row, column=5, value=item.options_price)
            ws.cell(row=row, column=6, value=item.total_price)
            ws.cell(row=row, column=7, value=order.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            ws.cell(row=row, column=8, value=order.get_status_display())
            ws.cell(row=row, column=9, value=options_str)
            ws.cell(row=row, column=10, value=order.buyer_phone)
            ws.cell(row=row, column=11, value=order.buyer_email)
            ws.cell(row=row, column=12, value=order.shipping_postal_code)
            ws.cell(row=row, column=13, value=order.shipping_address)
            ws.cell(row=row, column=14, value=order.shipping_detail_address)
            ws.cell(row=row, column=15, value=order.order_memo)
        
        # 열 너비 자동 조정
        for col in range(1, len(headers) + 1):
            column_letter = get_column_letter(col)
            ws.column_dimensions[column_letter].width = 15
        
        # 메모리에 엑셀 파일 저장
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        # HTTP 응답 생성
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{store.store_id}_{product.title}_orders_with_shipping.xlsx"'
        
        return response
    
    except ImportError:
        # openpyxl이 없으면 기존 CSV 방식 사용
        logger.warning("openpyxl 라이브러리가 없어 CSV로 다운로드됩니다.")
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{store.store_id}_{product.title}_orders.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel
        
        writer = csv.writer(response)
        writer.writerow([
            '주문번호', '주문자', '수량', '단가', '옵션가격', '총액', '주문일시', '상태', '선택옵션',
            '연락처', '이메일', '우편번호', '주소', '상세주소', '요청사항'
        ])
        
        order_items = OrderItem.objects.filter(
            product=product
        ).select_related('order').order_by('-order__created_at')
        
        for item in order_items:
            order = item.order
            
            # 선택된 옵션을 문자열로 변환
            options_str = ''
            if item.selected_options:
                options_list = []
                for key, value in item.selected_options.items():
                    options_list.append(f"{key}: {value}")
                options_str = ', '.join(options_list)
            
            writer.writerow([
                order.order_number,
                order.buyer_name,
                item.quantity,
                item.product_price,
                item.options_price,
                item.total_price,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.get_status_display(),
                options_str,
                order.buyer_phone,
                order.buyer_email,
                order.shipping_postal_code,
                order.shipping_address,
                order.shipping_detail_address,
                order.order_memo,
            ])
        
        return response


@login_required
def my_purchases(request):
    """구매 내역 목록"""
    purchases = PurchaseHistory.objects.filter(user=request.user).select_related(
        'order', 'order__store'
    ).prefetch_related(
        'order__items', 'order__items__product', 'order__items__product__images'
    ).order_by('-purchase_date')
    
    context = {
        'purchases': purchases,
    }
    return render(request, 'orders/my_purchases.html', context)


@login_required
def purchase_detail(request, order_number):
    """구매 상세 정보"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'orders/purchase_detail.html', context)


@login_required
def shipping_info(request):
    """배송 정보 입력 페이지"""
    cart_items = []
    cart = None
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all().select_related('product', 'product__store')
        except Cart.DoesNotExist:
            messages.error(request, '장바구니가 비어있습니다.')
            return redirect('myshop:home')
    
    if not cart_items:
        messages.error(request, '장바구니가 비어있습니다.')
        return redirect('myshop:home')
    
    if request.method == 'POST':
        # 배송 정보를 세션에 저장
        shipping_data = {
            'buyer_name': request.POST.get('buyer_name', '').strip(),
            'buyer_phone': request.POST.get('buyer_phone', '').strip(),
            'buyer_email': request.POST.get('buyer_email', '').strip(),
            'shipping_postal_code': request.POST.get('shipping_postal_code', '').strip(),
            'shipping_address': request.POST.get('shipping_address', '').strip(),
            'shipping_detail_address': request.POST.get('shipping_detail_address', '').strip(),
            'order_memo': request.POST.get('order_memo', '').strip(),
        }
        
        # 필수 필드 검증
        required_fields = ['buyer_name', 'buyer_phone', 'buyer_email', 'shipping_postal_code', 'shipping_address']
        missing_fields = []
        for field in required_fields:
            if not shipping_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            messages.error(request, '필수 정보를 모두 입력해주세요.')
            
            # 스토어별로 그룹화하여 배송비 계산 (에러 시에도 필요)
            from itertools import groupby
            stores_with_items = []
            total_shipping_fee = 0
            
            cart_items_sorted = cart_items.order_by('product__store__store_name', '-added_at')
            
            for store, items in groupby(cart_items_sorted, key=lambda x: x.product.store):
                store_items = list(items)
                store_subtotal = sum(item.total_price for item in store_items)
                
                # 스토어별 배송비 계산 (스토어 내 상품 중 최대 배송비 사용)
                store_shipping_fee = max(item.product.display_shipping_fee for item in store_items) if store_items else 0
                store_total = store_subtotal + store_shipping_fee
                total_shipping_fee += store_shipping_fee
                
                stores_with_items.append({
                    'store': store,
                    'items': store_items,
                    'subtotal': store_subtotal,
                    'shipping_fee': store_shipping_fee,
                    'total': store_total
                })
            
            # 전체 총액 계산
            subtotal_amount = sum(store_data['subtotal'] for store_data in stores_with_items)
            total_amount = subtotal_amount + total_shipping_fee
            
            context = {
                'cart': cart,
                'cart_items': cart_items,
                'stores_with_items': stores_with_items,
                'subtotal_amount': subtotal_amount,
                'total_shipping_fee': total_shipping_fee,
                'total_amount': total_amount,
                'form_data': shipping_data,
                'store': cart_items[0].product.store if cart_items else None,
            }
            return render(request, 'orders/shipping_info.html', context)
        
        # 세션에 배송 정보 저장
        request.session['shipping_data'] = shipping_data
        return redirect('orders:checkout')
    
    # 스토어별로 그룹화하여 배송비 계산
    from itertools import groupby
    stores_with_items = []
    total_shipping_fee = 0
    
    cart_items_sorted = cart_items.order_by('product__store__store_name', '-added_at')
    
    for store, items in groupby(cart_items_sorted, key=lambda x: x.product.store):
        store_items = list(items)
        store_subtotal = sum(item.total_price for item in store_items)
        
        # 스토어별 배송비 계산 (스토어 내 상품 중 최대 배송비 사용)
        store_shipping_fee = max(item.product.display_shipping_fee for item in store_items) if store_items else 0
        store_total = store_subtotal + store_shipping_fee
        total_shipping_fee += store_shipping_fee
        
        stores_with_items.append({
            'store': store,
            'items': store_items,
            'subtotal': store_subtotal,
            'shipping_fee': store_shipping_fee,
            'total': store_total
        })
    
    # 전체 총액 계산
    subtotal_amount = sum(store_data['subtotal'] for store_data in stores_with_items)
    total_amount = subtotal_amount + total_shipping_fee
    
    # store_base.html을 위한 기본 store 설정
    store = cart_items[0].product.store if cart_items else None
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'stores_with_items': stores_with_items,
        'subtotal_amount': subtotal_amount,
        'total_shipping_fee': total_shipping_fee,
        'total_amount': total_amount,
        'store': store,
    }
    return render(request, 'orders/shipping_info.html', context)


@login_required
def checkout(request):
    """주문/결제 페이지"""
    # 배송 정보가 세션에 있는지 확인
    if 'shipping_data' not in request.session:
        messages.error(request, '배송 정보를 먼저 입력해주세요.')
        return redirect('orders:shipping_info')
    
    cart_items = []
    cart = None
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all().select_related('product', 'product__store').order_by('product__store__store_name', '-added_at')
        except Cart.DoesNotExist:
            messages.error(request, '장바구니가 비어있습니다.')
            return redirect('myshop:home')
    
    if not cart_items:
        messages.error(request, '장바구니가 비어있습니다.')
        return redirect('myshop:home')
    
    # 스토어별로 그룹화
    from itertools import groupby
    stores_with_items = []
    total_shipping_fee = 0
    
    if settings.DEBUG:
        logger.debug(f"[CHECKOUT] 장바구니 아이템 수: {len(cart_items)}")
    
    for store, items in groupby(cart_items, key=lambda x: x.product.store):
        store_items = list(items)
        store_subtotal = sum(item.total_price for item in store_items)
        
        # 스토어별 배송비 계산 (스토어 내 상품 중 최대 배송비 사용)
        store_shipping_fee = max(item.product.display_shipping_fee for item in store_items) if store_items else 0
        store_total = store_subtotal + store_shipping_fee
        total_shipping_fee += store_shipping_fee
        
        if settings.DEBUG:
            logger.debug(f"[CHECKOUT] 스토어: {store.store_name}")
            logger.debug(f"[CHECKOUT]   - 상품 수: {len(store_items)}")
            logger.debug(f"[CHECKOUT]   - 상품 소계: {store_subtotal} sats")
            logger.debug(f"[CHECKOUT]   - 배송비: {store_shipping_fee} sats (최대 배송비)")
            logger.debug(f"[CHECKOUT]   - 스토어 총액: {store_total} sats")
            for item in store_items:
                logger.debug(f"[CHECKOUT]     * {item.product.title}: {item.quantity}개 x {item.unit_price} = {item.total_price} sats")
                logger.debug(f"[CHECKOUT]       배송비 정보: shipping_fee={item.product.shipping_fee}, display_shipping_fee={item.product.display_shipping_fee}")
        
        stores_with_items.append({
            'store': store,
            'items': store_items,
            'subtotal': store_subtotal,
            'shipping_fee': store_shipping_fee,
            'total': store_total
        })
    
    # 전체 총액 계산
    subtotal_amount = sum(store_data['subtotal'] for store_data in stores_with_items)
    total_amount = subtotal_amount + total_shipping_fee
    
    if settings.DEBUG:
        logger.debug(f"[CHECKOUT] 전체 계산 결과:")
        logger.debug(f"[CHECKOUT]   - 상품 총액: {subtotal_amount} sats")
        logger.debug(f"[CHECKOUT]   - 배송비 총액: {total_shipping_fee} sats")
        logger.debug(f"[CHECKOUT]   - 최종 총액: {total_amount} sats")
    
    # store_base.html을 위한 기본 store 설정
    store = stores_with_items[0]['store'] if stores_with_items else None
    
    # 세션에서 배송 정보 가져오기
    shipping_data = request.session.get('shipping_data', {})
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'stores_with_items': stores_with_items,
        'subtotal_amount': subtotal_amount,
        'total_shipping_fee': total_shipping_fee,
        'total_amount': total_amount,
        'shipping_data': shipping_data,
        'store': store,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def checkout_complete(request, order_number):
    """주문 완료 페이지"""
    # 기본 주문 정보 가져오기
    primary_order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # 같은 결제 해시로 생성된 모든 주문 가져오기
    all_orders = Order.objects.filter(
        user=request.user,
        payment_id=primary_order.payment_id
    ).prefetch_related('items__product__images')
    
    # 전체 통계 계산
    total_amount = sum(order.total_amount for order in all_orders)
    total_subtotal = sum(order.subtotal for order in all_orders)
    total_shipping_fee = sum(order.shipping_fee for order in all_orders)
    total_items = sum(order.items.count() for order in all_orders)
    
    # 모든 주문 아이템을 하나의 리스트로 합치기 (주문 정보도 함께 저장)
    all_order_items = []
    for order in all_orders:
        for item in order.items.all():
            # 아이템에 주문 정보를 추가
            item.order = order
            all_order_items.append(item)
    
    context = {
        'primary_order': primary_order,
        'all_orders': all_orders,
        'all_order_items': all_order_items,
        'total_amount': total_amount,
        'total_subtotal': total_subtotal,
        'total_shipping_fee': total_shipping_fee,
        'total_items': total_items,
        'total_orders': len(all_orders),
        'store': primary_order.store,  # 기본 스토어 (store_base.html용)
    }
    return render(request, 'orders/checkout_complete.html', context)


@login_required
@require_POST
def create_checkout_invoice(request):
    """결제용 인보이스 생성"""
    try:
        if settings.DEBUG:
            logger.debug("create_checkout_invoice 호출")
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
            if settings.DEBUG:
                logger.debug(f"인보이스 생성 요청 데이터: {data}")
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        # 장바구니 확인
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all().select_related('product', 'product__store')
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'error': '장바구니가 비어있습니다.'}, status=400)
        
        if not cart_items:
            return JsonResponse({'success': False, 'error': '장바구니가 비어있습니다.'}, status=400)
        
        # 스토어별로 그룹화하여 총액 계산
        from itertools import groupby
        stores_with_items = []
        total_shipping_fee = 0
        
        if settings.DEBUG:
            logger.debug(f"[INVOICE] 장바구니 아이템 수: {len(cart_items)}")
        
        for store, items in groupby(cart_items, key=lambda x: x.product.store):
            store_items = list(items)
            store_subtotal = sum(item.total_price for item in store_items)
            
            # 스토어별 배송비 계산 (스토어 내 상품 중 최대 배송비 사용)
            store_shipping_fee = max(item.product.display_shipping_fee for item in store_items) if store_items else 0
            store_total = store_subtotal + store_shipping_fee
            total_shipping_fee += store_shipping_fee
            
            if settings.DEBUG:
                logger.debug(f"[INVOICE] 스토어: {store.store_name}")
                logger.debug(f"[INVOICE]   - 상품 수: {len(store_items)}")
                logger.debug(f"[INVOICE]   - 상품 소계: {store_subtotal} sats")
                logger.debug(f"[INVOICE]   - 배송비: {store_shipping_fee} sats (최대 배송비)")
                logger.debug(f"[INVOICE]   - 스토어 총액: {store_total} sats")
                for item in store_items:
                    logger.debug(f"[INVOICE]     * {item.product.title}: {item.quantity}개 x {item.unit_price} = {item.total_price} sats")
                    logger.debug(f"[INVOICE]       배송비 정보: shipping_fee={item.product.shipping_fee}, display_shipping_fee={item.product.display_shipping_fee}")
            
            stores_with_items.append({
                'store': store,
                'items': store_items,
                'subtotal': store_subtotal,
                'shipping_fee': store_shipping_fee,
                'total': store_total
            })
        
        # 전체 총액 계산
        subtotal_amount = sum(store_data['subtotal'] for store_data in stores_with_items)
        total_amount = subtotal_amount + total_shipping_fee
        
        if settings.DEBUG:
            logger.debug(f"[INVOICE] 전체 계산 결과:")
            logger.debug(f"[INVOICE]   - 상품 총액: {subtotal_amount} sats")
            logger.debug(f"[INVOICE]   - 배송비 총액: {total_shipping_fee} sats")
            logger.debug(f"[INVOICE]   - 최종 총액: {total_amount} sats")
        
        # 첫 번째 스토어의 블링크 API 사용 (다중 스토어 주문의 경우 향후 개선 필요)
        first_store = stores_with_items[0]['store']
        
        # 메모 생성 - 제품 정보 포함
        memo_parts = []
        
        # 각 상품에 대한 정보를 수집
        for store_data in stores_with_items:
            for item in store_data['items']:
                product_name = item.product.title
                quantity = item.quantity
                price = item.total_price
                memo_parts.append(f"제품: {product_name} / 수량: {quantity}개 / 금액: {price} sats")
        
        # 메모 조합 (최대 3개 상품까지만 표시하고 나머지는 생략)
        if len(memo_parts) <= 3:
            memo = " | ".join(memo_parts)
        else:
            memo = " | ".join(memo_parts[:3]) + f" | 외 {len(memo_parts) - 3}개 상품"
        
        # 총액 정보 추가
        memo += f" | 총 {total_amount} sats"
        
        # BlinkAPIService 초기화
        try:
            blink_service = get_blink_service_for_store(first_store)
            if settings.DEBUG:
                logger.debug("BlinkAPIService 초기화 성공")
        except Exception as e:
            if settings.DEBUG:
                logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Blink API 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 인보이스 생성
        if settings.DEBUG:
            logger.debug(f"[INVOICE] 인보이스 생성 시작: amount={total_amount} sats, memo={memo}")
        
        result = blink_service.create_invoice(
            amount_sats=int(total_amount),
            memo=memo,
            expires_in_minutes=30  # 결제용 인보이스는 30분 유효
        )
        
        if settings.DEBUG:
            logger.debug(f"[INVOICE] 인보이스 생성 결과: {result}")
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
        
        # 인보이스 데이터베이스에 저장
        try:
            invoice = Invoice.objects.create(
                payment_hash=result['payment_hash'],
                invoice_string=result['invoice'],
                amount_sats=int(total_amount),
                memo=memo,
                user=request.user,
                store=first_store,
                expires_at=result['expires_at'],
                status='pending'
            )
            
            if settings.DEBUG:
                logger.debug(f"[INVOICE] 인보이스 DB 저장 완료: ID={invoice.id}")
                
        except Exception as e:
            if settings.DEBUG:
                logger.error(f"[INVOICE] 인보이스 DB 저장 실패: {str(e)}")
            # DB 저장 실패해도 인보이스는 생성되었으므로 계속 진행
        
        # 응답 데이터 준비
        response_data = {
            'success': True,
            'payment_hash': result['payment_hash'],
            'invoice': result['invoice'],
            'amount': int(total_amount),
            'memo': memo,
            'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None,
            'stores_count': len(stores_with_items),
            'items_count': cart.total_items
        }
        
        if settings.DEBUG:
            logger.debug(f"응답 데이터: {response_data}")
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        if settings.DEBUG:
            logger.error(f"JSON 디코딩 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"create_checkout_invoice 예외 발생: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'인보이스 생성 중 오류가 발생했습니다: {str(e)}'}, status=500)


@login_required
@require_POST
def check_checkout_payment(request):
    """결제 상태 확인 API"""
    try:
        if settings.DEBUG:
            logger.debug("check_checkout_payment 호출")
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
            if settings.DEBUG:
                logger.debug(f"결제 상태 확인 요청 데이터: {data}")
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        payment_hash = data.get('payment_hash')
        if not payment_hash:
            return JsonResponse({'success': False, 'error': 'payment_hash가 필요합니다.'}, status=400)
        
        if settings.DEBUG:
            logger.debug(f"결제 상태 확인: payment_hash={payment_hash}")
        
        # 장바구니 확인
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all().select_related('product', 'product__store')
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'error': '장바구니가 비어있습니다.'}, status=400)
        
        if not cart_items:
            return JsonResponse({'success': False, 'error': '장바구니가 비어있습니다.'}, status=400)
        
        # 첫 번째 스토어의 블링크 API 사용
        first_store = cart_items[0].product.store
        
        # BlinkAPIService 초기화
        try:
            blink_service = get_blink_service_for_store(first_store)
            if settings.DEBUG:
                logger.debug("스토어 정보로 BlinkAPIService 초기화")
        except Exception as e:
            if settings.DEBUG:
                logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Blink API 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 결제 상태 확인
        result = blink_service.check_invoice_status(payment_hash)
        
        if settings.DEBUG:
            logger.debug(f"결제 상태 확인 결과: {result}")
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
        
        # 결제 완료 시 주문 생성
        if result['status'] == 'paid':
            try:
                # 인보이스 상태 업데이트
                try:
                    invoice = Invoice.objects.get(payment_hash=payment_hash)
                    invoice.status = 'paid'
                    invoice.paid_at = timezone.now()
                    invoice.save()
                    
                    if settings.DEBUG:
                        logger.debug(f"[PAYMENT] 인보이스 상태 업데이트 완료: {payment_hash}")
                except Invoice.DoesNotExist:
                    if settings.DEBUG:
                        logger.warning(f"[PAYMENT] 인보이스를 찾을 수 없음: {payment_hash}")
                
                # 주문 생성 로직 (기존 checkout 뷰의 로직 활용)
                shipping_data = request.session.get('shipping_data', {})
                order_result = create_order_from_cart(request.user, cart, payment_hash, shipping_data)
                
                # 인보이스와 주문 연결 (첫 번째 주문과 연결)
                try:
                    invoice = Invoice.objects.get(payment_hash=payment_hash)
                    if order_result['orders']:
                        primary_order = order_result['orders'][0]
                        invoice.order = primary_order
                        invoice.save()
                        
                        if settings.DEBUG:
                            logger.debug(f"[PAYMENT] 인보이스-주문 연결 완료: {payment_hash} -> {primary_order.order_number}")
                except (Invoice.DoesNotExist, Order.DoesNotExist) as e:
                    if settings.DEBUG:
                        logger.warning(f"[PAYMENT] 인보이스-주문 연결 실패: {str(e)}")
                
                # 주문 완료 후 세션에서 배송 정보 삭제
                if 'shipping_data' in request.session:
                    del request.session['shipping_data']
                
                return JsonResponse({
                    'success': True,
                    'status': result['status'],
                    'paid': True,
                    'order_number': order_result['primary_order_number'],
                    'redirect_url': f'/orders/checkout/complete/{order_result["primary_order_number"]}/'
                })
            except Exception as e:
                if settings.DEBUG:
                    logger.error(f"주문 생성 실패: {str(e)}", exc_info=True)
                
                # 주문 생성 실패 시 인보이스 상태를 다시 pending으로 변경
                try:
                    invoice = Invoice.objects.get(payment_hash=payment_hash)
                    invoice.status = 'pending'
                    invoice.paid_at = None
                    invoice.save()
                except Invoice.DoesNotExist:
                    pass
                
                return JsonResponse({
                    'success': False,
                    'error': f'주문 생성 중 오류가 발생했습니다: {str(e)}'
                }, status=500)
        
        return JsonResponse({
            'success': True,
            'status': result['status'],
            'paid': False
        })
        
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"check_checkout_payment 예외 발생: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'결제 상태 확인 중 오류가 발생했습니다: {str(e)}'}, status=500)


@login_required
@require_POST
def cancel_invoice(request):
    """인보이스 취소"""
    try:
        if settings.DEBUG:
            logger.debug("cancel_invoice 호출")
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
            if settings.DEBUG:
                logger.debug(f"인보이스 취소 요청 데이터: {data}")
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        payment_hash = data.get('payment_hash')
        if not payment_hash:
            return JsonResponse({'success': False, 'error': 'payment_hash가 필요합니다.'}, status=400)
        
        # 인보이스 찾기 및 권한 확인
        try:
            invoice = Invoice.objects.get(payment_hash=payment_hash, user=request.user)
        except Invoice.DoesNotExist:
            return JsonResponse({'success': False, 'error': '인보이스를 찾을 수 없습니다.'}, status=404)
        
        # 취소 가능한 상태인지 확인
        if invoice.status != 'pending':
            return JsonResponse({
                'success': False, 
                'error': f'취소할 수 없는 상태입니다. 현재 상태: {invoice.get_status_display()}'
            }, status=400)
        
        # 인보이스 상태를 취소로 변경
        invoice.status = 'cancelled'
        invoice.save()
        
        if settings.DEBUG:
            logger.debug(f"인보이스 취소 완료: {payment_hash}")
        
        return JsonResponse({
            'success': True,
            'message': '인보이스가 취소되었습니다.'
        })
        
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"cancel_invoice 예외 발생: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'인보이스 취소 중 오류가 발생했습니다: {str(e)}'}, status=500)


def create_order_from_cart(user, cart, payment_hash, shipping_data=None):
    """장바구니에서 주문 생성"""
    import uuid
    from itertools import groupby
    
    # 스토어별로 정렬한 후 그룹화 (중요: groupby는 정렬된 데이터에서만 올바르게 작동)
    cart_items = cart.items.all().select_related('product', 'product__store').order_by('product__store__id')
    
    # 스토어별로 그룹화
    stores_orders = {}
    all_orders = []
    
    # 배송 정보 기본값 설정
    if not shipping_data:
        shipping_data = {
            'buyer_name': user.get_full_name() or user.username,
            'buyer_phone': '',
            'buyer_email': user.email,
            'shipping_postal_code': '',
            'shipping_address': '디지털 상품',
            'shipping_detail_address': '',
            'order_memo': '라이트닝 결제로 주문',
        }
    
    with transaction.atomic():
        for store, items in groupby(cart_items, key=lambda x: x.product.store):
            store_items = list(items)
            
            if settings.DEBUG:
                logger.debug(f"[ORDER_CREATE] 스토어: {store.store_name}, 상품 수: {len(store_items)}")
            
            # 주문 번호 생성
            order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # 스토어별 배송비 계산 (스토어 내 상품 중 최대 배송비 사용)
            store_shipping_fee = max(item.product.display_shipping_fee for item in store_items) if store_items else 0
            
            # 주문 생성
            order = Order.objects.create(
                order_number=order_number,
                user=user,
                store=store,
                buyer_name=shipping_data.get('buyer_name', ''),
                buyer_phone=shipping_data.get('buyer_phone', ''),
                buyer_email=shipping_data.get('buyer_email', ''),
                shipping_postal_code=shipping_data.get('shipping_postal_code', ''),
                shipping_address=shipping_data.get('shipping_address', ''),
                shipping_detail_address=shipping_data.get('shipping_detail_address', ''),
                order_memo=shipping_data.get('order_memo', ''),
                subtotal=0,  # 나중에 계산
                shipping_fee=store_shipping_fee,
                total_amount=0,  # 나중에 계산
                status='paid',
                payment_id=payment_hash,
                paid_at=timezone.now()
            )
            
            stores_orders[store.id] = order
            all_orders.append(order)
            
            if settings.DEBUG:
                logger.debug(f"[ORDER_CREATE] 주문 생성: {order_number}, 배송비: {store_shipping_fee} sats")
            
            # 주문 아이템 생성
            for item in store_items:
                # 재고 확인 및 감소
                if item.product.is_temporarily_out_of_stock:
                    raise Exception(f'"{item.product.title}" 상품이 일시품절 상태입니다.')
                elif not item.product.can_purchase(item.quantity):
                    raise Exception(f'"{item.product.title}" 상품의 재고가 부족합니다. (요청: {item.quantity}개, 재고: {item.product.stock_quantity}개)')
                
                # 재고 감소
                if not item.product.decrease_stock(item.quantity):
                    raise Exception(f'"{item.product.title}" 상품의 재고 감소에 실패했습니다.')
                
                # 옵션 정보를 문자열 형태로 변환
                options_display = {}
                for option_id, choice_id in item.selected_options.items():
                    try:
                        from products.models import ProductOption, ProductOptionChoice
                        option = ProductOption.objects.get(id=option_id)
                        choice = ProductOptionChoice.objects.get(id=choice_id)
                        options_display[option.name] = choice.name
                    except (ProductOption.DoesNotExist, ProductOptionChoice.DoesNotExist):
                        continue
                
                order_item = OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_title=item.product.title,
                    product_price=item.product.final_price,
                    quantity=item.quantity,
                    selected_options=options_display,
                    options_price=item.options_price
                )
                
                if settings.DEBUG:
                    logger.debug(f"[ORDER_CREATE]   - 상품: {item.product.title}, 수량: {item.quantity}, 총가격: {order_item.total_price} sats, 남은재고: {item.product.stock_quantity}개")
        
        # 각 주문의 총액 계산
        for order in stores_orders.values():
            order.subtotal = sum(item.total_price for item in order.items.all())
            order.total_amount = order.subtotal + order.shipping_fee
            order.save()
            
            if settings.DEBUG:
                logger.debug(f"[ORDER_CREATE] 주문 총액 계산: {order.order_number}, 상품: {order.subtotal} + 배송: {order.shipping_fee} = {order.total_amount} sats")
            
            # 구매 내역 생성
            PurchaseHistory.objects.create(
                user=user,
                order=order,
                store_name=order.store.store_name,
                total_amount=order.total_amount,
                purchase_date=order.paid_at
            )
        
        # 장바구니 비우기
        cart.items.all().delete()
        
        # 모든 주문 정보 반환
        total_amount = sum(order.total_amount for order in all_orders)
        total_subtotal = sum(order.subtotal for order in all_orders)
        total_shipping_fee = sum(order.shipping_fee for order in all_orders)
        
        if settings.DEBUG:
            logger.debug(f"[ORDER_CREATE] 전체 주문 완료: {len(all_orders)}개, 총액: {total_amount} sats")
        
        return {
            'orders': all_orders,
            'primary_order_number': all_orders[0].order_number if all_orders else None,
            'total_orders': len(all_orders),
            'total_amount': total_amount,
            'total_subtotal': total_subtotal,
            'total_shipping_fee': total_shipping_fee
        }
