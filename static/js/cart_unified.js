// 통합 장바구니 JavaScript

// 전역 변수
let cartData = [];
let currentStoreId = null;

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeCart();
});

// 장바구니 초기화
function initializeCart() {
    loadCartFromStorage();
    updateAllCartDisplays();
    
    // 스토어 ID 설정 (페이지에서 제공하는 경우)
    const storeElement = document.querySelector('[data-store-id]');
    if (storeElement) {
        currentStoreId = storeElement.dataset.storeId;
    }
}

// 로컬 스토리지에서 장바구니 데이터 로드
function loadCartFromStorage() {
    cartData = JSON.parse(localStorage.getItem('cart') || '[]');
}

// 로컬 스토리지에 장바구니 데이터 저장
function saveCartToStorage() {
    localStorage.setItem('cart', JSON.stringify(cartData));
}

// 모든 장바구니 디스플레이 업데이트
function updateAllCartDisplays() {
    updateSidebarCart();
    updatePageCart();
}

// 사이드바 장바구니 업데이트
function updateSidebarCart() {
    const cartItemsContainer = document.getElementById('cart-items');
    const emptyCartElement = document.getElementById('empty-cart');
    const cartTotalElement = document.getElementById('cart-total');
    const totalAmountElement = document.getElementById('total-amount');

    if (!cartItemsContainer) return;

    let totalAmount = 0;
    let totalItems = 0;

    if (cartData.length === 0) {
        // 장바구니가 비어있을 때
        if (emptyCartElement) emptyCartElement.classList.remove('hidden');
        if (cartTotalElement) cartTotalElement.classList.add('hidden');
        cartItemsContainer.innerHTML = '<div id="empty-cart" class="text-center py-8"><i class="fas fa-shopping-cart text-gray-400 text-3xl mb-3"></i><p class="text-gray-500 text-sm">장바구니가 비어있습니다</p></div>';
        return;
    }

    // 장바구니에 아이템이 있을 때
    if (emptyCartElement) emptyCartElement.classList.add('hidden');
    if (cartTotalElement) cartTotalElement.classList.remove('hidden');

    let cartHTML = '';
    cartData.forEach(item => {
        const itemTotal = item.totalPrice * item.quantity;
        totalAmount += itemTotal;
        totalItems += item.quantity;

        // 옵션 텍스트 생성
        let optionsText = '';
        if (item.options && Object.keys(item.options).length > 0) {
            const optionTexts = Object.entries(item.options).map(([key, value]) => {
                return `${key}: ${value.value}`;
            });
            optionsText = optionTexts.join(', ');
        }

        cartHTML += `
            <div class="bg-white p-3 rounded-lg border border-gray-200 cart-item" data-item-id="${item.id}">
                <div class="flex justify-between items-start mb-2">
                    <h4 class="font-medium text-sm">${escapeHtml(item.name)}</h4>
                    <button onclick="removeCartItem('${item.id}')" class="text-red-500 hover:text-red-700 transition-colors">
                        <i class="fas fa-times text-xs"></i>
                    </button>
                </div>
                ${optionsText ? `<div class="text-xs text-gray-600 mb-2">${escapeHtml(optionsText)}</div>` : ''}
                <div class="flex justify-between items-center">
                    <div class="flex items-center space-x-2">
                        <button onclick="updateItemQuantity('${item.id}', ${item.quantity - 1})" 
                                class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors flex items-center justify-center">
                            <i class="fas fa-minus"></i>
                        </button>
                        <span class="text-sm font-medium min-w-[1.5rem] text-center">${item.quantity}</span>
                        <button onclick="updateItemQuantity('${item.id}', ${item.quantity + 1})" 
                                class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors flex items-center justify-center">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <span class="text-sm font-semibold text-blue-600">${formatNumber(itemTotal)} sats</span>
                </div>
            </div>
        `;
    });

    cartItemsContainer.innerHTML = cartHTML;
    if (totalAmountElement) {
        totalAmountElement.textContent = `${formatNumber(totalAmount)} sats`;
    }
}

// 전체 페이지 장바구니 업데이트
function updatePageCart() {
    const cartPageItemsList = document.getElementById('cart-page-items-list');
    const cartPageEmptyCart = document.getElementById('cart-page-empty-cart');
    const cartPageOrderSummary = document.getElementById('cart-page-order-summary');
    const cartPageItemCount = document.getElementById('cart-page-item-count');
    const cartPageTotalAmount = document.getElementById('cart-page-total-amount');
    const cartPageSubtotalAmount = document.getElementById('cart-page-subtotal-amount');
    const cartPageFinalTotalAmount = document.getElementById('cart-page-final-total-amount');

    if (!cartPageItemsList) return;

    let totalAmount = 0;
    let totalItems = 0;

    if (cartData.length === 0) {
        // 장바구니가 비어있을 때
        if (cartPageEmptyCart) cartPageEmptyCart.classList.remove('hidden');
        if (cartPageOrderSummary) cartPageOrderSummary.classList.add('hidden');
        cartPageItemsList.innerHTML = '';
        if (cartPageItemCount) cartPageItemCount.textContent = '0';
        if (cartPageTotalAmount) cartPageTotalAmount.textContent = '0 sats';
        return;
    }

    // 장바구니에 아이템이 있을 때
    if (cartPageEmptyCart) cartPageEmptyCart.classList.add('hidden');
    if (cartPageOrderSummary) cartPageOrderSummary.classList.remove('hidden');

    let cartHTML = '';
    cartData.forEach(item => {
        const itemTotal = item.totalPrice * item.quantity;
        totalAmount += itemTotal;
        totalItems += item.quantity;

        // 옵션 텍스트 생성
        let optionsText = '';
        if (item.options && Object.keys(item.options).length > 0) {
            const optionTexts = Object.entries(item.options).map(([key, value]) => {
                return `${key}: ${value.value}`;
            });
            optionsText = optionTexts.join(', ');
        }

        cartHTML += `
            <div class="cart-item-page p-4" data-item-id="${item.id}">
                <div class="flex items-start space-x-4">
                    <!-- 메뉴 이미지 플레이스홀더 -->
                    <div class="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <i class="fas fa-utensils text-gray-400 text-xl"></i>
                    </div>
                    
                    <!-- 메뉴 정보 -->
                    <div class="flex-1 min-w-0">
                        <h3 class="text-lg font-semibold text-gray-900 mb-1">${escapeHtml(item.name)}</h3>
                        ${optionsText ? `<p class="text-sm text-gray-600 mb-2">${escapeHtml(optionsText)}</p>` : ''}
                        <div class="flex items-center justify-between">
                            <div class="flex items-center space-x-3">
                                <button onclick="updateItemQuantity('${item.id}', ${item.quantity - 1})" 
                                        class="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-lg flex items-center justify-center transition-colors">
                                    <i class="fas fa-minus text-gray-600 text-sm"></i>
                                </button>
                                <span class="text-lg font-semibold text-gray-900 min-w-[2rem] text-center">${item.quantity}</span>
                                <button onclick="updateItemQuantity('${item.id}', ${item.quantity + 1})" 
                                        class="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-lg flex items-center justify-center transition-colors">
                                    <i class="fas fa-plus text-gray-600 text-sm"></i>
                                </button>
                            </div>
                            <div class="text-right">
                                <div class="text-lg font-bold text-gray-900">${formatNumber(itemTotal)} sats</div>
                                <div class="text-sm text-gray-600">${formatNumber(item.totalPrice)} sats × ${item.quantity}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 삭제 버튼 -->
                    <button onclick="removeCartItem('${item.id}')" 
                            class="p-2 text-gray-400 hover:text-red-500 transition-colors">
                        <i class="fas fa-trash text-sm"></i>
                    </button>
                </div>
            </div>
        `;
    });

    cartPageItemsList.innerHTML = cartHTML;
    
    // 헤더 정보 업데이트
    if (cartPageItemCount) cartPageItemCount.textContent = totalItems;
    if (cartPageTotalAmount) cartPageTotalAmount.textContent = `${formatNumber(totalAmount)} sats`;
    if (cartPageSubtotalAmount) cartPageSubtotalAmount.textContent = `${formatNumber(totalAmount)} sats`;
    if (cartPageFinalTotalAmount) cartPageFinalTotalAmount.textContent = `${formatNumber(totalAmount)} sats`;
}

// 장바구니에 아이템 추가
function addToCart(menuItem) {
    // 같은 메뉴, 같은 옵션인지 확인
    const existingItemIndex = cartData.findIndex(item => {
        if (item.id !== menuItem.id) return false;
        
        // 옵션 비교
        const itemOptions = item.options || {};
        const newOptions = menuItem.options || {};
        
        const itemOptionKeys = Object.keys(itemOptions).sort();
        const newOptionKeys = Object.keys(newOptions).sort();
        
        if (itemOptionKeys.length !== newOptionKeys.length) return false;
        
        for (let key of itemOptionKeys) {
            if (!newOptions[key] || itemOptions[key].value !== newOptions[key].value) {
                return false;
            }
        }
        
        return true;
    });
    
    if (existingItemIndex !== -1) {
        // 기존 아이템의 수량 증가
        cartData[existingItemIndex].quantity += menuItem.quantity;
    } else {
        // 새로운 아이템 추가
        cartData.push(menuItem);
    }
    
    saveCartToStorage();
    updateAllCartDisplays();
}

// 장바구니 아이템 수량 업데이트
function updateItemQuantity(itemId, newQuantity) {
    if (newQuantity < 1) {
        removeCartItem(itemId);
        return;
    }
    
    const itemIndex = cartData.findIndex(item => item.id == itemId);
    
    if (itemIndex !== -1) {
        cartData[itemIndex].quantity = newQuantity;
        saveCartToStorage();
        updateAllCartDisplays();
    }
}

// 장바구니 아이템 삭제
function removeCartItem(itemId) {
    cartData = cartData.filter(item => item.id != itemId);
    saveCartToStorage();
    
    // 삭제 애니메이션 효과
    const itemElements = document.querySelectorAll(`[data-item-id="${itemId}"]`);
    itemElements.forEach(itemElement => {
        if (itemElement) {
            itemElement.style.transform = 'translateX(-100%)';
            itemElement.style.opacity = '0';
            itemElement.style.transition = 'all 0.2s ease-out';
        }
    });
    
    setTimeout(() => {
        updateAllCartDisplays();
    }, 200);
}

// 전체 장바구니 비우기
function clearCart() {
    if (cartData.length === 0) {
        return;
    }
    
    if (confirm('장바구니를 비우시겠습니까?')) {
        cartData = [];
        saveCartToStorage();
        updateAllCartDisplays();
    }
}

// 장바구니 페이지 열기
function openCartPage() {
    const cartPageOverlay = document.getElementById('cart-page-overlay');
    if (cartPageOverlay) {
        cartPageOverlay.classList.remove('hidden');
        updatePageCart();
        // 스크롤 방지
        document.body.style.overflow = 'hidden';
    }
}

// 장바구니 페이지 닫기
function closeCartPage() {
    const cartPageOverlay = document.getElementById('cart-page-overlay');
    if (cartPageOverlay) {
        cartPageOverlay.classList.add('hidden');
        // 스크롤 복원
        document.body.style.overflow = '';
    }
}

// 주문 처리 (사이드바에서)
function processOrder() {
    if (cartData.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // 장바구니 페이지 열기
    openCartPage();
}

// 주문 처리 (전체 페이지에서)
function processOrderFromPage() {
    if (cartData.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    const totalAmount = cartData.reduce((sum, item) => sum + (item.totalPrice * item.quantity), 0);
    const totalItems = cartData.reduce((sum, item) => sum + item.quantity, 0);
    
    const confirmMessage = `총 ${totalItems}개 메뉴, ${formatNumber(totalAmount)} sats를 주문하시겠습니까?`;
    
    if (confirm(confirmMessage)) {
        // 주문 처리 로직 (실제 구현 시 서버로 데이터 전송)
        console.log('주문 데이터:', {
            items: cartData,
            totalAmount: totalAmount,
            totalItems: totalItems,
            timestamp: new Date().toISOString(),
            storeId: currentStoreId
        });
        
        // 임시: 결제 완료 메시지
        alert('결제가 완료되었습니다!\n\n결제 기능은 현재 개발 중입니다.');
        
        // 주문 완료 후 장바구니 비우기 (나중에 실제 주문 완료 후에 실행)
        // cartData = [];
        // saveCartToStorage();
        // updateAllCartDisplays();
        // closeCartPage();
    }
}

// 장바구니 표시 업데이트 (외부에서 호출용)
function updateCartDisplay() {
    updateAllCartDisplays();
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

// 전역으로 노출할 함수들
window.addToCart = addToCart;
window.updateItemQuantity = updateItemQuantity;
window.removeCartItem = removeCartItem;
window.clearCart = clearCart;
window.processOrder = processOrder;
window.processOrderFromPage = processOrderFromPage;
window.openCartPage = openCartPage;
window.closeCartPage = closeCartPage;
window.updateCartDisplay = updateCartDisplay; 