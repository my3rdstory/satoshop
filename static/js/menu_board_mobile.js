/* 모바일 메뉴판 전용 JavaScript */

// 전역 변수
let currentView = 'menu-grid';
let currentCategory = 'all';
let mobileCart = [];
let cartTotal = 0;

// 페이지 로드 시 장바구니 데이터 복원
function loadCartFromStorage() {
    try {
        const storedCart = localStorage.getItem('mobileCart');
        if (storedCart) {
            mobileCart = JSON.parse(storedCart);
            updateCartDisplay();
            updateCartButton();
        }
    } catch (error) {
        console.error('장바구니 데이터 로드 오류:', error);
        mobileCart = [];
    }
    
    // 카테고리 아이템 클릭 이벤트 리스너 추가
    document.addEventListener('DOMContentLoaded', function() {
        const categoryItems = document.querySelectorAll('.mobile-category-item');
        categoryItems.forEach(item => {
            item.addEventListener('click', function() {
                const categoryId = this.dataset.category;
                const viewType = this.dataset.view;
                
                // 뷰 변경
                showView(viewType, categoryId);
                
                // 햄버거 메뉴 닫기
                closeMobileMenu();
            });
        });
    });
}

// 장바구니 데이터를 localStorage에 저장
function saveCartToStorage() {
    try {
        localStorage.setItem('mobileCart', JSON.stringify(mobileCart));
    } catch (error) {
        console.error('장바구니 데이터 저장 오류:', error);
    }
}

// 뷰 전환 함수
function showView(viewName, categoryId = null) {
    document.querySelectorAll('.content-view').forEach(view => {
        view.classList.remove('active');
    });
    
    const targetView = document.getElementById(viewName + '-view');
    if (targetView) {
        targetView.classList.add('active');
        currentView = viewName;
    }
    
    if (categoryId !== null) {
        currentCategory = categoryId;
        updateCategoryFilter(categoryId);
    }
    
    updateCategoryActiveState(viewName, categoryId);
}

// 카테고리 필터 업데이트
function updateCategoryFilter(categoryId) {
    if (currentView === 'menu-grid') {
        const menuCards = document.querySelectorAll('.menu-card');
        menuCards.forEach(card => {
            if (categoryId === 'all') {
                card.style.display = 'block';
            } else {
                const categories = JSON.parse(card.dataset.categories || '[]');
                card.style.display = categories.includes(parseInt(categoryId)) ? 'block' : 'none';
            }
        });
    }
}

// 카테고리 아이템 활성화 상태 업데이트
function updateCategoryActiveState(viewName, categoryId) {
    document.querySelectorAll('.mobile-category-item').forEach(item => {
        item.classList.remove('active');
    });
    
    if (viewName === 'menu-grid') {
        const targetCategory = document.querySelector(`[data-category="${categoryId}"][data-view="menu-grid"]`);
        if (targetCategory) {
            targetCategory.classList.add('active');
        }
    }
}

// 메뉴 상세 보기
function showMenuDetail(menuId) {
    const storeId = window.storeId;
    
    fetch(`/menu/${storeId}/detail/${menuId}/ajax/`)
        .then(response => response.text())
        .then(html => {
            const menuDetailView = document.getElementById('menu-detail-view');
            menuDetailView.innerHTML = html;
            
            const scripts = menuDetailView.querySelectorAll('script');
            scripts.forEach(oldScript => {
                try {
                    const newScript = document.createElement('script');
                    newScript.textContent = oldScript.textContent;
                    document.head.appendChild(newScript);
                    
                    setTimeout(() => {
                        if (document.head.contains(newScript)) {
                            document.head.removeChild(newScript);
                        }
                    }, 100);
                } catch (error) {
                    console.error('스크립트 실행 오류:', error);
                }
            });
            
            showView('menu-detail');
        })
        .catch(error => {
            console.error('메뉴 상세 로드 오류:', error);
        });
}

// 메뉴 그리드로 돌아가기
function backToMenuGrid() {
    showView('menu-grid', currentCategory);
}

// 모바일 메뉴 토글
function toggleMobileMenu() {
    const overlay = document.getElementById('mobile-menu-overlay');
    const menu = document.getElementById('mobile-menu');
    
    if (overlay.classList.contains('hidden')) {
        // 메뉴 열기
        overlay.classList.remove('hidden');
        setTimeout(() => {
            menu.classList.remove('translate-x-full');
            menu.classList.add('translate-x-0');
        }, 10); // 약간의 지연으로 애니메이션 효과
    } else {
        // 메뉴 닫기
        closeMobileMenu();
    }
}

// 모바일 메뉴 닫기
function closeMobileMenu() {
    const overlay = document.getElementById('mobile-menu-overlay');
    const menu = document.getElementById('mobile-menu');
    
    menu.classList.remove('translate-x-0');
    menu.classList.add('translate-x-full');
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 300); // CSS 애니메이션 시간과 동일
}

// 장바구니 뷰 관련 함수들
function showCartView() {
    showView('cart');
}

function hideCartView() {
    showView('menu-grid', currentCategory);
}

// 결제 뷰 관련 함수들
function showPaymentView() {
    showView('payment');
}

function hidePaymentView() {
    showView('cart');
}

// 데스크톱 장바구니 시스템과 호환되는 addToCart 함수 (메뉴 상세화면용)
window.addToCart = function(cartItem) {
    // 가격 검증
    if (cartItem.totalPrice === null || cartItem.totalPrice === undefined) {
        console.error('가격 정보가 없습니다:', cartItem.totalPrice);
        alert('메뉴 가격 정보가 올바르지 않습니다.');
        return;
    }
    
    // 데스크톱 형식의 cartItem을 모바일 형식으로 변환
    const existingIndex = mobileCart.findIndex(item => 
        item.menuId === cartItem.menuId.toString() && 
        JSON.stringify(item.options || {}) === JSON.stringify(cartItem.options || {})
    );
    
    if (existingIndex >= 0) {
        // 기존 아이템 수량 증가
        mobileCart[existingIndex].quantity += cartItem.quantity;
    } else {
        // 새 아이템 추가
        mobileCart.push({
            menuId: cartItem.menuId.toString(),
            menuName: cartItem.name,
            price: cartItem.totalPrice,
            quantity: cartItem.quantity,
            options: cartItem.options || {},
            originalCartItem: cartItem // 원본 정보 보관
        });
    }
    
    updateCartDisplay();
    updateCartButton();
    saveCartToStorage();
    
    // 성공 피드백
    showToast('장바구니에 담았습니다!');
};

// 장바구니 담기 성공 피드백
function showToast(message) {
    // 기존 피드백이 있으면 제거
    const existingFeedback = document.getElementById('cart-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }
    
    // 새 피드백 생성
    const feedback = document.createElement('div');
    feedback.id = 'cart-feedback';
    feedback.className = 'fixed top-20 left-4 right-4 bg-green-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 text-center transition-opacity duration-300';
    feedback.innerHTML = `<i class="fas fa-check mr-2"></i>${message}`;
    
    document.body.appendChild(feedback);
    
    // 3초 후 제거
    setTimeout(() => {
        feedback.style.opacity = '0';
        setTimeout(() => {
            if (document.body.contains(feedback)) {
                document.body.removeChild(feedback);
            }
        }, 300);
    }, 2000);
}

// 장바구니에 메뉴 추가 (기존 모바일 전용 함수)
function addToMobileCart(menuId, menuName, price, quantity = 1) {
    const existingItem = mobileCart.find(item => item.menuId === menuId);
    
    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        mobileCart.push({
            menuId: menuId,
            menuName: menuName,
            price: price,
            quantity: quantity
        });
    }
    
    updateCartDisplay();
    updateCartButton();
    saveCartToStorage();
    
    // 토스트 메시지 표시 (메뉴 상세에서와 동일한 피드백)
    showToast('장바구니에 담았습니다!');
}

// 장바구니에서 아이템 제거
function removeFromMobileCart(menuId, index = null) {
    if (index !== null && mobileCart[index] && mobileCart[index].menuId === menuId) {
        // 특정 인덱스의 아이템 제거
        mobileCart.splice(index, 1);
    } else {
        // menuId로 첫 번째 일치하는 아이템 제거
        const itemIndex = mobileCart.findIndex(item => item.menuId === menuId);
        if (itemIndex >= 0) {
            mobileCart.splice(itemIndex, 1);
        }
    }
    updateCartDisplay();
    updateCartButton();
    saveCartToStorage();
}

// 장바구니 비우기
function clearMobileCart() {
    mobileCart = [];
    updateCartDisplay();
    updateCartButton();
    saveCartToStorage();
}

// 장바구니 표시 업데이트
function updateCartDisplay() {
    const cartItemsContainer = document.getElementById('mobile-cart-view-items');
    const emptyCartMessage = document.getElementById('mobile-cart-view-empty');
    const cartSummary = document.getElementById('mobile-cart-view-summary');
    const cartTotalElement = document.getElementById('mobile-cart-view-total');
    
    if (mobileCart.length === 0) {
        if (cartItemsContainer) cartItemsContainer.innerHTML = '';
        if (emptyCartMessage) emptyCartMessage.classList.remove('hidden');
        if (cartSummary) cartSummary.classList.add('hidden');
        cartTotal = 0;
    } else {
        if (emptyCartMessage) emptyCartMessage.classList.add('hidden');
        if (cartSummary) cartSummary.classList.remove('hidden');
        
        cartTotal = mobileCart.reduce((total, item) => total + (item.price * item.quantity), 0);
        if (cartTotalElement) cartTotalElement.textContent = `${cartTotal.toLocaleString()} sats`;
        
        if (cartItemsContainer) {
            cartItemsContainer.innerHTML = mobileCart.map((item, index) => {
                // 옵션 정보 표시 문자열 생성
                const optionsText = item.options && Object.keys(item.options).length > 0 
                    ? Object.entries(item.options).map(([key, value]) => `${key}: ${value.value}`).join(', ')
                    : '';
                
                return `
                    <div class="cart-item flex items-center justify-between p-3 border-b border-gray-100 dark:border-gray-600">
                        <div class="flex-1">
                            <h4 class="font-medium text-gray-900 dark:text-white">${item.menuName}</h4>
                            ${optionsText ? `<p class="text-xs text-blue-600 dark:text-blue-400">${optionsText}</p>` : ''}
                            <p class="text-sm text-gray-600 dark:text-gray-400">${item.price.toLocaleString()} sats</p>
                        </div>
                        <div class="flex items-center space-x-2">
                            <button onclick="changeCartItemQuantity('${item.menuId}', -1, ${index})" 
                                    class="w-8 h-8 bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 rounded-full flex items-center justify-center">
                                <i class="fas fa-minus text-xs text-gray-600 dark:text-gray-200"></i>
                            </button>
                            <span class="w-8 text-center text-gray-900 dark:text-white">${item.quantity}</span>
                            <button onclick="changeCartItemQuantity('${item.menuId}', 1, ${index})" 
                                    class="w-8 h-8 bg-blue-500 dark:bg-blue-600 hover:bg-blue-600 dark:hover:bg-blue-700 text-white rounded-full flex items-center justify-center">
                                <i class="fas fa-plus text-xs"></i>
                            </button>
                            <button onclick="removeFromMobileCart('${item.menuId}', ${index})" 
                                    class="ml-2 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }
}

// 장바구니 아이템 수량 변경
function changeCartItemQuantity(menuId, delta, index = null) {
    // index가 제공된 경우 해당 인덱스의 아이템을 직접 찾기
    let item;
    if (index !== null && mobileCart[index] && mobileCart[index].menuId === menuId) {
        item = mobileCart[index];
    } else {
        // index가 없거나 일치하지 않으면 menuId로 찾기 (첫 번째 일치하는 아이템)
        item = mobileCart.find(item => item.menuId === menuId);
    }
    
    if (item) {
        item.quantity += delta;
        if (item.quantity <= 0) {
            removeFromMobileCart(menuId, index);
        } else {
            updateCartDisplay();
            updateCartButton();
            saveCartToStorage();
        }
    }
}

// 장바구니 업데이트 함수
function updateCartButton() {
    const badge = document.getElementById('mobile-cart-badge');
    const clearBtn = document.getElementById('mobile-cart-view-clear-btn');
    
    const cartItems = mobileCart.length;
    const totalQuantity = mobileCart.reduce((total, item) => total + item.quantity, 0);
    
    if (cartItems > 0) {
        if (badge) {
            badge.textContent = totalQuantity;
            badge.classList.remove('hidden');
        }
        if (clearBtn) clearBtn.classList.remove('hidden');
    } else {
        if (badge) badge.classList.add('hidden');
        if (clearBtn) clearBtn.classList.add('hidden');
    }
}

// 주문 처리
function processOrderFromCart() {
    if (mobileCart.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // 유효하지 않은 아이템 필터링 (가격이 null이나 undefined인 경우만)
    const validCartItems = mobileCart.filter(item => item.price !== null && item.price !== undefined);
    
    if (validCartItems.length === 0) {
        alert('유효한 상품이 없습니다. 가격 정보를 확인해주세요.');
        return;
    }
    
    if (validCartItems.length !== mobileCart.length) {
        // 유효한 아이템만으로 장바구니 업데이트
        mobileCart = validCartItems;
        updateCartDisplay();
        updateCartButton();
        saveCartToStorage();
    }
    
    // 모바일 장바구니 데이터를 데스크톱 장바구니 형식으로 변환
    const convertedCartData = validCartItems.map(item => ({
        id: `mobile_${item.menuId}_${Date.now()}`, // 고유 ID 생성
        name: item.menuName,
        totalPrice: item.price,
        quantity: item.quantity,
        options: item.options || {} // 옵션 정보도 포함
    }));
    
    // 전역 cartData 설정 (데스크톱 장바구니 시스템에서 사용)
    window.cartData = convertedCartData;
    
    // localStorage에도 저장 (데스크톱 장바구니와 동기화)
    localStorage.setItem('cart', JSON.stringify(convertedCartData));
    
    // 스토어 ID 설정
    if (window.storeId) {
        window.currentStoreId = window.storeId;
    }
    
    // 결제 화면 표시
    showPaymentView();
    updatePaymentView();
}

// 결제 뷰 업데이트 함수
function updatePaymentView() {
    const totalAmount = mobileCart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const totalItems = mobileCart.reduce((sum, item) => sum + item.quantity, 0);
    
    if (totalAmount < 0 || isNaN(totalAmount)) {
        alert('결제 금액이 올바르지 않습니다.');
        return;
    }
    
    // 무료 상품인 경우 바로 결제 완료 처리
    if (totalAmount === 0) {
        showMobileFreeOrderSuccess();
        return;
    }
    
    // 총 결제 금액 업데이트
    const totalElement = document.getElementById('mobile-payment-total');
    if (totalElement) {
        totalElement.textContent = `${totalAmount.toLocaleString()} sats`;
    }
    
    // 주문 목록 업데이트
    updateMobilePaymentOrderList();
    
    // 결제 상태 초기화
    document.getElementById('mobile-payment-initial').classList.remove('hidden');
    document.getElementById('mobile-payment-loading').classList.add('hidden');
    document.getElementById('mobile-payment-invoice').classList.add('hidden');
    document.getElementById('mobile-payment-success').classList.add('hidden');
    document.getElementById('mobile-payment-cancelled').classList.add('hidden');
}

// 모바일 무료 상품 결제 완료 화면 표시
function showMobileFreeOrderSuccess() {
    // 결제 뷰 표시
    showPaymentView();
    
    // 총 결제 금액을 무료로 업데이트
    const totalElement = document.getElementById('mobile-payment-total');
    if (totalElement) {
        totalElement.innerHTML = '<i class="fas fa-gift mr-2"></i>무료';
        totalElement.classList.remove('text-blue-600', 'dark:text-blue-400');
        totalElement.classList.add('text-green-600', 'dark:text-green-400');
    }
    
    // 주문 목록 업데이트
    updateMobilePaymentOrderList();
    
    // 모든 결제 상태 숨기기
    document.getElementById('mobile-payment-initial').classList.add('hidden');
    document.getElementById('mobile-payment-loading').classList.add('hidden');
    document.getElementById('mobile-payment-invoice').classList.add('hidden');
    document.getElementById('mobile-payment-cancelled').classList.add('hidden');
    
    // 무료 주문 성공 상태 표시
    const successElement = document.getElementById('mobile-payment-success');
    if (successElement) {
        // 무료 상품용 내용으로 업데이트
        successElement.innerHTML = `
            <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-4">
                <i class="fas fa-gift text-green-600 dark:text-green-400 text-3xl mb-3"></i>
                <h4 class="text-lg font-semibold text-green-900 dark:text-green-100 mb-2">무료 상품 주문이 완료되었습니다!</h4>
                <p class="text-green-700 dark:text-green-300 text-sm">주문이 성공적으로 접수되었습니다.</p>
            </div>
            <div id="mobile-free-order-error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-3 text-red-800 dark:text-red-200 hidden">
                <i class="fas fa-exclamation-triangle text-red-600 dark:text-red-400 mr-2"></i>
                <span id="mobile-free-order-error-text"></span>
            </div>
            <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
                <div class="text-blue-600 dark:text-blue-400 text-lg font-bold" id="mobile-redirect-countdown">10</div>
                <div class="text-blue-500 dark:text-blue-400 text-sm">초 후 메뉴판으로 이동합니다</div>
            </div>
            <button onclick="goBackToMobileMenuBoard()" 
                    class="w-full bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white py-2 px-4 rounded-lg font-medium transition-colors">
                <i class="fas fa-arrow-left mr-2"></i>지금 메뉴판으로 이동
            </button>
        `;
        successElement.classList.remove('hidden');
    }
    
    // 무료 상품 주문 처리
    processMobileFreeOrder();
    
    // 자동 리다이렉트 시작
    startMobileRedirectCountdown();
}

// 모바일 무료 상품 주문 처리
function processMobileFreeOrder() {
    const storeId = currentStoreId || window.location.pathname.split('/')[2];
    
    // 모바일 장바구니 데이터를 서버 형식으로 변환
    const convertedCartData = mobileCart.map(item => ({
        menuId: item.menuId,
        id: item.menuId,
        quantity: item.quantity,
        price: item.price,
        totalPrice: item.price
    }));
    
    fetch(`/menu/${storeId}/m/cart/process-free-order/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            items: convertedCartData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 장바구니 비우기
            clearMobileCart();
            console.log('무료 상품 주문이 완료되었습니다.');
        } else {
            console.error('무료 상품 주문 처리 실패:', data.error);
            // 에러 발생 시 사용자에게 알림
            updateMobileFreeOrderError(data.error || '무료 상품 주문 처리 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        console.error('무료 상품 주문 처리 중 오류:', error);
        // 네트워크 오류 등 예외 상황 처리
        updateMobileFreeOrderError('네트워크 오류가 발생했습니다. 다시 시도해주세요.');
    });
}

// 모바일 무료 상품 주문 에러 표시
function updateMobileFreeOrderError(errorMessage) {
    const errorElement = document.getElementById('mobile-free-order-error');
    const errorTextElement = document.getElementById('mobile-free-order-error-text');
    
    if (errorElement && errorTextElement) {
        errorTextElement.textContent = errorMessage;
        errorElement.classList.remove('hidden');
    } else {
        // 에러 표시 영역이 없는 경우 알림으로 표시
        alert(errorMessage);
    }
}

// 장바구니 비우기 확인
function confirmClearCart() {
    if (confirm('장바구니를 비우시겠습니까?')) {
        clearMobileCart();
    }
}

// 모바일 결제 관련 함수들
function closeMobilePaymentView() {
    hidePaymentView();
}

function generateMobilePaymentInvoice() {
    // 모바일 장바구니가 비어있는지 확인
    if (mobileCart.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // 유효한 장바구니 아이템 필터링
    const validCartItems = mobileCart.filter(item => item.price !== null && item.price !== undefined);
    
    if (validCartItems.length === 0) {
        alert('유효한 상품이 장바구니에 없습니다.');
        return;
    }
    
    // 총 금액 계산
    const totalAmount = validCartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    if (totalAmount < 0 || isNaN(totalAmount)) {
        alert('결제 금액이 올바르지 않습니다.');
        return;
    }
    
    // UI 상태 변경
    document.getElementById('mobile-payment-initial').classList.add('hidden');
    document.getElementById('mobile-payment-loading').classList.remove('hidden');
    
    // 스토어 ID 가져오기
    const storeId = currentStoreId || window.location.pathname.split('/')[2];
    
    // 모바일 장바구니 데이터를 서버 형식으로 변환
    const convertedCartData = validCartItems.map(item => ({
        menuId: item.menuId,
        id: item.menuId,
        quantity: item.quantity,
        price: item.price,
        totalPrice: item.price
    }));
    
    // 서버에 인보이스 생성 요청
    fetch(`/menu/${storeId}/cart/create-invoice/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            cart_items: convertedCartData
        })
    })
    .then(response => {
        if (!response.ok) {
            console.error('HTTP 오류:', response.status, response.statusText);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // 인보이스 생성 성공
            window.currentPaymentHash = data.payment_hash;
            window.paymentExpiresAt = new Date(data.expires_at);
            
            // QR 코드 생성
            generateMobileQRCode(data.invoice);
            
            // 인보이스 텍스트 표시
            document.getElementById('mobile-invoice-text').value = data.invoice;
            
            // UI 상태 변경
            document.getElementById('mobile-payment-loading').classList.add('hidden');
            document.getElementById('mobile-payment-invoice').classList.remove('hidden');
            
            // 카운트다운 시작
            startMobilePaymentCountdown();
            
            // 결제 상태 확인 시작
            startMobilePaymentStatusCheck();
            
        } else {
            // 인보이스 생성 실패
            alert('인보이스 생성에 실패했습니다: ' + data.error);
            
            // UI 상태 복원
            document.getElementById('mobile-payment-loading').classList.add('hidden');
            document.getElementById('mobile-payment-initial').classList.remove('hidden');
        }
    })
    .catch(error => {
        console.error('모바일 인보이스 생성 오류:', error);
        alert('인보이스 생성 중 오류가 발생했습니다.');
        
        // UI 상태 복원
        document.getElementById('mobile-payment-loading').classList.add('hidden');
        document.getElementById('mobile-payment-initial').classList.remove('hidden');
    });
}

function openMobileLightningWallet() {
    const invoiceText = document.getElementById('mobile-invoice-text');
    if (!invoiceText || !invoiceText.value) {
        alert('인보이스가 생성되지 않았습니다.');
        return;
    }
    
    const invoice = invoiceText.value.trim();
    
    try {
        // 버튼 상태 변경
        const button = event.target.closest('button');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2 text-lg"></i>지갑 앱 열기 시도 중...';
        button.classList.remove('bg-orange-500', 'hover:bg-orange-600');
        button.classList.add('bg-green-500');
        
        // 표준 라이트닝 URL로 먼저 시도
        const lightningUrl = `lightning:${invoice}`;
        
        // 새 창으로 열기 시도 (모바일에서 더 잘 작동)
        const newWindow = window.open(lightningUrl, '_blank');
        
        // 새 창이 열리지 않으면 현재 창에서 시도
        if (!newWindow || newWindow.closed) {
            window.location.href = lightningUrl;
        }
        
        // 지갑이 열렸는지 확인하기 위한 타이머
        let walletOpened = false;
        
        // 페이지가 숨겨지면 (앱이 열리면) 지갑이 열린 것으로 간주
        const handleVisibilityChange = () => {
            if (document.hidden) {
                walletOpened = true;
                // 버튼 상태를 성공으로 변경
                button.innerHTML = '<i class="fas fa-check mr-2 text-lg"></i>지갑 앱이 열렸습니다!';
                button.classList.remove('bg-green-500');
                button.classList.add('bg-emerald-500');
                
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.classList.remove('bg-emerald-500');
                    button.classList.add('bg-orange-500', 'hover:bg-orange-600');
                }, 2000);
            }
        };
        
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        // 3초 후에도 지갑이 열리지 않았으면 fallback 실행
        setTimeout(() => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            
            if (!walletOpened) {
                // 지갑이 열리지 않았으므로 인보이스 복사로 대체
                copyMobileInvoiceText();
                
                // 버튼 상태 변경
                button.innerHTML = '<i class="fas fa-copy mr-2 text-lg"></i>인보이스가 복사되었습니다';
                button.classList.remove('bg-green-500');
                button.classList.add('bg-blue-500');
                
                // 사용자에게 안내
                alert('라이트닝 지갑을 자동으로 열 수 없어 인보이스를 복사했습니다.\n지갑 앱을 직접 열고 붙여넣어 주세요.');
                
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.classList.remove('bg-blue-500');
                    button.classList.add('bg-orange-500', 'hover:bg-orange-600');
                }, 3000);
            }
        }, 3000);
        
    } catch (error) {
        console.error('모바일 라이트닝 지갑 열기 실패:', error);
        
        // 실패 시 인보이스 복사로 대체
        copyMobileInvoiceText();
        alert('지갑 앱을 자동으로 열 수 없습니다. 인보이스가 복사되었으니 지갑 앱에서 직접 붙여넣어 주세요.');
        
        // 버튼 원상복구
        const button = event.target.closest('button');
        if (button) {
            const originalText = '<i class="fas fa-bolt mr-2 text-lg"></i>라이트닝 지갑 열어 결제하기';
            button.innerHTML = originalText;
            button.classList.remove('bg-green-500');
            button.classList.add('bg-orange-500', 'hover:bg-orange-600');
        }
    }
}

function copyMobileInvoiceText() {
    const invoiceText = document.getElementById('mobile-invoice-text');
    if (invoiceText) {
        invoiceText.select();
        invoiceText.setSelectionRange(0, 99999);
        navigator.clipboard.writeText(invoiceText.value).then(() => {
            alert('인보이스가 클립보드에 복사되었습니다.');
        }).catch(() => {
            // clipboard API가 실패하면 기존 방법 시도
            try {
                document.execCommand('copy');
                alert('인보이스가 클립보드에 복사되었습니다.');
            } catch (err) {
                alert('복사에 실패했습니다.');
            }
        });
    }
}

function cancelMobilePayment() {
    if (!confirm('정말로 결제를 취소하시겠습니까?')) {
        return;
    }
    
    // 취소 중 표시
    const cancelBtn = document.querySelector('[onclick="cancelMobilePayment()"]');
    if (cancelBtn) {
        cancelBtn.disabled = true;
        cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> 취소 중...';
    }
    
    // 현재 결제 해시가 있는 경우에만 서버에 취소 요청
    if (window.currentPaymentHash) {
        const storeId = currentStoreId || window.location.pathname.split('/')[2];
        
        fetch(`/menu/${storeId}/m/cart/cancel-invoice/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                payment_hash: window.currentPaymentHash
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 서버 취소 성공
                handleMobileCancelSuccess();
            } else {
                // 서버 취소 실패 또는 이미 결제 완료된 경우
                if (data.order_number) {
                    // 이미 결제가 완료된 경우
                    alert(data.error || '결제가 완료되었습니다.');
                    
                    // 결제 상태 확인 중지
                    if (window.paymentCheckInterval) {
                        clearInterval(window.paymentCheckInterval);
                        window.paymentCheckInterval = null;
                    }
                    
                    // 성공 화면으로 전환
                    document.getElementById('mobile-payment-invoice').classList.add('hidden');
                    document.getElementById('mobile-payment-success').classList.remove('hidden');
                    
                    // 장바구니 비우기
                    clearMobileCart();
                    
                    // 자동 리다이렉트 시작
                    startMobileRedirectCountdown();
                    
                } else {
                    // 일반적인 취소 실패
                    alert('취소 중 오류가 발생했습니다: ' + (data.error || '알 수 없는 오류'));
                    
                    // 취소 버튼 복원
                    if (cancelBtn) {
                        cancelBtn.disabled = false;
                        cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
                    }
                }
            }
        })
        .catch(error => {
            console.error('취소 요청 중 오류:', error);
            alert('취소 요청 중 오류가 발생했습니다.');
            
            // 취소 버튼 복원
            if (cancelBtn) {
                cancelBtn.disabled = false;
                cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
            }
        });
    } else {
        // 결제 해시가 없는 경우 클라이언트 측에서만 처리
        handleMobileCancelSuccess();
    }
}

// 모바일 취소 성공 처리 공통 함수
function handleMobileCancelSuccess() {
    // 결제 상태 확인 중지
    if (window.paymentCheckInterval) {
        clearInterval(window.paymentCheckInterval);
        window.paymentCheckInterval = null;
    }
    
    // 카운트다운 중지
    if (window.paymentCountdownInterval) {
        clearInterval(window.paymentCountdownInterval);
        window.paymentCountdownInterval = null;
    }
    
    // UI 상태 변경
    document.getElementById('mobile-payment-invoice').classList.add('hidden');
    document.getElementById('mobile-payment-cancelled').classList.remove('hidden');
    
    // 결제 관련 변수 초기화
    window.currentPaymentHash = null;
    window.paymentExpiresAt = null;
    
    // 🔄 페이지 새로고침으로 완전 초기화
    setTimeout(() => {
        location.reload();
    }, 1500);
}

function goBackToMobileMenuBoard() {
    // 결제 완료 후 모바일 장바구니 비우기
    clearMobileCart();
    showView('menu-grid', currentCategory);
}

// 전역 함수들 노출
window.showView = showView;
window.showMenuDetail = showMenuDetail;
window.backToMenuGrid = backToMenuGrid;
window.toggleMobileMenu = toggleMobileMenu;
window.closeMobileMenu = closeMobileMenu;
window.showCartView = showCartView;
window.hideCartView = hideCartView;
window.showPaymentView = showPaymentView;
window.hidePaymentView = hidePaymentView;
window.updatePaymentView = updatePaymentView;
window.addToMobileCart = addToMobileCart;
window.removeFromMobileCart = removeFromMobileCart;
window.clearMobileCart = clearMobileCart;
window.changeCartItemQuantity = changeCartItemQuantity;
window.processOrderFromCart = processOrderFromCart;
window.confirmClearCart = confirmClearCart;
window.clearMobileCartAfterPayment = clearMobileCartAfterPayment;
// showMobilePaymentModal 함수 제거됨 - updatePaymentView 사용
window.closeMobilePaymentView = closeMobilePaymentView;
window.generateMobilePaymentInvoice = generateMobilePaymentInvoice;
window.openMobileLightningWallet = openMobileLightningWallet;
window.copyMobileInvoiceText = copyMobileInvoiceText;
window.cancelMobilePayment = cancelMobilePayment;
window.goBackToMobileMenuBoard = goBackToMobileMenuBoard;

// 결제 완료 후 장바구니 비우기 (데스크톱 시스템과 동기화)
function clearMobileCartAfterPayment() {
    clearMobileCart();
    // localStorage에서도 제거
    localStorage.removeItem('cart');
}

// 데스크톱 장바구니 시스템과 동기화
function syncWithDesktopCart() {
    // localStorage에서 장바구니 변경 사항 감지
    window.addEventListener('storage', function(e) {
        if (e.key === 'cart') {
            // 데스크톱에서 장바구니가 비워졌으면 모바일도 비우기
            if (!e.newValue || e.newValue === '[]') {
                clearMobileCart();
            }
        }
    });
}

// 장바구니 데이터 정리 (유효하지 않은 아이템 제거)
function cleanupMobileCart() {
    const originalLength = mobileCart.length;
    mobileCart = mobileCart.filter(item => item.price !== null && item.price !== undefined);
    
    if (mobileCart.length !== originalLength) {
        updateCartDisplay();
        updateCartButton();
        saveCartToStorage();
    }
}

// DOM 로드 완료 시 이벤트 바인딩
document.addEventListener('DOMContentLoaded', function() {
    // localStorage에서 장바구니 데이터 복원
    loadCartFromStorage();
    
    // 장바구니 데이터 정리
    cleanupMobileCart();
    
    document.querySelectorAll('.mobile-category-item').forEach(item => {
        item.addEventListener('click', function() {
            const viewType = this.dataset.view;
            const categoryId = this.dataset.category;
            
            if (viewType === 'menu-grid') {
                showView('menu-grid', categoryId);
            } else {
                showView(viewType);
            }
            
            closeMobileMenu();
        });
    });
    
    showView('menu-grid', 'all');
    
    // 초기 장바구니 버튼 상태 설정
    updateCartButton();
    
    // 데스크톱 장바구니와 동기화 설정
    syncWithDesktopCart();
});

// 모바일 QR 코드 생성
function generateMobileQRCode(invoice) {
    const container = document.getElementById('mobile-qr-code-container');
    if (!container) return;
    
    // QRious 라이브러리 사용
    if (typeof QRious !== 'undefined') {
        try {
            // 기존 내용 지우기
            container.innerHTML = '';
            
            // 캔버스 생성
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);
            
            // QRious 인스턴스 생성
            const qr = new QRious({
                element: canvas,
                value: invoice,
                size: 256,
                foreground: '#000000',
                background: '#ffffff',
                level: 'M'
            });
        } catch (error) {
            // fallback으로 API 사용
            generateMobileQRCodeWithAPI(invoice, container);
        }
    } else {
        // QR 코드 API 사용 (fallback)
        generateMobileQRCodeWithAPI(invoice, container);
    }
}

// API를 사용한 모바일 QR 코드 생성
function generateMobileQRCodeWithAPI(invoice, container) {
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(invoice)}`;
    container.innerHTML = `<img src="${qrUrl}" alt="QR Code" class="max-w-full h-auto border rounded">`;
}

// 모바일 카운트다운 시작
function startMobilePaymentCountdown() {
    if (!window.paymentExpiresAt) return;
    
    window.paymentCountdownInterval = setInterval(() => {
        const now = new Date();
        const timeLeft = window.paymentExpiresAt - now;
        
        if (timeLeft <= 0) {
            // 시간 만료
            clearInterval(window.paymentCountdownInterval);
            document.getElementById('mobile-countdown-timer').textContent = '00:00';
            
            // 결제 상태 확인 중지
            if (window.paymentCheckInterval) {
                clearInterval(window.paymentCheckInterval);
                window.paymentCheckInterval = null;
            }
            
            alert('인보이스가 만료되었습니다. 다시 시도해주세요.');
            closeMobilePaymentView();
            return;
        }
        
        // 시간 포맷팅
        const minutes = Math.floor(timeLeft / 60000);
        const seconds = Math.floor((timeLeft % 60000) / 1000);
        const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        document.getElementById('mobile-countdown-timer').textContent = timeString;
    }, 1000);
}

// 모바일 결제 상태 확인 시작
function startMobilePaymentStatusCheck() {
    if (!window.currentPaymentHash) return;
    
    const storeId = currentStoreId || window.location.pathname.split('/')[2];
    
    window.paymentCheckInterval = setInterval(() => {
        fetch(`/menu/${storeId}/cart/check-payment/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                payment_hash: window.currentPaymentHash
            })
        })
        .then(response => {
            if (!response.ok) {
                console.error('HTTP 오류:', response.status, response.statusText);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                
                if (data.status === 'paid') {
                    // 결제 완료
                    clearInterval(window.paymentCheckInterval);
                    clearInterval(window.paymentCountdownInterval);
                    
                    // UI 상태 변경
                    document.getElementById('mobile-payment-invoice').classList.add('hidden');
                    document.getElementById('mobile-payment-success').classList.remove('hidden');
                    
                    // 장바구니 비우기
                    clearMobileCart();
                    
                    // 10초 후 메뉴판으로 자동 이동
                    startMobileRedirectCountdown();
                    
                } else if (data.status === 'expired') {
                    // 인보이스 만료
                    clearInterval(window.paymentCheckInterval);
                    clearInterval(window.paymentCountdownInterval);
                    
                    alert('인보이스가 만료되었습니다.');
                    closeMobilePaymentView();
                }
                // pending인 경우 계속 확인
            } else {
                console.error('모바일 결제 상태 확인 오류:', data.error);
            }
        })
        .catch(error => {
            console.error('모바일 결제 상태 확인 중 오류:', error);
        });
    }, 3000); // 3초마다 확인
}

// 모바일 리다이렉트 카운트다운
function startMobileRedirectCountdown() {
    let seconds = 10;
    const countdownElement = document.getElementById('mobile-redirect-countdown');
    
    if (!countdownElement) return;
    
    const interval = setInterval(() => {
        countdownElement.textContent = seconds;
        seconds--;
        
        if (seconds < 0) {
            clearInterval(interval);
            goBackToMobileMenuBoard();
        }
    }, 1000);
}

// CSRF 토큰 가져오기
function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    if (token) {
        return token.value;
    }
    
    // 쿠키에서 CSRF 토큰 찾기
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
    return cookieValue;
}

// 모바일 결제 주문 목록 업데이트
function updateMobilePaymentOrderList() {
    const orderListContainer = document.getElementById('mobile-payment-order-list');
    if (!orderListContainer) return;
    
    orderListContainer.innerHTML = mobileCart.map(item => `
        <div class="flex justify-between items-center py-2 border-b border-gray-200 last:border-b-0">
            <div class="flex-1">
                <div class="font-medium text-sm">${item.menuName}</div>
                <div class="text-xs text-gray-600">${formatNumber(item.price)} sats × ${item.quantity}</div>
            </div>
            <div class="font-bold text-blue-600">${formatNumber(item.price * item.quantity)} sats</div>
        </div>
    `).join('');
} 