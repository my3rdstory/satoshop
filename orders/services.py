from django.db import transaction
from django.contrib.auth.models import User
from products.models import Product, ProductOption, ProductOptionChoice
from .models import Cart, CartItem, Order, OrderItem, PurchaseHistory, Invoice
import json
import logging
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)


class CartService:
    """
    하이브리드 장바구니 서비스
    - 로그인 사용자: DB 저장
    - 비로그인 사용자: 세션 저장
    - 로그인 시 세션 -> DB 자동 마이그레이션
    """
    
    def __init__(self, request):
        self.request = request
        self.user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        self.session = request.session
    
    def get_cart_items(self):
        """장바구니 아이템들 반환"""
        try:
            if self.user:
                return self._get_db_cart_items()
            else:
                return self._get_session_cart_items()
        except Exception as e:
            logger.warning(f"장바구니 아이템 조회 실패: {e}")
            return []
    
    def add_to_cart(self, product_id, quantity=1, selected_options=None, force_replace=False):
        """장바구니에 상품 추가"""
        if selected_options is None:
            selected_options = {}
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return {
                'success': False,
                'error': '상품을 찾을 수 없습니다.'
            }
        
        # 🛡️ 단일 스토어 제약 확인
        existing_items = self.get_cart_items()
        if existing_items and not force_replace:
            # 기존 장바구니에 있는 스토어들 확인
            existing_stores = set(item['store_id'] for item in existing_items)
            current_store_id = product.store.store_id
            
            # 다른 스토어의 상품이 이미 있는 경우
            if current_store_id not in existing_stores:
                existing_store_names = set(item['store_name'] for item in existing_items)
                return {
                    'success': False,
                    'error': 'multi_store_conflict',
                    'message': f'장바구니에 다른 스토어({", ".join(existing_store_names)})의 상품이 있습니다.',
                    'current_store': product.store.store_name,
                    'existing_stores': list(existing_store_names),
                    'require_confirmation': True
                }
        
        # force_replace가 True인 경우 기존 장바구니 비우기
        if force_replace and existing_items:
            self.clear_cart()
        
        try:
            if self.user:
                return self._add_to_db_cart(product, quantity, selected_options)
            else:
                return self._add_to_session_cart(product, quantity, selected_options)
        except Exception as e:
            logger.error(f"장바구니 추가 실패: {e}")
            return {
                'success': False,
                'error': '장바구니 추가 중 오류가 발생했습니다.'
            }
    
    def remove_from_cart(self, item_id):
        """장바구니에서 상품 제거"""
        try:
            if self.user:
                return self._remove_from_db_cart(item_id)
            else:
                return self._remove_from_session_cart(item_id)
        except Exception as e:
            logger.error(f"장바구니 삭제 실패: {e}")
            return {
                'success': False,
                'error': '장바구니 삭제 중 오류가 발생했습니다.'
            }
    
    def update_cart_item(self, item_id, quantity):
        """장바구니 상품 수량 업데이트"""
        if quantity <= 0:
            return self.remove_from_cart(item_id)
        
        try:
            if self.user:
                return self._update_db_cart_item(item_id, quantity)
            else:
                return self._update_session_cart_item(item_id, quantity)
        except Exception as e:
            logger.error(f"장바구니 수량 업데이트 실패: {e}")
            return {
                'success': False,
                'error': '수량 업데이트 중 오류가 발생했습니다.'
            }
    
    def clear_cart(self):
        """장바구니 비우기"""
        try:
            if self.user:
                try:
                    cart = Cart.objects.get(user=self.user)
                    cart.items.all().delete()
                except Cart.DoesNotExist:
                    pass
            else:
                if 'cart' in self.session:
                    del self.session['cart']
                    self.session.modified = True
        except Exception as e:
            logger.error(f"장바구니 비우기 실패: {e}")
    
    def get_cart_summary(self):
        """장바구니 요약 정보 반환"""
        try:
            items = self.get_cart_items()
            total_items = sum(item['quantity'] for item in items)
            total_amount = sum(item['total_price'] for item in items)
            
            return {
                'total_items': total_items,
                'total_amount': total_amount,
                'items_count': len(items)
            }
        except Exception as e:
            logger.error(f"장바구니 요약 조회 실패: {e}")
            return {
                'total_items': 0,
                'total_amount': 0,
                'items_count': 0
            }
    
    def migrate_session_to_db(self):
        """세션 장바구니를 DB로 마이그레이션 (로그인 시 호출)"""
        if not self.user or 'cart' not in self.session:
            return
        
        try:
            session_cart = self.session['cart']
            if not session_cart.get('items'):
                return
                
            # DB 장바구니 생성 또는 가져오기
            cart, created = Cart.objects.get_or_create(user=self.user)
            
            with transaction.atomic():
                # 세션 아이템들을 DB에 추가
                for item_data in session_cart['items']:
                    try:
                        product = Product.objects.get(id=item_data['product_id'], is_active=True)
                        
                        # 동일한 상품과 옵션이 이미 있는지 확인
                        existing_item = cart.items.filter(
                            product=product,
                            selected_options=item_data['selected_options']
                        ).first()
                        
                        if existing_item:
                            # 수량 합산
                            existing_item.quantity += item_data['quantity']
                            existing_item.save()
                        else:
                            # 새 아이템 생성
                            CartItem.objects.create(
                                cart=cart,
                                product=product,
                                quantity=item_data['quantity'],
                                selected_options=item_data['selected_options']
                            )
                    except Product.DoesNotExist:
                        continue
            
            # 세션 장바구니 삭제
            del self.session['cart']
            self.session.modified = True
            
        except Exception as e:
            logger.error(f"장바구니 마이그레이션 실패: {e}")
    
    # === DB 카트 관련 메서드 ===
    
    def _freeze_prices_if_krw_product(self, product, selected_options):
        """원화 연동 상품인 경우 현재 환율로 가격을 고정"""
        frozen_data = {}
        
        if product.price_krw:  # 원화 연동 상품인 경우
            from myshop.models import ExchangeRate
            
            # 현재 환율 가져오기
            try:
                exchange_rate = ExchangeRate.objects.latest('created_at')
                frozen_data['frozen_exchange_rate'] = float(exchange_rate.btc_krw_rate)
                
                # 상품 가격 고정 (할인 적용)
                # 할인 상품인 경우 할인가를 고정, 그렇지 않으면 정가 고정
                if product.is_discounted and product.public_discounted_price:
                    frozen_data['frozen_product_price_sats'] = product.public_discounted_price
                else:
                    frozen_data['frozen_product_price_sats'] = product.public_price
                
                # 옵션 가격 고정
                options_price_sats = 0
                if selected_options:
                    from products.models import ProductOptionChoice
                    for option_id, choice_id in selected_options.items():
                        try:
                            choice = ProductOptionChoice.objects.get(id=choice_id)
                            options_price_sats += choice.public_price
                        except ProductOptionChoice.DoesNotExist:
                            continue
                
                frozen_data['frozen_options_price_sats'] = options_price_sats
                
            except ExchangeRate.DoesNotExist:
                # 환율 정보가 없으면 고정하지 않음
                pass
        
        return frozen_data
    
    def _get_db_cart_items(self):
        """DB에서 장바구니 아이템들 가져오기"""
        try:
            cart = Cart.objects.get(user=self.user)
            items = []
            
            for cart_item in cart.items.all().select_related('product', 'product__store'):
                # 옵션 정보 처리
                options_display = []
                if cart_item.selected_options:
                    # 고정된 옵션 가격이 있는 경우 사용 (환율 고정)
                    if cart_item.frozen_options_price_sats is not None and cart_item.frozen_options_price_sats > 0:
                        # 고정된 총 옵션 가격을 개별 옵션들에 비례적으로 분배
                        total_current_option_price = 0
                        option_prices = {}
                        for option_id, choice_id in cart_item.selected_options.items():
                            try:
                                option = ProductOption.objects.get(id=option_id)
                                choice = ProductOptionChoice.objects.get(id=choice_id)
                                current_price = choice.public_price
                                option_prices[(option_id, choice_id)] = {
                                    'option': option,
                                    'choice': choice,
                                    'current_price': current_price
                                }
                                total_current_option_price += current_price
                            except:
                                pass
                        
                        # 비례적으로 고정 가격 분배
                        for (option_id, choice_id), data in option_prices.items():
                            if total_current_option_price > 0:
                                frozen_price = int((data['current_price'] / total_current_option_price) * cart_item.frozen_options_price_sats)
                            else:
                                frozen_price = 0
                            
                            options_display.append({
                                'option_name': data['option'].name,
                                'choice_name': data['choice'].name,
                                'choice_price': frozen_price
                            })
                    else:
                        # 고정된 가격이 없으면 실시간 가격 사용
                        for option_id, choice_id in cart_item.selected_options.items():
                            try:
                                option = ProductOption.objects.get(id=option_id)
                                choice = ProductOptionChoice.objects.get(id=choice_id)
                                options_display.append({
                                    'option_name': option.name,
                                    'choice_name': choice.name,
                                    'choice_price': choice.public_price
                                })
                            except:
                                pass
                
                # 상품 이미지 URL
                product_image_url = None
                if cart_item.product.images.first():
                    product_image_url = cart_item.product.images.first().file_url
                
                items.append({
                    'id': cart_item.id,
                    'product_id': cart_item.product.id,
                    'product_title': cart_item.product.title,
                    'product_image_url': product_image_url,
                    'quantity': cart_item.quantity,
                    'unit_price': cart_item.unit_price,
                    'total_price': cart_item.total_price,
                    'selected_options': cart_item.selected_options,
                    'options_display': options_display,
                    'store_id': cart_item.product.store.store_id,
                    'store_name': cart_item.product.store.store_name,
                    'is_db_item': True,
                    'force_free_shipping': cart_item.product.force_free_shipping,
                })
            
            return items
            
        except Cart.DoesNotExist:
            return []
    
    def _add_to_db_cart(self, product, quantity, selected_options):
        """DB 장바구니에 상품 추가"""
        cart, created = Cart.objects.get_or_create(user=self.user)
        
        # 원화 연동 상품인 경우 현재 환율을 고정
        frozen_data = self._freeze_prices_if_krw_product(product, selected_options)
        
        # 항상 새 항목으로 추가 (기존 로직 유지)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            selected_options=selected_options,
            **frozen_data
        )
        
        return {
            'success': True,
            'item_id': cart_item.id,
            'message': '상품이 장바구니에 추가되었습니다.'
        }
    
    def _remove_from_db_cart(self, item_id):
        """DB 장바구니에서 상품 제거"""
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__user=self.user)
            cart_item.delete()
            return {
                'success': True,
                'message': '상품이 장바구니에서 제거되었습니다.'
            }
        except CartItem.DoesNotExist:
            return {
                'success': False,
                'error': '장바구니 아이템을 찾을 수 없습니다.'
            }
    
    def _update_db_cart_item(self, item_id, quantity):
        """DB 장바구니 상품 수량 업데이트"""
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__user=self.user)
            cart_item.quantity = quantity
            cart_item.save()
            return {
                'success': True,
                'item_total_price': cart_item.total_price,
                'message': '수량이 업데이트되었습니다.'
            }
        except CartItem.DoesNotExist:
            return {
                'success': False,
                'error': '장바구니 아이템을 찾을 수 없습니다.'
            }
    
    # === 세션 카트 관련 메서드 ===
    
    def _get_session_cart_items(self):
        """세션에서 장바구니 아이템들 가져오기"""
        cart_data = self.session.get('cart', {'items': []})
        items = []
        
        for item_data in cart_data['items']:
            try:
                product = Product.objects.get(id=item_data['product_id'], is_active=True)
                
                # 옵션 정보 처리
                options_display = []
                
                # 고정된 옵션 가격이 있는 경우 사용 (환율 고정)
                if item_data.get('frozen_options_price_sats') is not None and item_data.get('frozen_options_price_sats', 0) > 0:
                    # 고정된 총 옵션 가격을 개별 옵션들에 비례적으로 분배
                    total_current_option_price = 0
                    option_prices = {}
                    if item_data.get('selected_options'):
                        for option_id, choice_id in item_data['selected_options'].items():
                            try:
                                option = ProductOption.objects.get(id=option_id)
                                choice = ProductOptionChoice.objects.get(id=choice_id)
                                current_price = choice.public_price
                                option_prices[(option_id, choice_id)] = {
                                    'option': option,
                                    'choice': choice,
                                    'current_price': current_price
                                }
                                total_current_option_price += current_price
                            except:
                                pass
                    
                    # 비례적으로 고정 가격 분배
                    for (option_id, choice_id), data in option_prices.items():
                        if total_current_option_price > 0:
                            frozen_price = int((data['current_price'] / total_current_option_price) * item_data['frozen_options_price_sats'])
                        else:
                            frozen_price = 0
                        
                        options_display.append({
                            'option_name': data['option'].name,
                            'choice_name': data['choice'].name,
                            'choice_price': frozen_price
                        })
                else:
                    # 고정된 가격이 없으면 실시간 가격 사용 (할인 적용)
                    # 할인 상품인 경우 할인가를 사용, 그렇지 않으면 정가 사용
                    if product.is_discounted and product.public_discounted_price:
                        base_price = product.public_discounted_price
                    else:
                        base_price = product.public_price
                    
                    # 옵션 가격도 환율 적용 (public_price 사용)
                    options_total = 0
                    if item_data.get('selected_options'):
                        for option_id, choice_id in item_data['selected_options'].items():
                            try:
                                choice = ProductOptionChoice.objects.get(id=choice_id)
                                options_total += choice.public_price
                            except:
                                pass
                    
                    unit_price = base_price + options_total
                
                total_price = unit_price * item_data['quantity']
                
                items.append({
                    'id': item_data['id'],
                    'product_id': product.id,
                    'product_title': product.title,
                    'product_image_url': product.images.first().file_url if product.images.first() else None,
                    'quantity': item_data['quantity'],
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'selected_options': item_data.get('selected_options', {}),
                    'options_display': options_display,
                    'store_id': product.store.store_id,
                    'store_name': product.store.store_name,
                    'is_db_item': False,
                    'force_free_shipping': product.force_free_shipping,
                })
                
            except Product.DoesNotExist:
                continue
        
        return items
    
    def _add_to_session_cart(self, product, quantity, selected_options):
        """세션 장바구니에 상품 추가"""
        cart_data = self.session.get('cart', {'items': []})
        
        # 새 아이템 ID 생성 (타임스탬프 기반)
        import time
        item_id = f"session_{int(time.time() * 1000)}"
        
        # 원화 연동 상품인 경우 현재 환율을 고정
        frozen_data = self._freeze_prices_if_krw_product(product, selected_options)
        
        # 새 아이템 추가
        item_data = {
            'id': item_id,
            'product_id': product.id,
            'quantity': quantity,
            'selected_options': selected_options,
            'added_at': time.time(),
            'force_free_shipping': product.force_free_shipping,
        }
        
        # 환율 고정 데이터 추가
        if frozen_data:
            item_data.update(frozen_data)
        
        cart_data['items'].append(item_data)
        
        self.session['cart'] = cart_data
        self.session.modified = True
        
        return {
            'success': True,
            'item_id': item_id,
            'message': '상품이 장바구니에 추가되었습니다.'
        }
    
    def _remove_from_session_cart(self, item_id):
        """세션 장바구니에서 상품 제거"""
        cart_data = self.session.get('cart', {'items': []})
        
        original_count = len(cart_data['items'])
        cart_data['items'] = [item for item in cart_data['items'] if item['id'] != str(item_id)]
        
        if len(cart_data['items']) < original_count:
            self.session['cart'] = cart_data
            self.session.modified = True
            return {
                'success': True,
                'message': '상품이 장바구니에서 제거되었습니다.'
            }
        else:
            return {
                'success': False,
                'error': '장바구니 아이템을 찾을 수 없습니다.'
            }
    
    def _update_session_cart_item(self, item_id, quantity):
        """세션 장바구니 상품 수량 업데이트"""
        cart_data = self.session.get('cart', {'items': []})
        
        for item in cart_data['items']:
            if item['id'] == str(item_id):
                item['quantity'] = quantity
                self.session['cart'] = cart_data
                self.session.modified = True
                
                # 총 가격 계산 (응답용)
                try:
                    product = Product.objects.get(id=item['product_id'], is_active=True)
                    
                    # 고정된 가격이 있으면 사용 (환율 고정)
                    if item.get('frozen_product_price_sats') is not None:
                        unit_price = item['frozen_product_price_sats'] + item.get('frozen_options_price_sats', 0)
                    else:
                        # 실시간 가격 사용 (할인 적용)
                        # 할인 상품인 경우 할인가를 사용, 그렇지 않으면 정가 사용
                        if product.is_discounted and product.public_discounted_price:
                            base_price = product.public_discounted_price
                        else:
                            base_price = product.public_price
                        
                        # 옵션 가격도 환율 적용 (public_price 사용)
                        options_total = 0
                        if item.get('selected_options'):
                            for option_id, choice_id in item['selected_options'].items():
                                try:
                                    choice = ProductOptionChoice.objects.get(id=choice_id)
                                    options_total += choice.public_price
                                except:
                                    pass
                        
                        unit_price = base_price + options_total
                    
                    total_price = unit_price * quantity
                    
                    return {
                        'success': True,
                        'item_total_price': total_price,
                        'message': '수량이 업데이트되었습니다.'
                    }
                except Product.DoesNotExist:
                    pass
                
                return {
                    'success': True,
                    'message': '수량이 업데이트되었습니다.'
                }
        
        return {
            'success': False,
            'error': '장바구니 아이템을 찾을 수 없습니다.'
        }

def generate_order_txt_content(order):
    """
    주문서 TXT 내용 생성 (하위 호환성을 위한 래퍼 함수)
    
    Args:
        order: Order 인스턴스
    
    Returns:
        str: 주문서 텍스트 내용
    """
    from .formatters import generate_txt_order
    return generate_txt_order(order)


def send_order_notification_email(order):
    """
    주문 완료 시 스토어 주인장에게 이메일 발송
    
    Args:
        order: Order 인스턴스
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        # 🛡️ 중복 이메일 발송 방지: 같은 payment_id로 이미 이메일을 발송했는지 확인
        if order.payment_id:
            # 같은 payment_id를 가진 다른 주문들 중에서 이메일이 이미 발송된 것이 있는지 확인
            from django.core.cache import cache
            email_cache_key = f"order_email_sent_{order.payment_id}_{order.store.id}"
            
            if cache.get(email_cache_key):
                logger.debug(f"주문 {order.order_number}: 같은 결제ID({order.payment_id})로 이미 이메일 발송됨")
                return False
        
        # 스토어 이메일 설정 확인
        store = order.store
        
        # 이메일 기능이 비활성화되어 있으면 발송하지 않음
        if not store.email_enabled:
            logger.debug(f"주문 {order.order_number}: 스토어 이메일 기능 비활성화됨")
            return False
            
        # 필수 설정 확인 (Gmail 설정)
        if not store.email_host_user or not store.email_host_password_encrypted:
            logger.debug(f"주문 {order.order_number}: Gmail 설정 불완전 (이메일: {bool(store.email_host_user)}, 비밀번호: {bool(store.email_host_password_encrypted)})")
            return False
            
        # 🛡️ 중요: 수신 이메일 주소 확인 (주인장 이메일)
        if not store.owner_email:
            logger.debug(f"주문 {order.order_number}: 스토어 주인장 이메일 주소가 설정되지 않음")
            return False
            
        # 스토어별 SMTP 설정
        backend = EmailBackend(
            host='smtp.gmail.com',
            port=587,
            username=store.email_host_user,
            password=store.get_email_host_password(),
            use_tls=True,
            fail_silently=False,
        )
        
        # 이메일용 주문서 생성 (새로운 포맷터 사용)
        from .formatters import generate_email_order
        email_data = generate_email_order(order)
        
        subject = email_data['subject']
        message = email_data['body']
        
        # 이메일 발송
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=f'{store.email_from_display} <{store.email_host_user}>',
            to=[store.owner_email],
            connection=backend
        )
        
        email.send()
        
        # 🛡️ 이메일 발송 성공 기록 (중복 방지용)
        if order.payment_id:
            from django.core.cache import cache
            email_cache_key = f"order_email_sent_{order.payment_id}_{order.store.id}"
            cache.set(email_cache_key, True, timeout=86400)  # 24시간 보관
        
        logger.info(f"주문 알림 이메일 발송 성공 - 주문: {order.order_number}, 수신: {store.owner_email}")
        return True
        
    except Exception as e:
        # 이메일 발송 실패 시 로그 기록 (주문 처리는 계속 진행)
        logger.error(f"주문 알림 이메일 발송 실패 - 주문: {order.order_number}, 오류: {str(e)}")
        return False 



def restore_order_from_payment_transaction(payment_transaction, *, operator=None):
    """수동으로 결제 트랜잭션을 주문으로 복구한다."""
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from ln_payment.models import PaymentStageLog, OrderItemReservation, PaymentTransaction
    from ln_payment.services import PaymentStage

    metadata = payment_transaction.metadata if isinstance(payment_transaction.metadata, dict) else {}
    shipping_data = metadata.get('shipping') or {}
    cart_snapshot = metadata.get('cart_snapshot') or []

    if payment_transaction.order_id:
        raise ValueError('이미 주문과 연결된 트랜잭션입니다.')
    if not shipping_data:
        raise ValueError('저장된 배송 정보가 없습니다.')
    if not cart_snapshot:
        raise ValueError('저장된 장바구니 정보가 없습니다.')

    store = payment_transaction.store
    if not store:
        raise ValueError('트랜잭션의 스토어 정보를 확인할 수 없습니다.')

    UserModel = get_user_model()
    user = payment_transaction.user
    if not user:
        email_hint = None
        if isinstance(shipping_data, dict):
            email_hint = shipping_data.get('buyer_email') or shipping_data.get('buyerEmail')
        if email_hint:
            user = UserModel.objects.filter(email__iexact=email_hint).first()
    if not user:
        fallback_username = 'anonymous_guest'
        user, _ = UserModel.objects.get_or_create(
            username=fallback_username,
            defaults={
                'email': 'anonymous@satoshop.com',
                'first_name': 'Anonymous',
                'last_name': 'Guest',
            },
        )

    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    shipping_fee = _to_int(metadata.get('shipping_fee_sats'))
    subtotal_hint = _to_int(metadata.get('subtotal_sats'))
    total_hint = _to_int(metadata.get('total_sats'))

    now = timezone.now()
    operator_label = getattr(operator, 'username', None) or getattr(operator, 'email', None)

    stock_issues = []

    with transaction.atomic():
        payment_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.USER_PAYMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()

        if not payment_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.USER_PAYMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 확인을 수동으로 완료 처리했습니다.',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        pickup_requested = bool(shipping_data.get('pickup_requested'))

        order = Order.objects.create(
            user=user,
            store=store,
            status='paid',
            delivery_status='pickup' if pickup_requested else 'preparing',
            buyer_name=shipping_data.get('buyer_name', ''),
            buyer_phone=shipping_data.get('buyer_phone', ''),
            buyer_email=shipping_data.get('buyer_email', '') or (user.email or ''),
            shipping_postal_code='' if pickup_requested else shipping_data.get('shipping_postal_code', ''),
            shipping_address='' if pickup_requested else shipping_data.get('shipping_address', ''),
            shipping_detail_address='' if pickup_requested else shipping_data.get('shipping_detail_address', ''),
            order_memo=shipping_data.get('order_memo', ''),
            subtotal=0,
            shipping_fee=shipping_fee,
            total_amount=0,
            payment_id=payment_transaction.payment_hash or str(payment_transaction.id),
            paid_at=payment_transaction.updated_at or now,
        )

        computed_subtotal = 0

        for item in cart_snapshot:
            if item.get('store_id') and item.get('store_id') != store.store_id:
                raise ValueError('장바구니 정보의 스토어와 트랜잭션 스토어가 일치하지 않습니다.')

            product_id = item.get('product_id')
            if not product_id:
                raise ValueError('상품 정보가 누락된 항목이 있습니다.')

            product = Product.objects.select_for_update().filter(id=product_id, store=store).first()
            if not product:
                raise ValueError(f"상품({item.get('product_title') or product_id})을 찾을 수 없습니다.")

            quantity = _to_int(item.get('quantity'))
            if quantity <= 0:
                raise ValueError('유효하지 않은 수량 값이 포함되어 있습니다.')

            if quantity > 0:
                if not product.decrease_stock(quantity):
                    stock_issues.append({
                        'product_id': product.id,
                        'product_title': product.title,
                        'requested': quantity,
                        'available': product.stock_quantity,
                    })
                    # 재고 부족 시에는 재고를 0으로 맞춘 뒤 그대로 진행한다.
                    product.stock_quantity = 0
                    product.save(update_fields=['stock_quantity'])

            options_display = item.get('options_display') or []
            selected_options_map = {}
            options_price = 0
            if options_display:
                for option in options_display:
                    name = option.get('option_name')
                    choice = option.get('choice_name')
                    if name and choice:
                        selected_options_map[name] = choice
                    options_price += _to_int(option.get('choice_price'))
            else:
                raw_options = item.get('selected_options') or {}
                for option_id, choice_id in raw_options.items():
                    try:
                        option_obj = ProductOption.objects.get(id=option_id)
                        choice_obj = ProductOptionChoice.objects.get(id=choice_id)
                        selected_options_map[option_obj.name] = choice_obj.name
                        options_price += choice_obj.public_price
                    except (ProductOption.DoesNotExist, ProductOptionChoice.DoesNotExist):
                        continue

            unit_price = _to_int(item.get('unit_price'))
            base_price = unit_price - options_price if unit_price > options_price else unit_price
            if base_price <= 0:
                base_price = _to_int(item.get('frozen_product_price_sats')) or (product.public_price or 0)

            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                product_title=item.get('product_title') or product.title,
                product_price=base_price,
                quantity=quantity,
                selected_options=selected_options_map,
                options_price=max(options_price, 0),
            )
            computed_subtotal += order_item.total_price

        if computed_subtotal <= 0:
            raise ValueError('주문 금액을 계산할 수 없습니다.')

        order.subtotal = subtotal_hint or computed_subtotal
        if order.subtotal <= 0:
            order.subtotal = computed_subtotal
        order.total_amount = total_hint or (order.subtotal + shipping_fee)
        if order.total_amount <= 0:
            order.total_amount = order.subtotal + shipping_fee
        order.save(update_fields=['subtotal', 'total_amount', 'updated_at'])

        if user:
            PurchaseHistory.objects.update_or_create(
                user=user,
                order=order,
                defaults={
                    'store_name': store.store_name,
                    'total_amount': order.total_amount,
                    'purchase_date': order.paid_at or now,
                },
            )

        OrderItemReservation.objects.filter(transaction=payment_transaction).update(
            status=OrderItemReservation.STATUS_CONVERTED,
        )

        payment_transaction.order = order
        payment_transaction.status = PaymentTransaction.STATUS_COMPLETED
        payment_transaction.current_stage = PaymentStage.ORDER_FINALIZE
        payment_transaction.save(update_fields=['order', 'status', 'current_stage', 'updated_at'])

        if not payment_transaction.stage_logs.filter(
            stage=PaymentStage.MERCHANT_SETTLEMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists():
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.MERCHANT_SETTLEMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 입금을 확인했습니다 (수동)',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                    'stock_issues': stock_issues,
                },
            )

        PaymentStageLog.objects.create(
            transaction=payment_transaction,
            stage=PaymentStage.ORDER_FINALIZE,
            status=PaymentStageLog.STATUS_COMPLETED,
            message='스토어에서 주문서를 수동으로 생성했습니다.',
            detail={
                'operator': operator_label,
                'restored_at': now.isoformat(),
                'stock_issues': stock_issues,
            },
        )

        meta = dict(metadata)
        restore_history = meta.setdefault('manual_restore_history', [])
        restore_history.append({
            'restored_at': now.isoformat(),
            'operator': operator_label,
            'stock_issues': stock_issues,
        })
        meta['manual_restored'] = True
        if stock_issues:
            meta['manual_stock_issues'] = stock_issues
        payment_transaction.metadata = meta
        payment_transaction.save(update_fields=['metadata'])

        try:
            send_order_notification_email(order)
        except Exception:
            logger.warning('수동 주문 복구 알림 이메일 발송 실패 order=%s', order.order_number, exc_info=True)

    order.manual_stock_issues = stock_issues
    return order


def restore_meetup_transaction(payment_transaction, *, operator=None):
    """수동으로 밋업 결제 트랜잭션을 참가 확정 상태로 복구한다."""
    from django.utils import timezone
    from meetup.models import MeetupOrder
    from meetup.services import (
        send_meetup_notification_email,
        send_meetup_participant_confirmation_email,
    )
    from ln_payment.models import PaymentStageLog, PaymentTransaction
    from ln_payment.services import PaymentStage

    metadata = payment_transaction.metadata if isinstance(payment_transaction.metadata, dict) else {}
    participant_data = metadata.get('participant') or {}
    if not participant_data:
        raise ValueError('저장된 참가자 정보가 없습니다.')

    meetup_order = payment_transaction.meetup_order
    if not meetup_order:
        meetup_order_id = metadata.get('meetup_order_id')
        if meetup_order_id:
            meetup_order = MeetupOrder.objects.filter(id=meetup_order_id).first()
    if not meetup_order:
        raise ValueError('연결된 밋업 주문을 찾을 수 없습니다.')

    now = timezone.now()
    operator_label = getattr(operator, 'username', None) or getattr(operator, 'email', None)

    with transaction.atomic():
        meetup_order.participant_name = participant_data.get('participant_name', meetup_order.participant_name)
        meetup_order.participant_email = participant_data.get('participant_email', meetup_order.participant_email)
        meetup_order.participant_phone = participant_data.get('participant_phone', meetup_order.participant_phone or '')
        meetup_order.base_price = participant_data.get('base_price', meetup_order.base_price)
        meetup_order.options_price = participant_data.get('options_price', meetup_order.options_price)
        meetup_order.total_price = participant_data.get('total_price', meetup_order.total_price)
        meetup_order.is_early_bird = participant_data.get('is_early_bird', meetup_order.is_early_bird)
        meetup_order.discount_rate = participant_data.get('discount_rate', meetup_order.discount_rate)
        meetup_order.original_price = participant_data.get('original_price', meetup_order.original_price)
        meetup_order.payment_hash = (
            payment_transaction.payment_hash
            or participant_data.get('payment_hash')
            or meetup_order.payment_hash
        )
        meetup_order.payment_request = (
            payment_transaction.payment_request
            or participant_data.get('payment_request')
            or meetup_order.payment_request
        )
        meetup_order.status = 'confirmed'
        meetup_order.is_temporary_reserved = False
        meetup_order.auto_cancelled_reason = ''
        if not meetup_order.paid_at:
            meetup_order.paid_at = payment_transaction.updated_at or now
        if not meetup_order.confirmed_at:
            meetup_order.confirmed_at = now
        meetup_order.save(update_fields=[
            'participant_name',
            'participant_email',
            'participant_phone',
            'base_price',
            'options_price',
            'total_price',
            'is_early_bird',
            'discount_rate',
            'original_price',
            'payment_hash',
            'payment_request',
            'status',
            'is_temporary_reserved',
            'auto_cancelled_reason',
            'paid_at',
            'confirmed_at',
            'updated_at',
        ])

        payment_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.USER_PAYMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()
        if not payment_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.USER_PAYMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 확인을 수동으로 완료 처리했습니다.',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        settlement_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.MERCHANT_SETTLEMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()
        if not settlement_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.MERCHANT_SETTLEMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 입금을 확인했습니다 (수동)',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        PaymentStageLog.objects.create(
            transaction=payment_transaction,
            stage=PaymentStage.ORDER_FINALIZE,
            status=PaymentStageLog.STATUS_COMPLETED,
            message='스토어에서 밋업 참가를 수동으로 확정했습니다.',
            detail={
                'operator': operator_label,
                'restored_at': now.isoformat(),
                'order_number': meetup_order.order_number,
            },
        )

        meta = dict(metadata)
        restore_history = meta.setdefault('manual_restore_history', [])
        restore_history.append({
            'restored_at': now.isoformat(),
            'operator': operator_label,
            'type': 'meetup',
            'order_number': meetup_order.order_number,
        })
        meta['manual_restored'] = True

        update_fields = {'metadata', 'meetup_order', 'status', 'current_stage', 'updated_at'}
        if participant_data.get('payment_hash') and not payment_transaction.payment_hash:
            payment_transaction.payment_hash = participant_data['payment_hash']
            update_fields.add('payment_hash')
        if participant_data.get('payment_request') and not payment_transaction.payment_request:
            payment_transaction.payment_request = participant_data['payment_request']
            update_fields.add('payment_request')

        payment_transaction.metadata = meta
        payment_transaction.meetup_order = meetup_order
        payment_transaction.status = PaymentTransaction.STATUS_COMPLETED
        payment_transaction.current_stage = PaymentStage.ORDER_FINALIZE
        payment_transaction.save(update_fields=list(update_fields))

    try:
        send_meetup_notification_email(meetup_order)
        send_meetup_participant_confirmation_email(meetup_order)
    except Exception:  # pylint: disable=broad-except
        logger.warning('밋업 수동 복구 이메일 발송 실패 order=%s', meetup_order.order_number, exc_info=True)

    return meetup_order


def restore_live_lecture_transaction(payment_transaction, *, operator=None):
    """수동으로 라이브 강의 결제 트랜잭션을 참가 확정 상태로 복구한다."""
    from django.utils import timezone
    from lecture.models import LiveLectureOrder
    from lecture.services import (
        send_live_lecture_notification_email,
        send_live_lecture_participant_confirmation_email,
    )
    from ln_payment.models import PaymentStageLog, PaymentTransaction
    from ln_payment.services import PaymentStage

    metadata = payment_transaction.metadata if isinstance(payment_transaction.metadata, dict) else {}
    participant_data = metadata.get('participant') or {}
    if not participant_data:
        raise ValueError('저장된 참가자 정보가 없습니다.')

    live_lecture_order = payment_transaction.live_lecture_order
    if not live_lecture_order:
        live_lecture_order_id = metadata.get('live_lecture_order_id')
        if live_lecture_order_id:
            live_lecture_order = LiveLectureOrder.objects.filter(id=live_lecture_order_id).first()
    if not live_lecture_order:
        raise ValueError('연결된 라이브 강의 주문을 찾을 수 없습니다.')

    now = timezone.now()
    operator_label = getattr(operator, 'username', None) or getattr(operator, 'email', None)

    with transaction.atomic():
        # 최신 상태를 잠금으로 가져와 중복 확정을 방지
        live_lecture_order = LiveLectureOrder.objects.select_for_update().get(pk=live_lecture_order.pk)

        merged_original_order_id = None
        existing_active_order = (
            LiveLectureOrder.objects.select_for_update()
            .filter(
                live_lecture=live_lecture_order.live_lecture,
                user=live_lecture_order.user,
                status__in=['confirmed', 'completed'],
            )
            .exclude(id=live_lecture_order.id)
            .order_by('-updated_at')
            .first()
        )

        merged_existing_order = existing_active_order is not None
        if existing_active_order:
            # 이미 확정된 주문이 있으면 해당 주문으로 결제 정보를 병합한다.
            target_order = existing_active_order
            original_order_id = live_lecture_order.id

            if live_lecture_order.id != target_order.id and live_lecture_order.status != 'cancelled':
                live_lecture_order.status = 'cancelled'
                live_lecture_order.is_temporary_reserved = False
                live_lecture_order.auto_cancelled_reason = '중복 주문 자동 취소 (수동 복구 병합)'
                live_lecture_order.save(update_fields=[
                    'status',
                    'is_temporary_reserved',
                    'auto_cancelled_reason',
                    'updated_at',
                ])
            logger.info(
                '라이브 강의 수동 복구: 기존 확정 주문과 병합 transaction=%s original_order=%s merged_order=%s',
                payment_transaction.id,
                original_order_id,
                target_order.id,
            )
            merged_original_order_id = original_order_id
            live_lecture_order = target_order

        live_lecture_order.price = participant_data.get('total_price', live_lecture_order.price)
        live_lecture_order.is_early_bird = participant_data.get('is_early_bird', live_lecture_order.is_early_bird)
        live_lecture_order.discount_rate = participant_data.get('discount_rate', live_lecture_order.discount_rate)
        original_price = participant_data.get('original_price')
        if original_price is not None:
            live_lecture_order.original_price = original_price
        live_lecture_order.payment_hash = (
            payment_transaction.payment_hash
            or participant_data.get('payment_hash')
            or live_lecture_order.payment_hash
        )
        live_lecture_order.payment_request = (
            payment_transaction.payment_request
            or participant_data.get('payment_request')
            or live_lecture_order.payment_request
        )
        if live_lecture_order.status != 'completed':
            live_lecture_order.status = 'confirmed'
        live_lecture_order.is_temporary_reserved = False
        live_lecture_order.auto_cancelled_reason = ''
        if not live_lecture_order.paid_at:
            live_lecture_order.paid_at = payment_transaction.updated_at or now
        if not live_lecture_order.confirmed_at:
            live_lecture_order.confirmed_at = now
        live_lecture_order.save(update_fields=[
            'price',
            'is_early_bird',
            'discount_rate',
            'original_price',
            'payment_hash',
            'payment_request',
            'status',
            'is_temporary_reserved',
            'auto_cancelled_reason',
            'paid_at',
            'confirmed_at',
            'updated_at',
        ])

        payment_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.USER_PAYMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()
        if not payment_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.USER_PAYMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 확인을 수동으로 완료 처리했습니다.',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        settlement_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.MERCHANT_SETTLEMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()
        if not settlement_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.MERCHANT_SETTLEMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 입금을 확인했습니다 (수동)',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        PaymentStageLog.objects.create(
            transaction=payment_transaction,
            stage=PaymentStage.ORDER_FINALIZE,
            status=PaymentStageLog.STATUS_COMPLETED,
            message='스토어에서 라이브 강의 참가를 수동으로 확정했습니다.',
            detail={
                'operator': operator_label,
                'restored_at': now.isoformat(),
                'order_number': live_lecture_order.order_number,
                'merged_existing_order': merged_existing_order,
                'cancelled_duplicate_order_id': merged_original_order_id,
            },
        )

        meta = dict(metadata)
        restore_history = meta.setdefault('manual_restore_history', [])
        restore_history.append({
            'restored_at': now.isoformat(),
            'operator': operator_label,
            'type': 'live_lecture',
            'order_number': live_lecture_order.order_number,
            'merged_existing_order': merged_existing_order,
            'cancelled_duplicate_order_id': merged_original_order_id,
        })
        meta['live_lecture_order_id'] = live_lecture_order.id
        if merged_original_order_id is not None:
            meta['cancelled_duplicate_live_lecture_order_id'] = merged_original_order_id
        if isinstance(participant_data, dict):
            participant_data['live_lecture_order_id'] = live_lecture_order.id
            meta['participant'] = participant_data
        meta['manual_restored'] = True

        update_fields = {'metadata', 'live_lecture_order', 'status', 'current_stage', 'updated_at'}
        if participant_data.get('payment_hash') and not payment_transaction.payment_hash:
            payment_transaction.payment_hash = participant_data['payment_hash']
            update_fields.add('payment_hash')
        if participant_data.get('payment_request') and not payment_transaction.payment_request:
            payment_transaction.payment_request = participant_data['payment_request']
            update_fields.add('payment_request')

        payment_transaction.metadata = meta
        payment_transaction.live_lecture_order = live_lecture_order
        payment_transaction.status = PaymentTransaction.STATUS_COMPLETED
        payment_transaction.current_stage = PaymentStage.ORDER_FINALIZE
        payment_transaction.save(update_fields=list(update_fields))

    try:
        send_live_lecture_notification_email(live_lecture_order)
        send_live_lecture_participant_confirmation_email(live_lecture_order)
    except Exception:  # pylint: disable=broad-except
        logger.warning(
            '라이브 강의 수동 복구 이메일 발송 실패 order=%s',
            live_lecture_order.order_number,
            exc_info=True,
        )

    return live_lecture_order


def restore_file_transaction(payment_transaction, *, operator=None):
    """수동으로 디지털 파일 결제 트랜잭션을 구매 확정 상태로 복구한다."""
    from django.utils import timezone
    from file.models import FileOrder
    from file.services import (
        send_file_buyer_confirmation_email,
        send_file_purchase_notification_email,
    )
    from ln_payment.models import PaymentStageLog, PaymentTransaction
    from ln_payment.services import PaymentStage

    metadata = payment_transaction.metadata if isinstance(payment_transaction.metadata, dict) else {}
    file_order = payment_transaction.file_order
    if not file_order:
        file_order_id = metadata.get('file_order_id')
        if file_order_id:
            file_order = FileOrder.objects.filter(id=file_order_id).first()
    if not file_order:
        raise ValueError('연결된 파일 주문을 찾을 수 없습니다.')

    now = timezone.now()
    operator_label = getattr(operator, 'username', None) or getattr(operator, 'email', None)

    with transaction.atomic():
        file_order.status = 'confirmed'
        file_order.is_temporary_reserved = False
        file_order.auto_cancelled_reason = ''
        if not file_order.paid_at:
            file_order.paid_at = payment_transaction.updated_at or now
        if not file_order.confirmed_at:
            file_order.confirmed_at = now
        if file_order.digital_file.download_expiry_days and not file_order.download_expires_at:
            file_order.download_expires_at = now + timezone.timedelta(days=file_order.digital_file.download_expiry_days)
        file_order.payment_hash = payment_transaction.payment_hash or file_order.payment_hash
        file_order.payment_request = payment_transaction.payment_request or file_order.payment_request
        file_order.save(update_fields=[
            'status',
            'is_temporary_reserved',
            'auto_cancelled_reason',
            'paid_at',
            'confirmed_at',
            'download_expires_at',
            'payment_hash',
            'payment_request',
            'updated_at',
        ])

        payment_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.USER_PAYMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()
        if not payment_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.USER_PAYMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 확인을 수동으로 완료 처리했습니다.',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        settlement_completed = payment_transaction.stage_logs.filter(
            stage=PaymentStage.MERCHANT_SETTLEMENT,
            status=PaymentStageLog.STATUS_COMPLETED,
        ).exists()
        if not settlement_completed:
            PaymentStageLog.objects.create(
                transaction=payment_transaction,
                stage=PaymentStage.MERCHANT_SETTLEMENT,
                status=PaymentStageLog.STATUS_COMPLETED,
                message='스토어에서 결제 입금을 확인했습니다 (수동)',
                detail={
                    'manual': True,
                    'operator': operator_label,
                    'recorded_at': now.isoformat(),
                },
            )

        PaymentStageLog.objects.create(
            transaction=payment_transaction,
            stage=PaymentStage.ORDER_FINALIZE,
            status=PaymentStageLog.STATUS_COMPLETED,
            message='스토어에서 파일 주문을 수동으로 확정했습니다.',
            detail={
                'operator': operator_label,
                'restored_at': now.isoformat(),
                'order_number': file_order.order_number,
            },
        )

        meta = dict(metadata)
        restore_history = meta.setdefault('manual_restore_history', [])
        restore_history.append({
            'restored_at': now.isoformat(),
            'operator': operator_label,
            'type': 'file',
            'order_number': file_order.order_number,
        })
        meta['manual_restored'] = True

        update_fields = {'metadata', 'file_order', 'status', 'current_stage', 'updated_at'}
        payment_transaction.metadata = meta
        payment_transaction.file_order = file_order
        payment_transaction.status = PaymentTransaction.STATUS_COMPLETED
        payment_transaction.current_stage = PaymentStage.ORDER_FINALIZE
        payment_transaction.save(update_fields=list(update_fields))

    try:
        send_file_purchase_notification_email(file_order)
        send_file_buyer_confirmation_email(file_order)
    except Exception:  # pylint: disable=broad-except
        logger.warning('파일 주문 수동 복구 이메일 발송 실패 order=%s', file_order.order_number, exc_info=True)

    return file_order
