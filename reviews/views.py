import logging

from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.db import transaction

from products.models import Product

from .forms import ReviewForm
from .models import Review, ReviewImage
from .services import (
    create_review_images,
    delete_review_image,
    upload_review_images,
    user_has_purchased_product,
)


logger = logging.getLogger(__name__)


def _redirect_to_reviews(request, store_id: str, product_id: int) -> HttpResponseRedirect:
    base_url = reverse('products:product_detail', args=[store_id, product_id])
    page = request.POST.get('page') or request.GET.get('page')
    if page and page.isdigit() and int(page) > 1:
        base_url = f"{base_url}?page={page}"
    return HttpResponseRedirect(f"{base_url}#reviews")


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

        if not user_has_purchased_product(request.user, product):
            logger.warning(
                "ReviewCreateView blocked - user has no purchase",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'store_id': store_id,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)

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
                "ReviewCreateView form invalid",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'errors': form.errors,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)

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
                "ReviewCreateView validation error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'errors': exc.messages,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "ReviewCreateView unexpected error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)

        logger.info(
            "ReviewCreateView completed",
            extra={
                'user_id': request.user.id,
                'product_id': product.id,
            },
        )
        return _redirect_to_reviews(request, store_id, product_id)


class ReviewUpdateView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int, review_id: int):
        product = _get_product(store_id, product_id)
        review = get_object_or_404(Review, id=review_id, product=product)

        if review.author != request.user:
            return HttpResponseForbidden(_('자신의 후기만 수정할 수 있습니다.'))

        existing_count = review.images.count()
        form = ReviewForm(
            request.POST,
            request.FILES,
            instance=review,
            existing_image_count=existing_count,
        )

        if not form.is_valid():
            logger.warning(
                "ReviewUpdateView form invalid",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                    'errors': form.errors,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)

        images = form.cleaned_data.get('images') or []

        try:
            with transaction.atomic():
                review = form.save(commit=True)
                if images:
                    uploaded = upload_review_images(images, product, existing_count=existing_count)
                    create_review_images(review, uploaded)
        except ValidationError as exc:
            logger.warning(
                "ReviewUpdateView validation error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                    'errors': exc.messages,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "ReviewUpdateView unexpected error",
                extra={
                    'user_id': request.user.id,
                    'product_id': product.id,
                    'review_id': review.id,
                },
            )
            return _redirect_to_reviews(request, store_id, product_id)

        return _redirect_to_reviews(request, store_id, product_id)


class ReviewDeleteView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int, review_id: int):
        product = _get_product(store_id, product_id)
        review = get_object_or_404(Review, id=review_id, product=product)

        if review.author != request.user:
            return HttpResponseForbidden(_('자신의 후기만 삭제할 수 있습니다.'))

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
            return _redirect_to_reviews(request, store_id, product_id)

        return _redirect_to_reviews(request, store_id, product_id)


class ReviewImageDeleteView(LoginRequiredMixin, View):
    def post(self, request, store_id: str, product_id: int, review_id: int, image_id: int):
        product = _get_product(store_id, product_id)
        review = get_object_or_404(Review, id=review_id, product=product)
        image = get_object_or_404(ReviewImage, id=image_id, review=review)

        if review.author != request.user:
            return HttpResponseForbidden(_('자신의 후기 이미지만 삭제할 수 있습니다.'))

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
            return _redirect_to_reviews(request, store_id, product_id)

        return _redirect_to_reviews(request, store_id, product_id)
