from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product
from reviews.models import Review
from reviews.services import (
    MAX_IMAGES_PER_REVIEW,
    ProcessedImage,
    process_image,
    upload_review_images,
    user_has_purchased_product,
)
from stores.models import Store


def make_uploaded_image(width=1200, height=800, color='white'):
    """테스트용 이미지를 생성합니다."""
    from PIL import Image

    buffer = BytesIO()
    image = Image.new('RGB', (width, height), color=color)
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile('test.jpg', buffer.getvalue(), content_type='image/jpeg')


class ReviewServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='password', email='alice@example.com')
        self.other_user = User.objects.create_user(username='bob', password='password', email='bob@example.com')
        self.store = Store.objects.create(
            store_id='satoshop-test',
            store_name='테스트 스토어',
            owner_name='앨리스',
            chat_channel='https://example.com/chat',
            owner=self.user,
            is_active=True,
        )
        self.product = Product.objects.create(
            store=self.store,
            title='테스트 상품',
            description='테스트 설명',
            price=1500,
        )

    def create_order(self, user, status='paid'):
        order = Order.objects.create(
            user=user,
            store=self.store,
            status=status,
            delivery_status='preparing',
            buyer_name='구매자',
            buyer_phone='010-0000-0000',
            buyer_email='buyer@example.com',
            shipping_postal_code='12345',
            shipping_address='서울시 테스트구',
            shipping_detail_address='101동 1001호',
            order_memo='',
            subtotal=1500,
            shipping_fee=0,
            total_amount=1500,
            paid_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_title=self.product.title,
            product_price=self.product.price,
            quantity=1,
        )
        return order

    def test_user_has_purchased_product_returns_true_for_paid_order(self):
        self.create_order(self.user, status='paid')
        self.assertTrue(user_has_purchased_product(self.user, self.product))

    def test_user_has_purchased_product_ignores_non_paid_orders(self):
        self.create_order(self.user, status='pending')
        self.assertFalse(user_has_purchased_product(self.user, self.product))

    def test_user_has_purchased_product_checks_by_user(self):
        self.create_order(self.other_user, status='paid')
        self.assertFalse(user_has_purchased_product(self.user, self.product))

    def test_process_image_resizes_and_converts_to_webp(self):
        uploaded = make_uploaded_image(width=2048, height=1024)
        result = process_image(uploaded)
        self.assertLessEqual(result.width, 1000)
        self.assertTrue(result.file.name.endswith('.webp'))
        self.assertGreater(result.height, 0)

    @patch('reviews.services.upload_file_to_s3')
    @patch('reviews.services.process_image')
    def test_upload_review_images_success(self, mock_process_image, mock_upload_file):
        dummy_file = ContentFile(b'data', name='dummy.webp')
        mock_process_image.return_value = ProcessedImage(
            original_name='original.png',
            file=dummy_file,
            width=800,
            height=600,
        )
        mock_upload_file.return_value = {
            'success': True,
            'file_path': 'reviews/1/test.webp',
            'file_url': 'https://example.com/reviews/test.webp',
        }

        uploaded_files = [SimpleUploadedFile('image.png', b'data', content_type='image/png')]
        result = upload_review_images(uploaded_files, self.product)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['file_url'], 'https://example.com/reviews/test.webp')
        mock_process_image.assert_called_once()
        mock_upload_file.assert_called_once()

    def test_upload_review_images_rejects_excess_files(self):
        files = [SimpleUploadedFile(f'image_{i}.png', b'data', content_type='image/png') for i in range(MAX_IMAGES_PER_REVIEW + 1)]
        with self.assertRaises(ValidationError):
            upload_review_images(files, self.product)

    def test_upload_review_images_respects_existing_count(self):
        files = [SimpleUploadedFile('extra.png', b'data', content_type='image/png') for _ in range(2)]
        with self.assertRaises(ValidationError):
            upload_review_images(files, self.product, existing_count=MAX_IMAGES_PER_REVIEW - 1)

