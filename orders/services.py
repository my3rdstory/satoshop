from django.db import transaction
from django.contrib.auth.models import User
from products.models import Product, ProductOption, ProductOptionChoice
from .models import Cart, CartItem
import json
import logging

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
    
    def add_to_cart(self, product_id, quantity=1, selected_options=None):
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
    
    def _get_db_cart_items(self):
        """DB에서 장바구니 아이템들 가져오기"""
        try:
            cart = Cart.objects.get(user=self.user)
            items = []
            
            for cart_item in cart.items.all().select_related('product', 'product__store'):
                # 옵션 정보 처리
                options_display = []
                if cart_item.selected_options:
                    for option_id, choice_id in cart_item.selected_options.items():
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
                    'is_db_item': True
                })
            
            return items
            
        except Cart.DoesNotExist:
            return []
    
    def _add_to_db_cart(self, product, quantity, selected_options):
        """DB 장바구니에 상품 추가"""
        cart, created = Cart.objects.get_or_create(user=self.user)
        
        # 항상 새 항목으로 추가 (기존 로직 유지)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            selected_options=selected_options
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
                options_price = 0
                if item_data.get('selected_options'):
                    for option_id, choice_id in item_data['selected_options'].items():
                        try:
                            option = ProductOption.objects.get(id=option_id)
                            choice = ProductOptionChoice.objects.get(id=choice_id)
                            options_display.append({
                                'option_name': option.name,
                                'choice_name': choice.name,
                                'choice_price': choice.price
                            })
                            options_price += choice.price
                        except:
                            pass
                
                # 상품 이미지 URL
                product_image_url = None
                if product.images.first():
                    product_image_url = product.images.first().file_url
                
                unit_price = product.final_price + options_price
                total_price = unit_price * item_data['quantity']
                
                items.append({
                    'id': item_data['id'],
                    'product_id': product.id,
                    'product_title': product.title,
                    'product_image_url': product_image_url,
                    'quantity': item_data['quantity'],
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'selected_options': item_data.get('selected_options', {}),
                    'options_display': options_display,
                    'store_id': product.store.store_id,
                    'store_name': product.store.store_name,
                    'is_db_item': False
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
        
        # 새 아이템 추가
        cart_data['items'].append({
            'id': item_id,
            'product_id': product.id,
            'quantity': quantity,
            'selected_options': selected_options,
            'added_at': time.time()
        })
        
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
                    options_price = 0
                    if item.get('selected_options'):
                        for option_id, choice_id in item['selected_options'].items():
                            try:
                                choice = ProductOptionChoice.objects.get(id=choice_id)
                                options_price += choice.price
                            except:
                                pass
                    
                    unit_price = product.final_price + options_price
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