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
    
    // 스토어 ID 설정
    const storeIdElement = document.querySelector('[data-store-id]');
    if (storeIdElement) {
        currentStoreId = storeIdElement.getAttribute('data-store-id');
    } else {
        // URL에서 스토어 ID 추출
        const pathParts = window.location.pathname.split('/');
        if (pathParts.length > 2) {
            currentStoreId = pathParts[2];
        }
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
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // 결제 화면 표시
    showPaymentModal();
}

// 주문 처리 (페이지에서)
function processOrderFromPage() {
    processOrder();
}

// 결제 관련 변수
let currentPaymentHash = null;
let paymentCheckInterval = null;
let paymentCountdownInterval = null;
let paymentExpiresAt = null;

// 결제 화면 표시
function showPaymentModal() {
    const totalAmount = cartData.reduce((sum, item) => sum + ((item.totalPrice || 0) * item.quantity), 0);
    const totalItems = cartData.reduce((sum, item) => sum + item.quantity, 0);
    
    if (totalAmount <= 0) {
        alert('결제 금액이 올바르지 않습니다.');
        return;
    }
    
    // 결제 화면을 메뉴 콘텐츠 영역에 표시
    const menuContent = document.querySelector('.menu-content');
    if (!menuContent) {
        alert('결제 화면을 표시할 수 없습니다.');
        return;
    }
    
    // 기존 결제 화면이 있으면 제거
    const existingPaymentView = document.getElementById('payment-view');
    if (existingPaymentView) {
        existingPaymentView.remove();
    }
    
    // 기존 콘텐츠 숨기기
    const existingViews = menuContent.querySelectorAll('.content-view');
    existingViews.forEach(view => view.classList.remove('active'));
    
    // 결제 화면 HTML 생성
    const paymentHTML = `
        <div id="payment-view" class="content-view active">
            <div class="p-6">
                <div class="bg-white rounded-lg shadow-lg">
                    <!-- 헤더 -->
                    <div class="p-6 border-b border-gray-200">
                        <div class="flex items-center justify-between">
                            <h2 class="text-2xl font-bold text-gray-900">결제하기</h2>
                            <button onclick="closePaymentView()" class="text-gray-400 hover:text-gray-600 text-2xl">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- 내용 -->
                    <div class="p-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- 왼쪽: 주문 목록 -->
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900 mb-4">주문 내역</h3>
                            <div class="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                                <div id="payment-order-list" class="space-y-3">
                                    <!-- 주문 목록이 여기에 동적으로 추가됩니다 -->
                                </div>
                                <div class="border-t border-gray-200 mt-4 pt-4">
                                    <div class="flex justify-between items-center text-lg font-bold">
                                        <span>총 결제 금액</span>
                                        <span class="text-blue-600">${formatNumber(totalAmount)} sats</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 오른쪽: 결제 정보 -->
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900 mb-4">결제 정보</h3>
                            
                            <!-- 인보이스 생성 전 -->
                            <div id="payment-initial" class="text-center">
                                <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
                                    <i class="fas fa-bolt text-blue-600 text-3xl mb-3"></i>
                                    <h4 class="text-lg font-semibold text-blue-900 mb-2">라이트닝 결제</h4>
                                    <p class="text-blue-700 text-sm">빠르고 저렴한 비트코인 결제</p>
                                </div>
                                <button onclick="generatePaymentInvoice()" 
                                        class="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 px-6 rounded-lg font-medium transition-colors">
                                    <i class="fas fa-qrcode mr-2"></i>결제 인보이스 생성
                                </button>
                            </div>
                            
                            <!-- 로딩 -->
                            <div id="payment-loading" class="hidden text-center py-8">
                                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
                                <p class="text-gray-600">인보이스를 생성하고 있습니다...</p>
                            </div>
                            
                            <!-- QR 코드 및 인보이스 -->
                            <div id="payment-invoice" class="hidden">
                                <!-- 카운트다운 타이머 -->
                                <div id="payment-countdown" class="text-center mb-6">
                                    <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                                        <div class="text-red-600 text-2xl font-bold" id="countdown-timer">15:00</div>
                                        <div class="text-red-500 text-sm">인보이스 유효 시간</div>
                                    </div>
                                </div>
                                
                                <!-- QR 코드 -->
                                <div class="text-center mb-4">
                                    <div id="qr-code-container" class="inline-block p-4 bg-white border-2 border-gray-300 rounded-lg">
                                        <!-- QR 코드가 여기에 생성됩니다 -->
                                    </div>
                                </div>
                                
                                <!-- 인보이스 텍스트 -->
                                <div class="mb-4">
                                    <label class="block text-sm font-medium text-gray-700 mb-2">인보이스</label>
                                    <div class="relative">
                                        <textarea id="invoice-text" readonly 
                                                class="w-full h-20 p-3 border border-gray-300 rounded-lg text-xs font-mono resize-none"></textarea>
                                        <button onclick="copyInvoiceText()" 
                                                class="absolute top-2 right-2 text-gray-400 hover:text-gray-600">
                                            <i class="fas fa-copy"></i>
                                        </button>
                                    </div>
                                </div>
                                
                                <!-- 취소 버튼 -->
                                <button onclick="cancelPayment()" 
                                        class="w-full bg-red-500 hover:bg-red-600 text-white py-3 px-6 rounded-lg font-medium transition-colors">
                                    <i class="fas fa-times mr-2"></i>결제 취소
                                </button>
                            </div>
                            
                            <!-- 결제 완료 -->
                            <div id="payment-success" class="hidden text-center py-8">
                                <i class="fas fa-check-circle text-green-500 text-6xl mb-4"></i>
                                <h4 class="text-xl font-bold text-green-600 mb-2">결제 완료!</h4>
                                <p class="text-gray-600 mb-6">주문이 성공적으로 처리되었습니다.</p>
                                <button onclick="closePaymentView()" 
                                        class="bg-green-500 hover:bg-green-600 text-white py-3 px-6 rounded-lg font-medium transition-colors">
                                    확인
                                </button>
                            </div>
                            
                            <!-- 결제 취소됨 -->
                            <div id="payment-cancelled" class="hidden text-center py-8">
                                <i class="fas fa-times-circle text-red-500 text-6xl mb-4"></i>
                                <h4 class="text-xl font-bold text-red-600 mb-2">결제가 취소되었습니다</h4>
                                <p class="text-gray-600 mb-6">다시 결제하려면 오른쪽 장바구니의 결제하기 버튼을 클릭하세요.</p>
                                <button onclick="closePaymentView()" 
                                        class="bg-gray-500 hover:bg-gray-600 text-white py-3 px-6 rounded-lg font-medium transition-colors">
                                    확인
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 결제 화면을 메뉴 콘텐츠에 추가
    menuContent.insertAdjacentHTML('beforeend', paymentHTML);
    
    // 주문 목록 업데이트
    updatePaymentOrderList();
}

// 결제 화면 닫기
function closePaymentView() {
    // 결제 상태 확인 중지
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        paymentCheckInterval = null;
    }
    
    // 카운트다운 중지
    if (paymentCountdownInterval) {
        clearInterval(paymentCountdownInterval);
        paymentCountdownInterval = null;
    }
    
    // 결제 화면 제거하고 메뉴 그리드로 돌아가기
    const paymentView = document.getElementById('payment-view');
    if (paymentView) {
        paymentView.remove();
    }
    
    // 메뉴 그리드 뷰 다시 활성화
    const menuGridView = document.getElementById('menu-grid-view');
    if (menuGridView) {
        menuGridView.classList.add('active');
    }
    
    // 결제 관련 변수 초기화
    currentPaymentHash = null;
    paymentExpiresAt = null;
}

// 주문 목록 업데이트
function updatePaymentOrderList() {
    const orderList = document.getElementById('payment-order-list');
    if (!orderList) return;
    
    let orderHTML = '';
    cartData.forEach(item => {
        const itemTotal = (item.totalPrice || 0) * item.quantity;
        
        // 옵션 텍스트 생성
        let optionsText = '';
        if (item.options && Object.keys(item.options).length > 0) {
            const optionTexts = Object.entries(item.options).map(([key, value]) => {
                return `${key}: ${value.value}`;
            });
            optionsText = optionTexts.join(', ');
        }
        
        orderHTML += `
            <div class="flex items-center justify-between p-3 bg-white rounded border">
                <div class="flex-1">
                    <div class="font-medium text-gray-900">${escapeHtml(item.name)}</div>
                    ${optionsText ? `<div class="text-sm text-gray-500">${escapeHtml(optionsText)}</div>` : ''}
                    <div class="text-sm text-blue-600">${formatNumber(item.totalPrice || 0)} sats × ${item.quantity}</div>
                </div>
                <div class="text-right">
                    <div class="font-medium text-gray-900">${formatNumber(itemTotal)} sats</div>
                </div>
            </div>
        `;
    });
    
    orderList.innerHTML = orderHTML;
}

// 결제 인보이스 생성
function generatePaymentInvoice() {
    const totalAmount = cartData.reduce((sum, item) => sum + ((item.totalPrice || 0) * item.quantity), 0);
    
    if (totalAmount <= 0) {
        alert('결제 금액이 올바르지 않습니다.');
        return;
    }
    
    // UI 상태 변경
    document.getElementById('payment-initial').classList.add('hidden');
    document.getElementById('payment-loading').classList.remove('hidden');
    
    // 스토어 ID 가져오기
    const storeId = currentStoreId || window.location.pathname.split('/')[2];
    
    // 서버에 인보이스 생성 요청
    fetch(`/menu/${storeId}/cart/create-invoice/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            cart_items: cartData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 인보이스 생성 성공
            currentPaymentHash = data.payment_hash;
            paymentExpiresAt = new Date(data.expires_at);
            
            // QR 코드 생성
            generateQRCode(data.invoice);
            
            // 인보이스 텍스트 표시
            document.getElementById('invoice-text').value = data.invoice;
            
            // UI 상태 변경
            document.getElementById('payment-loading').classList.add('hidden');
            document.getElementById('payment-invoice').classList.remove('hidden');
            
            // 카운트다운 시작
            startPaymentCountdown();
            
            // 결제 상태 확인 시작
            startPaymentStatusCheck();
            
        } else {
            // 인보이스 생성 실패
            alert('인보이스 생성에 실패했습니다: ' + data.error);
            
            // UI 상태 복원
            document.getElementById('payment-loading').classList.add('hidden');
            document.getElementById('payment-initial').classList.remove('hidden');
        }
    })
    .catch(error => {
        console.error('인보이스 생성 오류:', error);
        alert('인보이스 생성 중 오류가 발생했습니다.');
        
        // UI 상태 복원
        document.getElementById('payment-loading').classList.add('hidden');
        document.getElementById('payment-initial').classList.remove('hidden');
    });
}

// QR 코드 생성
function generateQRCode(invoice) {
    const container = document.getElementById('qr-code-container');
    if (!container) return;
    
    // QR 코드 라이브러리가 있는지 확인
    if (typeof QRCode !== 'undefined') {
        try {
            // QRCode.js 라이브러리 사용
            container.innerHTML = '';
            const qr = new QRCode(container, {
                text: invoice,
                width: 256,
                height: 256,
                colorDark: '#000000',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.M
            });
        } catch (error) {
            console.warn('QRCode.js 라이브러리 오류:', error);
            // fallback으로 API 사용
            generateQRCodeWithAPI(invoice, container);
        }
    } else if (typeof window.QRCode !== 'undefined') {
        try {
            // window.QRCode 사용
            container.innerHTML = '';
            window.QRCode.toCanvas(container, invoice, {
                width: 256,
                margin: 2
            });
        } catch (error) {
            console.warn('window.QRCode 오류:', error);
            generateQRCodeWithAPI(invoice, container);
        }
    } else {
        // QR 코드 API 사용 (fallback)
        generateQRCodeWithAPI(invoice, container);
    }
}

// API를 사용한 QR 코드 생성
function generateQRCodeWithAPI(invoice, container) {
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(invoice)}`;
    container.innerHTML = `<img src="${qrUrl}" alt="QR Code" class="max-w-full h-auto border rounded">`;
}

// 카운트다운 시작
function startPaymentCountdown() {
    if (!paymentExpiresAt) return;
    
    paymentCountdownInterval = setInterval(() => {
        const now = new Date();
        const timeLeft = paymentExpiresAt - now;
        
        if (timeLeft <= 0) {
            // 시간 만료
            clearInterval(paymentCountdownInterval);
            document.getElementById('countdown-timer').textContent = '00:00';
            
            // 결제 상태 확인 중지
            if (paymentCheckInterval) {
                clearInterval(paymentCheckInterval);
                paymentCheckInterval = null;
            }
            
            alert('인보이스가 만료되었습니다. 다시 시도해주세요.');
            closePaymentView();
            return;
        }
        
        // 시간 포맷팅
        const minutes = Math.floor(timeLeft / 60000);
        const seconds = Math.floor((timeLeft % 60000) / 1000);
        const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        document.getElementById('countdown-timer').textContent = timeString;
    }, 1000);
}

// 결제 상태 확인 시작
function startPaymentStatusCheck() {
    if (!currentPaymentHash) return;
    
    const storeId = currentStoreId || window.location.pathname.split('/')[2];
    
    paymentCheckInterval = setInterval(() => {
        fetch(`/menu/${storeId}/cart/check-payment/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                payment_hash: currentPaymentHash
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.status === 'paid') {
                    // 결제 완료
                    clearInterval(paymentCheckInterval);
                    clearInterval(paymentCountdownInterval);
                    
                    // UI 상태 변경
                    document.getElementById('payment-invoice').classList.add('hidden');
                    document.getElementById('payment-success').classList.remove('hidden');
                    
                    // 장바구니 비우기
                    clearCart();
                    
                } else if (data.status === 'expired') {
                    // 인보이스 만료
                    clearInterval(paymentCheckInterval);
                    clearInterval(paymentCountdownInterval);
                    
                    alert('인보이스가 만료되었습니다.');
                    closePaymentView();
                }
                // pending인 경우 계속 확인
            } else {
                console.error('결제 상태 확인 오류:', data.error);
            }
        })
        .catch(error => {
            console.error('결제 상태 확인 중 오류:', error);
        });
    }, 3000); // 3초마다 확인
}

// 결제 취소
function cancelPayment() {
    if (!confirm('정말로 결제를 취소하시겠습니까?')) {
        return;
    }
    
    // 결제 상태 확인 중지
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        paymentCheckInterval = null;
    }
    
    // 카운트다운 중지
    if (paymentCountdownInterval) {
        clearInterval(paymentCountdownInterval);
        paymentCountdownInterval = null;
    }
    
    // UI 상태 변경
    document.getElementById('payment-invoice').classList.add('hidden');
    document.getElementById('payment-cancelled').classList.remove('hidden');
    
    // 결제 관련 변수 초기화
    currentPaymentHash = null;
    paymentExpiresAt = null;
}

// 인보이스 텍스트 복사
function copyInvoiceText() {
    const textarea = document.getElementById('invoice-text');
    if (textarea) {
        textarea.select();
        document.execCommand('copy');
        
        // 복사 완료 알림
        const button = event.target.closest('button');
        const originalIcon = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check text-green-500"></i>';
        
        setTimeout(() => {
            button.innerHTML = originalIcon;
        }, 2000);
    }
}

// CSRF 토큰 가져오기
function getCsrfToken() {
    // 1. 폼에서 CSRF 토큰 찾기
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        return csrfToken.value;
    }
    
    // 2. 메타 태그에서 CSRF 토큰 찾기
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        return csrfMeta.getAttribute('content');
    }
    
    // 3. 쿠키에서 CSRF 토큰 가져오기
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    
    if (!cookieValue) {
        console.warn('CSRF 토큰을 찾을 수 없습니다.');
    }
    
    return cookieValue;
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