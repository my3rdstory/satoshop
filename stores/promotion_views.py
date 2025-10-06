from __future__ import annotations

import csv
import logging
from datetime import datetime
from io import StringIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BahPromotionRequestForm
from .models import (
    BahPromotionAdmin,
    BahPromotionRequest,
    MAX_PROMOTION_IMAGES,
    PROMOTION_STATUS_PENDING,
    PROMOTION_STATUS_SHIPPED,
    BahPromotionLinkSettings,
    Store,
)
from .promotion_services import delete_promotion_images, save_promotion_images

User = get_user_model()


def _is_bah_admin(user: User | None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return BahPromotionAdmin.objects.filter(user=user).exists()


def _get_existing_request(user: User | None) -> BahPromotionRequest | None:
    if not user or not user.is_authenticated:
        return None
    return (
        BahPromotionRequest.objects
        .filter(user=user)
        .prefetch_related('images')
        .first()
    )

logger = logging.getLogger(__name__)


def _csv_text(value) -> str:
    """CSV용 텍스트 값을 생성한다. Zero-width space로 숫자 앞 0 보존."""
    if value is None:
        text = ''
    elif isinstance(value, datetime):
        text = timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S')
    else:
        text = str(value)

    text = text.replace('\r', ' ').replace('\n', ' ')
    if text:
        return f"\u200B{text}"
    return ''


def _send_bah_promotion_email(promotion_request: BahPromotionRequest, *, is_new: bool) -> None:
    settings_obj = BahPromotionLinkSettings.get_solo()
    store_id = (settings_obj.email_store_id or '').strip() if settings_obj else ''
    if not store_id:
        return

    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        logging.getLogger(__name__).warning('BAH email store not found: %s', store_id)
        return

    if not (store.email_enabled and store.email_host_user and store.email_host_password_encrypted):
        logging.getLogger(__name__).info('BAH email skipped (email disabled or missing credentials) for store %s', store_id)
        return

    try:
        backend = EmailBackend(
            host='smtp.gmail.com',
            port=587,
            username=store.email_host_user,
            password=store.get_email_host_password(),
            use_tls=True,
            fail_silently=False,
        )
    except Exception:
        logging.getLogger(__name__).exception('BAH email backend init failed for store %s', store_id)
        return

    subject_prefix = '신규' if is_new else '수정'
    subject = f'[BAH 홍보요청 {subject_prefix}] {promotion_request.store_name}'

    lines = [
        'BAH 홍보요청이 접수되었습니다.',
        '',
        f'요청 종류: {"신규" if is_new else "수정"}',
        f'신청 저장 시각: {timezone.localtime(promotion_request.updated_at).strftime("%Y-%m-%d %H:%M:%S")}',
        '',
        '매장 정보',
        f'- 매장명: {promotion_request.store_name}',
        f'- 전화번호: {promotion_request.phone_number}',
        f'- 이메일: {promotion_request.email}',
        f'- 주소: {promotion_request.postal_code} {promotion_request.address} {promotion_request.address_detail}',
        '',
        '소개 내용',
        promotion_request.introduction or '',
    ]

    image_urls = [image.file_url for image in promotion_request.images.order_by('order', 'uploaded_at')]
    if image_urls:
        lines.extend(['', '이미지 링크'] + [f'- {url}' for url in image_urls])

    lines.extend([
        '',
        '관리자 페이지에서 발송 상태를 업데이트해 주세요.',
    ])

    body = '\n'.join(lines)

    to_addresses = [addr for addr in [store.email_host_user, store.owner_email] if addr]
    if not to_addresses:
        return
    # deduplicate preserving order
    seen = set()
    unique_addresses = []
    for addr in to_addresses:
        if addr not in seen:
            unique_addresses.append(addr)
            seen.add(addr)

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=f'{store.email_from_display} <{store.email_host_user}>',
        to=unique_addresses,
        connection=backend,
    )

    try:
        email.send(fail_silently=False)
    except Exception:
        logging.getLogger(__name__).exception('BAH 홍보요청 이메일 전송 실패 (store=%s)', store_id)

def bah_promotion_request_view(request):
    existing_request = _get_existing_request(request.user)
    existing_images = []
    if existing_request:
        existing_images = list(existing_request.images.order_by('order', 'uploaded_at'))

    status = request.GET.get('status')
    wants_post = request.method == 'POST'
    is_authenticated = request.user.is_authenticated
    is_superuser = bool(is_authenticated and request.user.is_superuser)
    has_lightning_profile = bool(
        is_authenticated and hasattr(request.user, 'lightning_profile')
    )
    user_can_submit = has_lightning_profile or is_superuser

    delete_ids = []
    if wants_post:
        delete_ids = request.POST.getlist('delete_images') if existing_request else []
        delete_count = 0
        if existing_request and delete_ids:
            delete_count = existing_request.images.filter(id__in=delete_ids).count()
    else:
        delete_count = 0

    existing_image_count = 0
    if existing_request:
        existing_image_count = max(existing_request.images.count() - delete_count, 0)

    form = BahPromotionRequestForm(
        data=request.POST or None,
        files=request.FILES or None,
        instance=existing_request,
        existing_image_count=existing_image_count,
    )

    if wants_post:
        if not is_authenticated:
            login_url = f"{reverse('accounts:lightning_login')}?next={request.path}"
            messages.error(request, '라이트닝 지갑으로 로그인 후 다시 시도해주세요.')
            return redirect(login_url)

        if not user_can_submit:
            login_url = f"{reverse('accounts:lightning_login')}?next={request.path}"
            messages.error(request, '홍보요청은 라이트닝 지갑으로 로그인한 계정만 가능합니다.')
            return redirect(login_url)

        if form.is_valid():
            is_new_request = existing_request is None
            promotion_request = form.save(commit=False)
            promotion_request.user = request.user
            if has_lightning_profile:
                lightning_public_key = request.user.lightning_profile.public_key
                promotion_request.lightning_public_key = lightning_public_key
                promotion_request.lightning_verified_at = timezone.now()
            promotion_request.save()

            if delete_ids:
                delete_promotion_images(promotion_request, delete_ids)

            uploaded_files = form.get_uploaded_images()
            if uploaded_files:
                save_promotion_images(
                    promotion_request,
                    uploaded_files,
                    uploaded_by=request.user,
                )

            try:
                _send_bah_promotion_email(promotion_request, is_new=is_new_request)
            except Exception:
                logger.exception('BAH 홍보요청 이메일 전송 중 오류 발생', extra={'request_id': promotion_request.id})

            query_status = 'created' if is_new_request else 'updated'
            return redirect(f"{reverse('stores:bah_promotion_request')}?status={query_status}")

    link_settings = BahPromotionLinkSettings.objects.first()

    try:
        default_usage_url = reverse('stores:bah_wallet_of_satoshi_guide')
    except NoReverseMatch:
        default_usage_url = getattr(settings, 'BAH_PROMOTION_WOS_GUIDE_URL', '#')

    try:
        default_login_url = reverse('accounts:link_lightning')
    except NoReverseMatch:
        default_login_url = getattr(settings, 'BAH_PROMOTION_LOGIN_GUIDE_URL', '#')

    login_guide_url = (
        link_settings.login_guide_url if link_settings and link_settings.login_guide_url else default_login_url
    )
    usage_guide_url = (
        link_settings.usage_guide_url if link_settings and link_settings.usage_guide_url else default_usage_url
    )

    is_bah_admin = _is_bah_admin(request.user)

    show_form = bool(user_can_submit and (form.errors or existing_request))
    needs_lightning_logout = bool(
        is_authenticated and not user_can_submit and not is_superuser and not is_bah_admin
    )

    remaining_slots = max(MAX_PROMOTION_IMAGES - len(existing_images), 0)

    context = {
        'form': form,
        'existing_request': existing_request,
        'existing_images': existing_images,
        'max_images': MAX_PROMOTION_IMAGES,
        'remaining_slots': remaining_slots,
        'user_is_authenticated': request.user.is_authenticated,
        'user_has_lightning': user_can_submit,
        'lightning_login_url': f"{reverse('accounts:lightning_login')}?next={request.path}",
        'link_lightning_url': reverse('accounts:link_lightning') if request.user.is_authenticated else f"{reverse('accounts:lightning_login')}?next={reverse('accounts:link_lightning')}",
        'status': status,
        'wos_guide_url': usage_guide_url,
        'wos_login_guide_url': login_guide_url,
        'show_form': show_form,
        'user_is_bah_admin': is_bah_admin,
        'admin_list_url': reverse('stores:bah_promotion_admin') if is_bah_admin else None,
        'requires_lightning_logout': needs_lightning_logout,
        'logout_url': reverse('accounts:logout'),
        'logout_next': request.path,
    }
    return render(request, 'stores/bah_promotion_request.html', context)


def bah_wallet_of_satoshi_guide_view(request):
    guide_sections = [
        {
            'title': '1. 월렛 설치와 백업',
            'icon': 'fa-download',
            'items': [
                '앱 스토어(안드로이드, iOS)에서 Wallet of Satoshi를 설치합니다.',
                '처음 실행 시 이메일을 입력해 계정을 보호하고 복구 코드를 저장합니다.',
                '설정 → Backup 메뉴에서 복구 문구(Recovery Phrase)를 기록해 두세요.',
            ],
        },
        {
            'title': '2. 비트코인 충전과 수신 테스트',
            'icon': 'fa-coins',
            'items': [
                '메인 화면의 Receive 버튼을 눌러 라이트닝 송금용 인보이스를 생성합니다.',
                '다른 지갑 또는 테스트넷 지원 서비스로 소액(1,000 사토시 이하)을 송금해 잔액을 확보합니다.',
                '인보이스가 결제되면 Wallet of Satoshi 잔액이 즉시 업데이트됩니다.',
            ],
        },
        {
            'title': '3. LNURL-auth로 지갑 인증하기',
            'icon': 'fa-bolt',
            'items': [
                'SatoShop에서 라이트닝 인증을 시작하면 QR 코드가 생성됩니다.',
                '월오사 앱의 Send → Scan 버튼을 눌러 QR을 스캔하거나 링크를 열어줍니다.',
                '인증에 성공하면 페이지가 자동으로 갱신되며 “라이트닝 지갑이 연동되어 있습니다” 메시지를 확인할 수 있습니다.',
            ],
        },
        {
            'title': '4. 결제 테스트 팁',
            'icon': 'fa-lightbulb',
            'items': [
                'POS 단말이 없는 경우 태블릿/휴대폰에서 SatoShop 스토어에 접속해 테스트 상품을 만들어 결제 흐름을 검증합니다.',
                '결제가 완료되면 월오사 앱에서 즉시 영수증을 확인할 수 있으며, 필요 시 내보내기(Export) 기능으로 증빙을 다운로드하세요.',
                '결제 오류가 발생하면 인터넷 연결과 최신 버전 여부를 먼저 확인한 뒤, 블링크 API 키를 다시 등록합니다.',
            ],
        },
    ]

    resources = [
        {
            'title': '월오사 공식 웹사이트',
            'url': 'https://walletofsatoshi.com/',
            'description': '앱 다운로드와 업데이트 공지, 고객지원 안내를 제공합니다.',
        },
        {
            'title': 'SatoShop 라이트닝 인증 가이드',
            'url': reverse('accounts:link_lightning'),
            'description': '라이트닝 지갑을 계정에 연동하는 단계별 안내를 제공합니다.',
        },
    ]

    context = {
        'guide_sections': guide_sections,
        'resources': resources,
        'promotion_request_url': reverse('stores:bah_promotion_request'),
    }
    return render(request, 'stores/bah_wallet_of_satoshi_guide.html', context)


def bah_promotion_admin_view(request):
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:lightning_login')}?next={request.path}"
        return redirect(login_url)

    if not _is_bah_admin(request.user):
        return HttpResponseForbidden('관리자만 접근할 수 있습니다.')

    page_number = request.GET.get('page')

    requests = (
        BahPromotionRequest.objects
        .select_related('user')
        .prefetch_related('images')
        .order_by('-created_at')
    )

    paginator = Paginator(requests, 5)
    page_obj = paginator.get_page(page_number)

    context = {
        'promotion_requests': page_obj.object_list,
        'page_obj': page_obj,
        'promotion_status_pending': PROMOTION_STATUS_PENDING,
        'promotion_status_shipped': PROMOTION_STATUS_SHIPPED,
    }
    return render(request, 'stores/bah_promotion_admin.html', context)


@require_POST
def bah_promotion_admin_toggle_status(request, pk: int):
    if not request.user.is_authenticated:
        return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)

    if not _is_bah_admin(request.user):
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)

    promotion_request = get_object_or_404(BahPromotionRequest, pk=pk)
    promotion_request.toggle_shipping_status()

    return JsonResponse({
        'status': promotion_request.shipping_status,
        'status_display': promotion_request.get_shipping_status_display(),
    })


def bah_promotion_admin_export_csv(request, pk: int):
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:lightning_login')}?next={request.path}"
        return redirect(login_url)

    if not _is_bah_admin(request.user):
        return HttpResponseForbidden('관리자만 접근할 수 있습니다.')

    request_obj = get_object_or_404(
        BahPromotionRequest.objects.select_related('user').prefetch_related('images'),
        pk=pk,
    )

    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    headers = [
        'ID', '신청일', '수정일', '매장명', '우편번호', '주소', '상세주소',
        '전화번호', '이메일', '소개', '발송상태', '라이트닝 공개키', '라이트닝 인증시각',
        '신청자'
    ]
    writer.writerow(headers)

    row = [
        _csv_text(request_obj.id),
        _csv_text(request_obj.created_at),
        _csv_text(request_obj.updated_at),
        _csv_text(request_obj.store_name),
        _csv_text(request_obj.postal_code),
        _csv_text(request_obj.address),
        _csv_text(request_obj.address_detail),
        _csv_text(request_obj.phone_number),
        _csv_text(request_obj.email),
        _csv_text(request_obj.introduction),
        _csv_text(request_obj.get_shipping_status_display()),
        _csv_text(request_obj.lightning_public_key),
        _csv_text(request_obj.lightning_verified_at),
        _csv_text(request_obj.user.username if request_obj.user else ''),
    ]
    writer.writerow(row)

    csv_content = output.getvalue()
    response = HttpResponse(
        '\ufeff' + csv_content,
        content_type='text/csv; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename="bah_promotion_request_{request_obj.id}.csv"'
    return response
