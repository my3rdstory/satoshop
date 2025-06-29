// 메뉴판 전용 JavaScript

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeCategoryFilters();
    updateCartDisplay();
});

// 카테고리 필터링 초기화
function initializeCategoryFilters() {
    document.querySelectorAll('.category-item').forEach(item => {
        item.addEventListener('click', function() {
            // 활성 상태 변경
            document.querySelectorAll('.category-item').forEach(cat => {
                cat.classList.remove('active');
            });
            this.classList.add('active');
            
            const categoryId = this.dataset.category;
            filterMenusByCategory(categoryId);
        });
    });
}

// 카테고리별 메뉴 필터링
function filterMenusByCategory(categoryId) {
    const menuCards = document.querySelectorAll('.menu-card');
    
    menuCards.forEach(card => {
        if (categoryId === 'all') {
            card.style.display = 'block';
        } else {
            const categories = JSON.parse(card.dataset.categories);
            if (categories.includes(parseInt(categoryId))) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        }
    });
}

// 장바구니에서 메뉴 제거
function removeFromCart(itemId) {
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    cart = cart.filter(item => item.id != itemId);
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartDisplay();
}

// 수량 업데이트
function updateQuantity(itemId, quantity) {
    if (quantity < 1) {
        removeFromCart(itemId);
        return;
    }
    
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const itemIndex = cart.findIndex(item => item.id == itemId);
    
    if (itemIndex !== -1) {
        cart[itemIndex].quantity = quantity;
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartDisplay();
    }
}

// 장바구니 화면 업데이트
function updateCartDisplay() {
    const cartItemsContainer = document.getElementById('cart-items');
    const emptyCart = document.getElementById('empty-cart');
    const cartTotal = document.getElementById('cart-total');
    const totalAmount = document.getElementById('total-amount');
    
    // 로컬 스토리지에서 장바구니 데이터 가져오기
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    if (cart.length === 0) {
        // 장바구니가 비어있을 때
        if (cartItemsContainer) {
            cartItemsContainer.innerHTML = '<div id="empty-cart" class="text-center py-8"><i class="fas fa-shopping-cart text-gray-400 text-3xl mb-3"></i><p class="text-gray-500 text-sm">장바구니가 비어있습니다</p></div>';
        }
        if (cartTotal) cartTotal.classList.add('hidden');
    } else {
        // 장바구니에 아이템이 있을 때
        if (cartTotal) cartTotal.classList.remove('hidden');
        
        let total = 0;
        let cartHTML = '';
        
        cart.forEach(item => {
            const itemTotal = item.totalPrice * item.quantity;
            total += itemTotal;
            
            // 옵션 문자열 생성
            let optionsText = '';
            if (item.options && Object.keys(item.options).length > 0) {
                const optionStrings = Object.entries(item.options).map(([name, option]) => {
                    return option.price > 0 ? `${option.value} (+${option.price})` : option.value;
                });
                optionsText = optionStrings.join(', ');
            }
            
            cartHTML += `
                <div class="bg-white p-3 rounded-lg border border-gray-200 mb-2">
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <h4 class="font-medium text-sm text-gray-900">${escapeHtml(item.name)}</h4>
                            ${optionsText ? `<p class="text-xs text-gray-600 mt-1">${escapeHtml(optionsText)}</p>` : ''}
                        </div>
                        <button onclick="removeFromCart('${item.id}')" 
                                class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors"
                                title="삭제">
                            <i class="fas fa-trash text-xs"></i>
                        </button>
                    </div>
                    <div class="flex justify-between items-center">
                        <div class="flex items-center space-x-2">
                            <button onclick="updateQuantity('${item.id}', ${item.quantity - 1})" 
                                    class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors flex items-center justify-center">
                                <i class="fas fa-minus"></i>
                            </button>
                            <span class="text-sm font-medium min-w-[1.5rem] text-center">${item.quantity}</span>
                            <button onclick="updateQuantity('${item.id}', ${item.quantity + 1})" 
                                    class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors flex items-center justify-center">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <span class="text-sm font-semibold text-blue-600">${formatNumber(itemTotal)} sats</span>
                    </div>
                </div>
            `;
        });
        
        if (cartItemsContainer) {
            cartItemsContainer.innerHTML = cartHTML;
        }
        if (totalAmount) {
            totalAmount.textContent = `${formatNumber(total)} sats`;
        }
    }
}

// 주문 처리
function processOrder() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    if (cart.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // menu_cart.js의 결제 모달 함수 호출
    if (typeof showPaymentModal === 'function') {
        // 장바구니 데이터를 menu_cart.js 형식으로 변환
        window.cartData = cart.map(item => ({
            id: item.id,
            name: item.name,
            totalPrice: item.totalPrice,
            quantity: item.quantity,
            options: item.options || {}
        }));
        
        // 스토어 ID 설정
        window.currentStoreId = window.location.pathname.split('/')[2];
        
        showPaymentModal();
    } else {
        // fallback: 장바구니 페이지로 이동
        const storeId = window.location.pathname.split('/')[2];
        window.location.href = `/menu/${storeId}/cart/`;
    }
}

// 장바구니 비우기
function clearCart() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    if (cart.length === 0) {
        return;
    }
    
    localStorage.removeItem('cart');
    updateCartDisplay();
}



// 유틸리티 함수들
function formatNumber(num) {
    return num.toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 다른 탭이나 페이지에서 장바구니가 변경될 때 동기화
window.addEventListener('storage', function(e) {
    if (e.key === 'cart') {
        updateCartDisplay();
    }
}); 