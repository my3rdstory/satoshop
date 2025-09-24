from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from stores.models import Store
from products.models import Product
import json


class CartAccessControlTestCase(TestCase):
    """장바구니 및 주문 접근 제어 테스트"""

    def setUp(self):
        self.client = Client()
        self.store_owner = User.objects.create_user(
            username='storeowner',
            email='store@example.com',
            password='testpass123'
        )
        self.store = Store.objects.create(
            store_id='teststore',
            store_name='테스트 스토어',
            store_description='테스트용 스토어입니다.',
            owner=self.store_owner,
            owner_name='스토어 주인',
            owner_phone='01012345678',
            owner_email='store@example.com',
            chat_channel='@testchannel',
            business_license_number='123-45-67890',
            telecommunication_sales_number='2023-서울-1234',
            is_active=True
        )
        self.product = Product.objects.create(
            store=self.store,
            title='테스트 상품',
            description='테스트용 상품입니다.',
            price=1000,
            price_display='sats',
            is_active=True,
            stock_quantity=10
        )
        self.user = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='buyerpass123'
        )

    def test_guest_add_to_cart_requires_login(self):
        response = self.client.post(
            reverse('orders:add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 1,
                'selected_options': {}
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get('success'))
        self.assertEqual(payload.get('error'), 'login_required')

    def test_authenticated_user_can_add_to_cart(self):
        logged_in = self.client.login(username='buyer', password='buyerpass123')
        self.assertTrue(logged_in)

        response = self.client.post(
            reverse('orders:add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 2,
                'selected_options': {}
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('cart_count'), 2)

    def test_guest_cart_view_redirects_to_login(self):
        response = self.client.get(reverse('orders:cart_view'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_guest_shipping_info_redirects_to_login(self):
        response = self.client.get(reverse('orders:shipping_info'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
