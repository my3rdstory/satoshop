// 통합 장바구니 JavaScript

// 전역 변수
let cartData = [];
let currentStoreId = null;

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 손상된 localStorage 데이터 정리
    try {
        const testData = localStorage.getItem('cart');
        if (testData && testData !== '[]') {
            JSON.parse(testData); // JSON 파싱 테스트
        }
    } catch (error) {
        console.warn('손상된 장바구니 데이터를 정리합니다:', error);
        localStorage.removeItem('cart');
    }
    
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
    try {
        const storedData = localStorage.getItem('cart');
        cartData = storedData ? JSON.parse(storedData) : [];
        
        // 데이터가 배열이 아닌 경우 빈 배열로 초기화
        if (!Array.isArray(cartData)) {
            console.warn('장바구니 데이터가 배열이 아닙니다. 초기화합니다.');
            cartData = [];
            saveCartToStorage();
            return;
        }
        
        // 기존 데이터 검증 및 수정
        cartData = cartData.filter(item => {
            // null이거나 undefined인 아이템 제거
            if (!item || typeof item !== 'object') {
                console.warn('유효하지 않은 장바구니 아이템을 제거합니다:', item);
                return false;
            }
            
            // 필수 속성 검증
            if (!item.id || !item.name) {
                console.warn('필수 속성이 없는 장바구니 아이템을 제거합니다:', item);
                return false;
            }
            
            // totalPrice 속성 수정
            if (!item.totalPrice && item.totalPrice !== 0) {
                console.warn('기존 장바구니 아이템에 totalPrice가 없습니다:', item);
                item.totalPrice = item.price || 0;
            }
            
            // quantity 속성 검증 및 수정
            if (!item.quantity || item.quantity < 1) {
                item.quantity = 1;
            }
            
            return true;
        });
        
        // 수정된 데이터 저장
        saveCartToStorage();
    } catch (error) {
        console.error('장바구니 데이터 로드 중 오류 발생:', error);
        cartData = [];
        localStorage.removeItem('cart');
    }
}

// 로컬 스토리지에 장바구니 데이터 저장
function saveCartToStorage() {
    localStorage.setItem('cart', JSON.stringify(cartData));
}

// 모든 장바구니 디스플레이 업데이트
function updateAllCartDisplays() {
    updateSidebarCart();
    updatePageCart();
    updateFullPageCart();
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
        // 아이템이 유효하지 않은 경우 건너뛰기
        if (!item || typeof item !== 'object' || !item.id || !item.name) {
            console.warn('유효하지 않은 장바구니 아이템을 건너뜁니다:', item);
            return;
        }
        
        // totalPrice가 null이거나 undefined인 경우 0으로 처리
        const itemPrice = item.totalPrice || 0;
        const itemQuantity = item.quantity || 1;
        const itemTotal = itemPrice * itemQuantity;
        totalAmount += itemTotal;
        totalItems += itemQuantity;

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
                        <button onclick="updateItemQuantity('${item.id}', ${itemQuantity - 1})" 
                                class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors flex items-center justify-center">
                            <i class="fas fa-minus"></i>
                        </button>
                        <span class="text-sm font-medium min-w-[1.5rem] text-center">${itemQuantity}</span>
                        <button onclick="updateItemQuantity('${item.id}', ${itemQuantity + 1})" 
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

// 전체 페이지 장바구니 업데이트 (오버레이)
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
        // 아이템이 유효하지 않은 경우 건너뛰기
        if (!item || typeof item !== 'object' || !item.id || !item.name) {
            console.warn('유효하지 않은 장바구니 아이템을 건너뜁니다:', item);
            return;
        }
        
        // totalPrice가 null이거나 undefined인 경우 0으로 처리
        const itemPrice = item.totalPrice || 0;
        const itemQuantity = item.quantity || 1;
        const itemTotal = itemPrice * itemQuantity;
        totalAmount += itemTotal;
        totalItems += itemQuantity;

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
                                <button onclick="updateItemQuantity('${item.id}', ${itemQuantity - 1})" 
                                        class="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-lg flex items-center justify-center transition-colors">
                                    <i class="fas fa-minus text-gray-600 text-sm"></i>
                                </button>
                                <span class="text-lg font-semibold text-gray-900 min-w-[2rem] text-center">${itemQuantity}</span>
                                <button onclick="updateItemQuantity('${item.id}', ${itemQuantity + 1})" 
                                        class="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-lg flex items-center justify-center transition-colors">
                                    <i class="fas fa-plus text-gray-600 text-sm"></i>
                                </button>
                            </div>
                            <div class="text-right">
                                <div class="text-lg font-bold text-gray-900">${formatNumber(itemTotal)} sats</div>
                                <div class="text-sm text-gray-600">${formatNumber(itemPrice)} sats × ${itemQuantity}</div>
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

// 독립 페이지 장바구니 업데이트
function updateFullPageCart() {
    const cartItemsList = document.getElementById('cart-items-list');
    const emptyCartMessage = document.getElementById('empty-cart-message');
    const orderSummary = document.getElementById('order-summary');
    const itemCount = document.getElementById('item-count');
    const totalAmount = document.getElementById('total-amount');
    const subtotalAmount = document.getElementById('subtotal-amount');
    const finalTotalAmount = document.getElementById('final-total-amount');

    if (!cartItemsList) return;

    let total = 0;
    let items = 0;

    if (cartData.length === 0) {
        // 장바구니가 비어있을 때
        cartItemsList.innerHTML = '';
        if (emptyCartMessage) emptyCartMessage.classList.remove('hidden');
        if (orderSummary) orderSummary.classList.add('hidden');
        if (itemCount) itemCount.textContent = '0';
        if (totalAmount) totalAmount.textContent = '0 sats';
        return;
    }

    // 장바구니에 아이템이 있을 때
    if (emptyCartMessage) emptyCartMessage.classList.add('hidden');
    if (orderSummary) orderSummary.classList.remove('hidden');

    let cartHTML = '';
    cartData.forEach(item => {
        // 아이템이 유효하지 않은 경우 건너뛰기
        if (!item || typeof item !== 'object' || !item.id || !item.name) {
            console.warn('유효하지 않은 장바구니 아이템을 건너뜁니다:', item);
            return;
        }
        
        // totalPrice가 null이거나 undefined인 경우 0으로 처리
        const itemPrice = item.totalPrice || 0;
        const itemQuantity = item.quantity || 1;
        const itemTotal = itemPrice * itemQuantity;
        total += itemTotal;
        items += itemQuantity;

        // 옵션 텍스트 생성
        let optionsText = '';
        if (item.options && Object.keys(item.options).length > 0) {
            const optionTexts = Object.entries(item.options).map(([key, value]) => {
                return `${key}: ${value.value}`;
            });
            optionsText = optionTexts.join(', ');
        }

        cartHTML += `
            <div class="cart-item flex items-center" data-item-id="${item.id}">
                <!-- 메뉴 이미지 -->
                <div class="cart-item-placeholder">
                    <i class="fas fa-utensils text-gray-400 text-2xl"></i>
                </div>
                
                <!-- 메뉴 정보 -->
                <div class="cart-item-info">
                    <div class="cart-item-name">${escapeHtml(item.name)}</div>
                    ${optionsText ? `<div class="cart-item-options">${escapeHtml(optionsText)}</div>` : ''}
                    <div class="cart-item-price">${formatNumber(itemPrice)} sats × ${itemQuantity}</div>
                </div>
                
                <!-- 수량 조절 -->
                <div class="quantity-controls">
                    <button class="quantity-btn" onclick="updateItemQuantity('${item.id}', ${itemQuantity - 1})">
                        <i class="fas fa-minus text-sm"></i>
                    </button>
                    <span class="quantity-display">${itemQuantity}</span>
                    <button class="quantity-btn" onclick="updateItemQuantity('${item.id}', ${itemQuantity + 1})">
                        <i class="fas fa-plus text-sm"></i>
                    </button>
                </div>
                
                <!-- 삭제 버튼 -->
                <button class="remove-btn" onclick="removeCartItem('${item.id}')" title="메뉴 삭제">
                    <i class="fas fa-trash text-sm"></i>
                </button>
            </div>
        `;
    });

    cartItemsList.innerHTML = cartHTML;
    
    // 헤더 및 요약 정보 업데이트
    if (itemCount) itemCount.textContent = items;
    if (totalAmount) totalAmount.textContent = `${formatNumber(total)} sats`;
    if (subtotalAmount) subtotalAmount.textContent = `${formatNumber(total)} sats`;
    if (finalTotalAmount) finalTotalAmount.textContent = `${formatNumber(total)} sats`;
}

// 장바구니에 아이템 추가
function addToCart(menuItem) {
    // totalPrice가 없는 경우 기본값 설정
    if (!menuItem.totalPrice && menuItem.totalPrice !== 0) {
        console.warn('menuItem.totalPrice가 없습니다:', menuItem);
        menuItem.totalPrice = menuItem.price || 0;
    }
    
    const existingItemIndex = cartData.findIndex(item => item.id === menuItem.id);
    
    if (existingItemIndex !== -1) {
        // 이미 있는 아이템이면 수량 증가
        cartData[existingItemIndex].quantity += menuItem.quantity || 1;
    } else {
        // 새로운 아이템 추가
        cartData.push({
            ...menuItem,
            quantity: menuItem.quantity || 1,
            totalPrice: menuItem.totalPrice || menuItem.price || 0
        });
    }
    
    saveCartToStorage();
    updateAllCartDisplays();
}

// 아이템 수량 업데이트
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
    itemElements.forEach(element => {
        element.style.transform = 'translateX(-100%)';
        element.style.opacity = '0';
    });
    
    setTimeout(() => {
        updateAllCartDisplays();
    }, 200);
}

// 전체 장바구니 비우기
function clearCart() {
    cartData = [];
    saveCartToStorage();
    updateAllCartDisplays();
}

// 장바구니 페이지 열기
function openCartPage() {
    const cartPageOverlay = document.getElementById('cart-page-overlay');
    if (cartPageOverlay) {
        cartPageOverlay.classList.remove('hidden');
        updatePageCart();
    }
}

// 장바구니 페이지 닫기
function closeCartPage() {
    const cartPageOverlay = document.getElementById('cart-page-overlay');
    if (cartPageOverlay) {
        cartPageOverlay.classList.add('hidden');
    }
}

// 주문 처리 (사이드바에서)
function processOrder() {
    if (cartData.length === 0) {
        return;
    }
    
    const totalAmount = cartData.reduce((sum, item) => sum + ((item.totalPrice || 0) * item.quantity), 0);
    const totalItems = cartData.reduce((sum, item) => sum + item.quantity, 0);
    
    // 주문 처리 로직 (실제 구현 시 서버로 데이터 전송)
    console.log('주문 데이터:', {
        items: cartData,
        totalAmount: totalAmount,
        totalItems: totalItems,
        storeId: currentStoreId,
        timestamp: new Date().toISOString()
    });
    
    // 임시: 콘솔에만 로그 출력
    console.log('결제가 완료되었습니다! 결제 기능은 현재 개발 중입니다.');
}

// 주문 처리 (페이지에서)
function processOrderFromPage() {
    processOrder();
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

// 페이지 새로고침 시 장바구니 데이터 유지
window.addEventListener('beforeunload', function() {
    // 장바구니 데이터는 이미 localStorage에 저장되어 있으므로 별도 처리 불필요
});

// 다른 탭에서 장바구니가 변경될 때 동기화
window.addEventListener('storage', function(e) {
    if (e.key === 'cart') {
        loadCartFromStorage();
        updateAllCartDisplays();
    }
});