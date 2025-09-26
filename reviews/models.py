from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


MIN_REVIEW_RATING = 1
MAX_REVIEW_RATING = 5


class Review(models.Model):
    """상품에 대한 구매 후기"""

    MIN_RATING = MIN_REVIEW_RATING
    MAX_RATING = MAX_REVIEW_RATING

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='상품',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        verbose_name='작성자',
    )
    rating = models.PositiveSmallIntegerField(verbose_name='평점')
    content = models.TextField(verbose_name='후기 내용')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '구입 후기'
        verbose_name_plural = '구입 후기'
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=MIN_REVIEW_RATING) & models.Q(rating__lte=MAX_REVIEW_RATING),
                name='reviews_review_rating_range',
            ),
        ]
        indexes = [
            models.Index(fields=['product', '-created_at'], name='reviews_product_created_idx'),
            models.Index(fields=['author', 'product'], name='reviews_author_product_idx'),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} - {self.author_id} ({self.rating})"


class ReviewImage(models.Model):
    """구입 후기 이미지"""

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='후기',
    )
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name='이미지 너비(px)')
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name='이미지 높이(px)')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 일시')

    class Meta:
        verbose_name = '구입 후기 이미지'
        verbose_name_plural = '구입 후기 이미지'
        ordering = ['order', 'uploaded_at', 'id']
        indexes = [
            models.Index(fields=['review', 'order'], name='reviews_image_order_idx'),
        ]

    def __str__(self) -> str:
        return f"Review {self.review_id} - {self.original_name}"
