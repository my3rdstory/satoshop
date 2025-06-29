// 장바구니 전용 JavaScript

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    loadCartFromStorage();
    updateCartDisplay();
});

// 로컬 스토리지에서 장바구니 데이터 로드
function loadCartFromStorage() {
    const cartData = localStorage.getItem('cart');
    if (cartData) {
        try {
            const cart = JSON.parse(cartData);
            displayCartItems(cart);
        } catch (error) {
            console.error('장바구니 데이터 로드 실패:', error);
            localStorage.removeItem('cart');
        }
    }
}

// 장바구니 아이템 표시
function displayCartItems(cart) {
    const cartItemsList = document.getElementById('cart-items-list');
    const emptyCartMessage = document.getElementById('empty-cart-message');
    const orderSummary = document.getElementById('order-summary');
    
    if (!cart || cart.length === 0) {
        cartItemsList.innerHTML = '';
        emptyCartMessage.classList.remove('hidden');
        orderSummary.classList.add('hidden');
        updateHeaderInfo(0, 0);
        return;
    }
    
    emptyCartMessage.classList.add('hidden');
    orderSummary.classList.remove('hidden');
    
    let totalAmount = 0;
    let totalItems = 0;
    
    cartItemsList.innerHTML = cart.map(item => {
        const itemTotal = item.totalPrice * item.quantity;
        totalAmount += itemTotal;
        totalItems += item.quantity;
        
        // 옵션 문자열 생성
        let optionsText = '';
        if (item.options && Object.keys(item.options).length > 0) {
            const optionStrings = Object.entries(item.options).map(([name, option]) => {
                if (option.price > 0) {
                    return `${name}: ${option.value} (+${option.price} sats)`;
                } else {
                    return `${name}: ${option.value}`;
                }
            });
            optionsText = optionStrings.join(', ');
        }
        
        return `
            <div class="cart-item flex items-center" data-item-id="${item.id}">
                <!-- 메뉴 이미지 -->
                <div class="cart-item-placeholder">
                    <i class="fas fa-utensils text-gray-400 text-2xl"></i>
                </div>
                
                <!-- 메뉴 정보 -->
                <div class="cart-item-info">
                    <div class="cart-item-name">${escapeHtml(item.name)}</div>
                    ${optionsText ? `<div class="cart-item-options">${escapeHtml(optionsText)}</div>` : ''}
                    <div class="cart-item-price">${formatNumber(item.totalPrice)} sats × ${item.quantity}</div>
                </div>
                
                <!-- 수량 조절 -->
                <div class="quantity-controls">
                    <button class="quantity-btn" onclick="updateItemQuantity('${item.id}', ${item.quantity - 1})">
                        <i class="fas fa-minus text-sm"></i>
                    </button>
                    <span class="quantity-display">${item.quantity}</span>
                    <button class="quantity-btn" onclick="updateItemQuantity('${item.id}', ${item.quantity + 1})">
                        <i class="fas fa-plus text-sm"></i>
                    </button>
                </div>
                
                <!-- 삭제 버튼 -->
                <button class="remove-btn" onclick="removeCartItem('${item.id}')" title="메뉴 삭제">
                    <i class="fas fa-trash text-sm"></i>
                </button>
            </div>
        `;
    }).join('');
    
    updateHeaderInfo(totalItems, totalAmount);
    updateOrderSummary(totalAmount);
}

// 헤더 정보 업데이트
function updateHeaderInfo(itemCount, totalAmount) {
    document.getElementById('item-count').textContent = itemCount;
    document.getElementById('total-amount').textContent = formatNumber(totalAmount) + ' sats';
}

// 주문 요약 업데이트
function updateOrderSummary(totalAmount) {
    document.getElementById('subtotal-amount').textContent = formatNumber(totalAmount) + ' sats';
    document.getElementById('final-total-amount').textContent = formatNumber(totalAmount) + ' sats';
}

// 장바구니 아이템 수량 업데이트
function updateItemQuantity(itemId, newQuantity) {
    if (newQuantity < 1) {
        removeCartItem(itemId);
        return;
    }
    
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const itemIndex = cart.findIndex(item => item.id == itemId);
    
    if (itemIndex !== -1) {
        cart[itemIndex].quantity = newQuantity;
        localStorage.setItem('cart', JSON.stringify(cart));
        displayCartItems(cart);
    }
}

// 장바구니 아이템 삭제
function removeCartItem(itemId) {
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    cart = cart.filter(item => item.id != itemId);
    localStorage.setItem('cart', JSON.stringify(cart));
    
    // 삭제 애니메이션 효과
    const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
    if (itemElement) {
        itemElement.style.transform = 'translateX(-100%)';
        itemElement.style.opacity = '0';
        setTimeout(() => {
            displayCartItems(cart);
        }, 200);
    } else {
        displayCartItems(cart);
    }
}

// 전체 장바구니 비우기
function clearCart() {
    localStorage.removeItem('cart');
    displayCartItems([]);
}

// 주문 처리
function processOrder() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    if (cart.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    const totalAmount = cart.reduce((sum, item) => sum + (item.totalPrice * item.quantity), 0);
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    
    const confirmMessage = `총 ${totalItems}개 메뉴, ${formatNumber(totalAmount)} sats를 주문하시겠습니까?`;
    
    if (confirm(confirmMessage)) {
        // 주문 처리 로직 (실제 구현 시 서버로 데이터 전송)
        console.log('주문 데이터:', {
            items: cart,
            totalAmount: totalAmount,
            totalItems: totalItems,
            timestamp: new Date().toISOString()
        });
        
        // 임시: 결제 완료 메시지
        alert('결제가 완료되었습니다!\n\n결제 기능은 현재 개발 중입니다.');
        
        // 주문 완료 후 장바구니 비우기 (나중에 실제 주문 완료 후에 실행)
        // localStorage.removeItem('cart');
        // displayCartItems([]);
    }
}

// 장바구니 표시 업데이트 (다른 페이지에서 호출용)
function updateCartDisplay() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    displayCartItems(cart);
}

// 유틸리티 함수들
function formatNumber(num) {
    return Math.round(num).toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 페이지 새로고침 시 장바구니 데이터 유지
window.addEventListener('beforeunload', function() {
    // 장바구니 데이터는 이미 localStorage에 저장되어 있으므로 별도 처리 불필요
});

// 다른 탭에서 장바구니가 변경될 때 동기화
window.addEventListener('storage', function(e) {
    if (e.key === 'cart') {
        loadCartFromStorage();
    }
}); 