from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.sessions.models import Session
from stores.models import Store
from products.models import Product, ProductImage
from orders.services import CartService
from orders.models import Invoice, Order
import json


class GuestCheckoutTestCase(TestCase):
    """비회원 구매 기능 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 스토어 주인 생성
        self.store_owner = User.objects.create_user(
            username='storeowner',
            email='store@example.com',
            password='testpass123'
        )
        
        # 스토어 생성
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
        
        # 상품 생성
        self.product = Product.objects.create(
            store=self.store,
            title='테스트 상품',
            description='테스트용 상품입니다.',
            price=1000,
            is_discounted=True,
            discounted_price=800,
            shipping_fee=100,
            is_active=True,
            stock_quantity=10
        )
        
        # 클라이언트 초기화
        self.client = Client()
    
    def test_session_cart_add_item(self):
        """세션 장바구니에 상품 추가 테스트"""
        # 비로그인 상태에서 장바구니에 상품 추가
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
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_count'], 2)
        
        # 세션에 장바구니 데이터가 저장되었는지 확인
        session = self.client.session
        self.assertIn('cart', session)
        self.assertEqual(len(session['cart']['items']), 1)
        self.assertEqual(session['cart']['items'][0]['product_id'], self.product.id)
        self.assertEqual(session['cart']['items'][0]['quantity'], 2)
    
    def test_session_cart_view(self):
        """세션 장바구니 조회 테스트"""
        # 먼저 상품을 장바구니에 추가
        self.client.post(
            reverse('orders:add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 1,
                'selected_options': {}
            }),
            content_type='application/json'
        )
        
        # 장바구니 페이지 접근
        response = self.client.get(reverse('orders:cart_view'))
        self.assertEqual(response.status_code, 200)
        
        # 템플릿 컨텍스트 확인
        self.assertIn('cart_items', response.context)
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0]['product_id'], self.product.id)
        self.assertEqual(cart_items[0]['quantity'], 1)
    
    def test_session_cart_remove_item(self):
        """세션 장바구니에서 상품 제거 테스트"""
        # 먼저 상품을 장바구니에 추가
        self.client.post(
            reverse('orders:add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 1,
                'selected_options': {}
            }),
            content_type='application/json'
        )
        
        # 세션에서 아이템 ID 가져오기
        session = self.client.session
        item_id = session['cart']['items'][0]['id']
        
        # 상품 제거
        response = self.client.post(
            reverse('orders:remove_from_cart'),
            data=json.dumps({'item_id': item_id}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # 세션에서 아이템이 제거되었는지 확인
        session = self.client.session
        self.assertEqual(len(session['cart']['items']), 0)
    
    def test_guest_shipping_info(self):
        """비회원 배송정보 입력 테스트"""
        # 먼저 상품을 장바구니에 추가
        self.client.post(
            reverse('orders:add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 1,
                'selected_options': {}
            }),
            content_type='application/json'
        )
        
        # 배송정보 페이지 접근
        response = self.client.get(reverse('orders:shipping_info'))
        self.assertEqual(response.status_code, 200)
        
        # 배송정보 제출
        response = self.client.post(reverse('orders:shipping_info'), {
            'buyer_name': '홍길동',
            'buyer_phone': '01012345678',
            'buyer_email': 'guest@example.com',
            'shipping_postal_code': '12345',
            'shipping_address': '서울시 강남구',
            'shipping_detail_address': '101동 101호',
            'order_memo': '문 앞에 놓아주세요'
        })
        
        # 체크아웃 페이지로 리다이렉트 되는지 확인
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('orders:checkout'))
        
        # 세션에 배송정보가 저장되었는지 확인
        session = self.client.session
        self.assertIn('shipping_data', session)
        self.assertEqual(session['shipping_data']['buyer_name'], '홍길동')
    
    def test_guest_checkout_view(self):
        """비회원 체크아웃 페이지 테스트"""
        # 장바구니에 상품 추가
        self.client.post(
            reverse('orders:add_to_cart'),
            data=json.dumps({
                'product_id': self.product.id,
                'quantity': 1,
                'selected_options': {}
            }),
            content_type='application/json'
        )
        
        # 배송정보를 세션에 저장
        session = self.client.session
        session['shipping_data'] = {
            'buyer_name': '홍길동',
            'buyer_phone': '01012345678',
            'buyer_email': 'guest@example.com',
            'shipping_postal_code': '12345',
            'shipping_address': '서울시 강남구',
            'shipping_detail_address': '101동 101호',
            'order_memo': '문 앞에 놓아주세요'
        }
        session.save()
        
        # 체크아웃 페이지 접근
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)
        
        # 컨텍스트 데이터 확인
        self.assertIn('cart_items', response.context)
        self.assertIn('shipping_data', response.context)
        self.assertIn('total_amount', response.context)
    
    def test_cart_service_functionality(self):
        """CartService 기능 테스트"""
        # Mock request 객체 생성
        from django.test import RequestFactory
        from django.contrib.sessions.backends.db import SessionStore
        
        factory = RequestFactory()
        request = factory.get('/')
        request.session = SessionStore()
        request.user = None  # 비로그인 상태
        
        # CartService 초기화
        cart_service = CartService(request)
        
        # 빈 장바구니 상태 확인
        cart_items = cart_service.get_cart_items()
        self.assertEqual(len(cart_items), 0)
        
        cart_summary = cart_service.get_cart_summary()
        self.assertEqual(cart_summary['total_items'], 0)
        self.assertEqual(cart_summary['total_amount'], 0)
        
        # 상품 추가
        result = cart_service.add_to_cart(self.product.id, 2)
        self.assertTrue(result['success'])
        
        # 장바구니 상태 확인
        cart_items = cart_service.get_cart_items()
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0]['product_id'], self.product.id)
        self.assertEqual(cart_items[0]['quantity'], 2)
        
        cart_summary = cart_service.get_cart_summary()
        self.assertEqual(cart_summary['total_items'], 2)
        self.assertGreater(cart_summary['total_amount'], 0)
    
    def test_session_to_db_migration(self):
        """세션 장바구니에서 DB로 마이그레이션 테스트"""
        # Mock request 객체 생성 (비로그인 상태)
        from django.test import RequestFactory
        from django.contrib.sessions.backends.db import SessionStore
        
        factory = RequestFactory()
        request = factory.get('/')
        request.session = SessionStore()
        request.user = None
        
        # 비로그인 상태에서 상품 추가
        cart_service = CartService(request)
        cart_service.add_to_cart(self.product.id, 3)
        
        # 세션에 상품이 있는지 확인
        session_items = cart_service.get_cart_items()
        self.assertEqual(len(session_items), 1)
        self.assertEqual(session_items[0]['quantity'], 3)
        
        # 로그인 사용자 생성
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 로그인 상태로 변경
        request.user = user
        cart_service = CartService(request)
        
        # 마이그레이션 실행
        cart_service.migrate_session_to_db()
        
        # DB에 장바구니가 생성되었는지 확인
        from orders.models import Cart, CartItem
        cart = Cart.objects.get(user=user)
        cart_items = cart.items.all()
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0].product, self.product)
        self.assertEqual(cart_items[0].quantity, 3)
        
        # 세션 장바구니가 비워졌는지 확인
        self.assertNotIn('cart', request.session)


class CartServiceIntegrationTestCase(TestCase):
    """CartService 통합 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 스토어 주인 생성
        self.store_owner = User.objects.create_user(
            username='storeowner',
            email='store@example.com',
            password='testpass123'
        )
        
        # 스토어 생성
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
        
        # 상품 생성
        self.product = Product.objects.create(
            store=self.store,
            title='테스트 상품',
            description='테스트용 상품입니다.',
            price=1000,
            is_discounted=True,
            discounted_price=800,
            shipping_fee=100,
            is_active=True,
            stock_quantity=10
        )
    
    def test_logged_in_vs_guest_cart_behavior(self):
        """로그인/비로그인 상태별 장바구니 동작 비교 테스트"""
        from django.test import RequestFactory
        from django.contrib.sessions.backends.db import SessionStore
        
        factory = RequestFactory()
        
        # 1. 비로그인 상태 테스트
        guest_request = factory.get('/')
        guest_request.session = SessionStore()
        guest_request.user = None
        
        guest_cart_service = CartService(guest_request)
        guest_result = guest_cart_service.add_to_cart(self.product.id, 2)
        self.assertTrue(guest_result['success'])
        
        guest_items = guest_cart_service.get_cart_items()
        self.assertEqual(len(guest_items), 1)
        self.assertFalse(guest_items[0]['is_db_item'])  # 세션 아이템
        
        # 2. 로그인 상태 테스트
        user_request = factory.get('/')
        user_request.session = SessionStore()
        user_request.user = self.user
        
        user_cart_service = CartService(user_request)
        user_result = user_cart_service.add_to_cart(self.product.id, 3)
        self.assertTrue(user_result['success'])
        
        user_items = user_cart_service.get_cart_items()
        self.assertEqual(len(user_items), 1)
        self.assertTrue(user_items[0]['is_db_item'])  # DB 아이템
        
        # 3. 데이터 구조 일관성 확인
        guest_item = guest_items[0]
        user_item = user_items[0]
        
        # 공통 필드들이 동일한 구조를 가지는지 확인
        common_fields = ['product_id', 'product_title', 'quantity', 'unit_price', 'total_price', 'store_id', 'store_name']
        for field in common_fields:
            self.assertIn(field, guest_item)
            self.assertIn(field, user_item) 