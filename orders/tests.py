from django.contrib.auth.models import User
from django.test import TestCase

from orders.views import calculate_store_totals
from products.models import Product
from stores.models import Store


class ShippingOverrideTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='test-pass')
        self.store = Store.objects.create(
            store_id='teststore',
            store_name='테스트 스토어',
            owner_name='홍길동',
            chat_channel='https://t.me/example',
            owner=self.owner,
            shipping_fee_mode='flat',
            shipping_fee_sats=5000,
            shipping_fee_krw=5000,
        )

    def test_calculate_store_totals_all_force_free(self):
        store_items = [
            {'total_price': 10_000, 'force_free_shipping': True},
            {'total_price': 5_000, 'force_free_shipping': True},
        ]

        subtotal, shipping_fee, override = calculate_store_totals(self.store, store_items)

        self.assertEqual(subtotal, 15_000)
        self.assertEqual(shipping_fee, 0)
        self.assertTrue(override)

    def test_calculate_store_totals_mixed_items(self):
        store_items = [
            {'total_price': 8_000, 'force_free_shipping': True},
            {'total_price': 12_000, 'force_free_shipping': False},
        ]

        subtotal, shipping_fee, override = calculate_store_totals(self.store, store_items)

        self.assertEqual(subtotal, 20_000)
        self.assertEqual(shipping_fee, 5_000)
        self.assertFalse(override)

    def test_product_force_free_shipping_properties(self):
        product = Product.objects.create(
            store=self.store,
            title='무료 배송 상품',
            description='테스트 상품',
            price=12_345,
            stock_quantity=10,
            force_free_shipping=True,
        )

        self.assertEqual(product.public_shipping_fee, 0)
        self.assertEqual(product.display_shipping_fee, 0)
        self.assertEqual(product.shipping_fee_display(), '배송비 무료')
