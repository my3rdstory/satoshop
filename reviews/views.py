import logging
from typing import Optional, Tuple

from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.db import transaction

from products.models import Product

from .forms import ReviewForm
from .models import Review, ReviewImage
from .services import (
    build_reviews_url,
    create_review_images,
    delete_review_image,
    get_paginated_reviews,
    upload_review_images,
    user_has_purchased_product,
)


logger = logging.getLogger(__name__)


def _is_ajax(request) -> bool:
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _build_navigation(request, store_id: str, product_id: int) -> dict:
    page_param = request.POST.get('page') or request.GET.get('page')
    return build_reviews_url(store_id, product_id, page_param)


def _render_reviews_fragment(request, product: Product, page_number: int) -> Tuple[str, int]:
    review_context = get_paginated_reviews(product, page_number)
    html = render_to_string(
        'products/partials/reviews_content.html',
        {
            'store': product.store,
            'product': product,
            **review_context,
        },
        request=request,
    )
    actual_page = review_context['reviews_page'].number
    return html, actual_page


def _success_response(
    request,
    navigation: dict,
    *,
    html: Optional[str] = None,
    page: Optional[int] = None,
    status: int = 200,
):
    if _is_ajax(request):
        payload = {
            'success': True,
            'url': navigation['path'],
            'anchor': navigation['anchor'],
            'reviews_url': navigation['anchor'],
            'page': page or navigation['page'],
        }
        if html is not None:
            payload['html'] = html
        return JsonResponse(payload, status=status)
    return HttpResponseRedirect(navigation['anchor'])


def _error_response(request, navigation: dict, *, errors=None, message=None, status: int = 400):
    if _is_ajax(request):
        payload = {
            'success': False,
            'url': navigation['path'],
            'anchor': navigation['anchor'],
            'reviews_url': navigation['anchor'],
            'page': navigation['page'],
        }
        if errors is not None:
            payload['errors'] = errors
        if message:
            payload['message'] = message
        return JsonResponse(payload, status=status)
    return HttpResponseRedirect(navigation['anchor'])


def _get_product(store_id: str, product_id: int) -> Product:
    return get_object_or_404(
        Product.objects.select_related('store'),
        id=product_id,
        store__store_id=store_id,
        store__is_active=True,
        store__deleted_at__isnull=True,
    )


class ReviewCreateView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int):
        product = _get_product(store_id, product_id)
        navigation = _build_navigation(request, store_id, product_id)

        if not user_has_purchased_product(request.user, product):
            logger.warning(
                "ReviewCreateView blocked - user has no purchase",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'store_id': store_id,
                },
            )
            return _error_response(
                request,
                navigation,
                message=_('상품을 구매한 고객만 후기를 작성할 수 있습니다.'),
                status=403,
            )

        logger.info(
            "ReviewCreateView received submit",
            extra={
                'user_id': request.user.id,
                'product_id': product.id,
                'store_id': store_id,
            },
        )

        form = ReviewForm(request.POST, request.FILES)
        if not form.is_valid():
            logger.warning(
                "ReviewCreateView form invalid errors=%s",
                form.errors.get_json_data(),
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                },
            )
            return _error_response(
                request,
                navigation,
                errors=form.errors.get_json_data(),
                status=400,
            )

        images = form.cleaned_data.get('images') or []

        try:
            with transaction.atomic():
                review = form.save(commit=False)
                review.product = product
                review.author = request.user
                review.save()
                logger.info(
                    "ReviewCreateView saved review",
                    extra={
                        'review_id': review.id,
                        'user_id': request.user.id,
                        'product_id': product.id,
                        'has_images': bool(images),
                    },
                )

                if images:
                    uploaded = upload_review_images(images, product)
                    logger.info(
                        "ReviewCreateView uploading images",
                        extra={
                            'review_id': review.id,
                            'uploaded_count': len(uploaded),
                        },
                    )
                    create_review_images(review, uploaded)
        except ValidationError as exc:
            logger.warning(
                "ReviewCreateView validation error messages=%s",
                exc.messages,
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                },
            )
            return _error_response(
                request,
                navigation,
                errors=exc.messages,
                status=400,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "ReviewCreateView unexpected error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                },
            )
            return _error_response(
                request,
                navigation,
                message=_('후기 저장 중 오류가 발생했습니다.'),
                status=500,
            )

        logger.info(
            "ReviewCreateView completed",
            extra={
                'user_id': request.user.id,
                'product_id': product.id,
            },
        )

        # 새 리뷰가 최신 순으로 노출되도록 첫 페이지로 이동
        navigation = build_reviews_url(store_id, product_id, 1)
        html, current_page = _render_reviews_fragment(request, product, navigation['page'])
        if current_page != navigation['page']:
            navigation = build_reviews_url(store_id, product_id, current_page)
        return _success_response(request, navigation, html=html, page=current_page)


class ReviewUpdateView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int, review_id: int):
        product = _get_product(store_id, product_id)
        review = get_object_or_404(Review, id=review_id, product=product)
        navigation = _build_navigation(request, store_id, product_id)

        if review.author != request.user:
            message = _('자신의 후기만 수정할 수 있습니다.')
            if _is_ajax(request):
                return _error_response(request, navigation, message=message, status=403)
            return HttpResponseForbidden(message)

        existing_count = review.images.count()
        form = ReviewForm(
            request.POST,
            request.FILES,
            instance=review,
            existing_image_count=existing_count,
        )

        if not form.is_valid():
            logger.warning(
                "ReviewUpdateView form invalid errors=%s",
                form.errors.get_json_data(),
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                },
            )
            return _error_response(
                request,
                navigation,
                errors=form.errors.get_json_data(),
                status=400,
            )

        images = form.cleaned_data.get('images') or []

        try:
            with transaction.atomic():
                review = form.save(commit=True)
                if images:
                    uploaded = upload_review_images(images, product, existing_count=existing_count)
                    create_review_images(review, uploaded)
        except ValidationError as exc:
            logger.warning(
                "ReviewUpdateView validation error messages=%s",
                exc.messages,
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                },
            )
            return _error_response(
                request,
                navigation,
                errors=exc.messages,
                status=400,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "ReviewUpdateView unexpected error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                },
            )
            return _error_response(
                request,
                navigation,
                message=_('후기 수정 중 오류가 발생했습니다.'),
                status=500,
            )

        html, current_page = _render_reviews_fragment(request, product, navigation['page'])
        if current_page != navigation['page']:
            navigation = build_reviews_url(store_id, product_id, current_page)
        return _success_response(request, navigation, html=html, page=current_page)


class ReviewDeleteView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int, review_id: int):
        product = _get_product(store_id, product_id)
        review = get_object_or_404(Review, id=review_id, product=product)
        navigation = _build_navigation(request, store_id, product_id)

        if review.author != request.user:
            message = _('자신의 후기만 삭제할 수 있습니다.')
            if _is_ajax(request):
                return _error_response(request, navigation, message=message, status=403)
            return HttpResponseForbidden(message)

        try:
            with transaction.atomic():
                for image in list(review.images.all()):
                    delete_review_image(image)
                review.delete()
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "ReviewDeleteView error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                },
            )
            return _error_response(
                request,
                navigation,
                message=_('후기 삭제 중 오류가 발생했습니다.'),
                status=500,
            )

        html, current_page = _render_reviews_fragment(request, product, navigation['page'])
        if current_page != navigation['page']:
            navigation = build_reviews_url(store_id, product_id, current_page)
        return _success_response(request, navigation, html=html, page=current_page)


class ReviewImageDeleteView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int, review_id: int, image_id: int):
        product = _get_product(store_id, product_id)
        review = get_object_or_404(Review, id=review_id, product=product)
        image = get_object_or_404(ReviewImage, id=image_id, review=review)
        navigation = _build_navigation(request, store_id, product_id)

        if review.author != request.user:
            message = _('자신의 후기 이미지만 삭제할 수 있습니다.')
            if _is_ajax(request):
                return _error_response(request, navigation, message=message, status=403)
            return HttpResponseForbidden(message)

        try:
            delete_review_image(image)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "ReviewImageDeleteView error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                    'image_id': image.id,
                },
            )
            return _error_response(
                request,
                navigation,
                message=_('후기 이미지 삭제 중 오류가 발생했습니다.'),
                status=500,
            )

        html, current_page = _render_reviews_fragment(request, product, navigation['page'])
        if current_page != navigation['page']:
            navigation = build_reviews_url(store_id, product_id, current_page)
        return _success_response(request, navigation, html=html, page=current_page)
