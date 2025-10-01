// 모바일 메뉴 상세 페이지 JavaScript

// 전역 변수
let currentQuantity = 1;
let basePrice = 0;
let mobileFeedbackTimeout = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeMenuDetail();
    loadCartFromStorage();
    updateCartBadge();
});

// 메뉴 상세 초기화
function initializeMenuDetail() {
    // 메뉴 가격 설정
    basePrice = window.menuPrice || 0;
    
    // 수량 표시 업데이트
    updateQuantityDisplay();
    updateTotalPrice();
}

// 수량 업데이트
function updateQuantity(change) {
    const newQuantity = currentQuantity + change;
    
    if (newQuantity >= 1 && newQuantity <= 99) {
        currentQuantity = newQuantity;
        updateQuantityDisplay();
        updateTotalPrice();
    }
}

// 수량 표시 업데이트
function updateQuantityDisplay() {
    const quantityDisplay = document.getElementById('quantity-display');
    if (quantityDisplay) {
        quantityDisplay.textContent = currentQuantity;
    }
}

// 총 가격 업데이트
function updateTotalPrice() {
    const totalPrice = basePrice * currentQuantity;
    const totalPriceElement = document.getElementById('total-price');
    
    if (totalPriceElement) {
        totalPriceElement.textContent = `${totalPrice.toLocaleString()} sats`;
    }
}

// 모바일 장바구니에 추가
function addToMobileCart() {
    if (!window.menuId || !window.menuName || !basePrice) {
        alert('메뉴 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.');
        return;
    }
    
    // 선택된 옵션 수집
    const selectedOptions = collectSelectedOptions();
    
    // 장바구니 아이템 생성
    const cartItem = {
        id: window.menuId,
        name: window.menuName,
        price: basePrice,
        quantity: currentQuantity,
        totalPrice: basePrice * currentQuantity,
        options: selectedOptions,
        timestamp: Date.now()
    };
    
    // 로컬 스토리지에서 장바구니 가져오기
    let cart = getCartFromStorage();
    
    // 같은 메뉴와 옵션 조합이 있는지 확인
    const existingItemIndex = cart.findIndex(item => 
        item.id === cartItem.id && 
        JSON.stringify(item.options) === JSON.stringify(cartItem.options)
    );
    
    if (existingItemIndex > -1) {
        // 기존 아이템의 수량 증가
        cart[existingItemIndex].quantity += cartItem.quantity;
        cart[existingItemIndex].totalPrice = cart[existingItemIndex].price * cart[existingItemIndex].quantity;
    } else {
        // 새 아이템 추가
        cart.push(cartItem);
    }
    
    // 장바구니 저장
    saveCartToStorage(cart);
    
    // UI 업데이트
    updateCartBadge();
    
    // 성공 메시지
    showInlineFeedback(`${window.menuName}이(가) 장바구니에 추가되었습니다.`, 'success');
    
    // 수량 초기화
    currentQuantity = 1;
    updateQuantityDisplay();
    updateTotalPrice();
}

// 선택된 옵션 수집
function collectSelectedOptions() {
    const options = {};
    const optionGroups = document.querySelectorAll('.option-group');
    
    optionGroups.forEach(group => {
        const optionId = group.dataset.optionId;
        const optionName = group.querySelector('h4').textContent;
        const selectedInputs = group.querySelectorAll('input:checked');
        
        if (selectedInputs.length > 0) {
            const selectedValues = Array.from(selectedInputs).map(input => input.value);
            options[optionName] = selectedValues;
        }
    });
    
    return options;
}

// 모바일 장바구니 토글
function toggleMobileCart() {
    const cartSidebar = document.getElementById('mobile-cart-sidebar');
    const overlay = document.getElementById('mobile-cart-overlay');
    
    if (cartSidebar && overlay) {
        const isOpen = !cartSidebar.classList.contains('-translate-x-full');
        
        if (isOpen) {
            closeMobileCart();
        } else {
            openMobileCart();
        }
    }
}

// 모바일 장바구니 열기
function openMobileCart() {
    const cartSidebar = document.getElementById('mobile-cart-sidebar');
    const overlay = document.getElementById('mobile-cart-overlay');
    
    if (cartSidebar && overlay) {
        cartSidebar.classList.remove('-translate-y-full');
        cartSidebar.classList.add('translate-y-0');
        overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // 장바구니 내용 업데이트
        renderMobileCartItems();
    }
}

// 모바일 장바구니 닫기
function closeMobileCart() {
    const cartSidebar = document.getElementById('mobile-cart-sidebar');
    const overlay = document.getElementById('mobile-cart-overlay');
    
    if (cartSidebar && overlay) {
        cartSidebar.classList.remove('translate-y-0');
        cartSidebar.classList.add('-translate-y-full');
        overlay.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

// 모바일 장바구니 아이템 렌더링
function renderMobileCartItems() {
    const cartItemsContainer = document.getElementById('mobile-cart-items');
    const emptyCartMessage = document.getElementById('mobile-empty-cart');
    const cartFooter = document.getElementById('mobile-cart-footer');
    const clearCartBtn = document.getElementById('mobile-clear-cart-btn');
    
    if (!cartItemsContainer) return;
    
    const cart = getCartFromStorage();
    
    if (cart.length === 0) {
        cartItemsContainer.innerHTML = '';
        if (emptyCartMessage) emptyCartMessage.classList.remove('hidden');
        if (cartFooter) cartFooter.classList.add('hidden');
        if (clearCartBtn) clearCartBtn.classList.add('hidden');
        return;
    }
    
    if (emptyCartMessage) emptyCartMessage.classList.add('hidden');
    if (cartFooter) cartFooter.classList.remove('hidden');
    if (clearCartBtn) clearCartBtn.classList.remove('hidden');
    
    let cartHTML = '';
    let totalAmount = 0;
    
    cart.forEach((item, index) => {
        totalAmount += item.totalPrice;
        
        // 옵션 문자열 생성
        let optionsText = '';
        if (item.options && Object.keys(item.options).length > 0) {
            const optionStrings = Object.entries(item.options).map(([key, values]) => {
                return `${key}: ${Array.isArray(values) ? values.join(', ') : values}`;
            });
            optionsText = optionStrings.join(' | ');
        }
        
        cartHTML += `
            <div class="cart-item bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div class="flex justify-between items-start mb-2">
                    <h4 class="font-medium text-gray-900 dark:text-white">${item.name}</h4>
                    <button onclick="removeFromCart(${index})" class="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 ml-2">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                ${optionsText ? `<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">${optionsText}</p>` : ''}
                
                <div class="flex justify-between items-center">
                    <div class="flex items-center space-x-2">
                        <button onclick="updateCartItemQuantity(${index}, -1)" 
                                class="w-8 h-8 bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 rounded-full flex items-center justify-center text-sm">
                            <i class="fas fa-minus text-gray-600 dark:text-gray-200"></i>
                        </button>
                        <span class="w-8 text-center font-medium text-gray-900 dark:text-white">${item.quantity}</span>
                        <button onclick="updateCartItemQuantity(${index}, 1)" 
                                class="w-8 h-8 bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 rounded-full flex items-center justify-center text-sm">
                            <i class="fas fa-plus text-gray-600 dark:text-gray-200"></i>
                        </button>
                    </div>
                    <span class="font-semibold text-gray-900 dark:text-white">${item.totalPrice.toLocaleString()} sats</span>
                </div>
            </div>
        `;
    });
    
    cartItemsContainer.innerHTML = cartHTML;
    
    // 총 금액 업데이트
    const cartTotalElement = document.getElementById('mobile-cart-total');
    if (cartTotalElement) {
        cartTotalElement.textContent = `${totalAmount.toLocaleString()} sats`;
    }
}

// 장바구니에서 아이템 제거
function removeFromCart(index) {
    let cart = getCartFromStorage();
    if (index >= 0 && index < cart.length) {
        cart.splice(index, 1);
        saveCartToStorage(cart);
        renderMobileCartItems();
        updateCartBadge();
        
        if (cart.length === 0) {
            closeMobileCart();
        }
    }
}

// 장바구니 아이템 수량 업데이트
function updateCartItemQuantity(index, change) {
    let cart = getCartFromStorage();
    if (index >= 0 && index < cart.length) {
        const newQuantity = cart[index].quantity + change;
        
        if (newQuantity <= 0) {
            removeFromCart(index);
        } else if (newQuantity <= 99) {
            cart[index].quantity = newQuantity;
            cart[index].totalPrice = cart[index].price * newQuantity;
            saveCartToStorage(cart);
            renderMobileCartItems();
            updateCartBadge();
        }
    }
}

// 장바구니 뱃지 업데이트
function updateCartBadge() {
    const cartBadge = document.getElementById('mobile-cart-badge');
    if (!cartBadge) return;
    
    const cart = getCartFromStorage();
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    
    if (totalItems > 0) {
        cartBadge.textContent = totalItems > 99 ? '99+' : totalItems;
        cartBadge.classList.remove('hidden');
    } else {
        cartBadge.classList.add('hidden');
    }
}

// 로컬 스토리지에서 장바구니 가져오기
function getCartFromStorage() {
    try {
        const cartData = localStorage.getItem(`cart_${window.storeId}`);
        return cartData ? JSON.parse(cartData) : [];
    } catch (error) {
        console.error('장바구니 데이터 로드 실패:', error);
        return [];
    }
}

// 로컬 스토리지에 장바구니 저장
function saveCartToStorage(cart) {
    try {
        localStorage.setItem(`cart_${window.storeId}`, JSON.stringify(cart));
    } catch (error) {
        console.error('장바구니 데이터 저장 실패:', error);
    }
}

// 로컬 스토리지에서 장바구니 로드
function loadCartFromStorage() {
    // 필요한 경우 여기서 추가 초기화 작업 수행
}

// 장바구니 비우기 확인
function confirmClearCart() {
    if (confirm('장바구니의 모든 상품을 삭제하시겠습니까?')) {
        clearCart();
    }
}

// 장바구니 비우기
function clearCart() {
    localStorage.removeItem(`cart_${window.storeId}`);
    renderMobileCartItems();
    updateCartBadge();
    closeMobileCart();
    showInlineFeedback('장바구니가 비워졌습니다.', 'info');
}

// 인라인 안내 메시지 출력
function showInlineFeedback(message, variant = 'info') {
    const wrapper = document.getElementById('mobile-feedback');
    const box = document.getElementById('mobile-feedback-box');

    if (!wrapper || !box) {
        return;
    }

    const baseClasses = 'px-4 py-3 rounded-lg text-sm font-medium border transition-opacity duration-300';
    const variants = {
        success: 'border-green-300 bg-green-50 text-green-800 dark:border-green-600 dark:bg-green-900/40 dark:text-green-200',
        info: 'border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-500 dark:bg-blue-900/40 dark:text-blue-100',
        warning: 'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-500 dark:bg-amber-900/40 dark:text-amber-100',
        error: 'border-red-300 bg-red-50 text-red-800 dark:border-red-500 dark:bg-red-900/40 dark:text-red-100'
    };

    box.className = `${baseClasses} ${variants[variant] || variants.info}`;
    box.textContent = message;

    wrapper.classList.remove('hidden');
    box.style.opacity = '1';

    if (mobileFeedbackTimeout) {
        clearTimeout(mobileFeedbackTimeout);
    }

    mobileFeedbackTimeout = setTimeout(() => {
        box.style.opacity = '0';
        setTimeout(() => {
            wrapper.classList.add('hidden');
            box.style.opacity = '1';
        }, 300);
    }, 3000);
}

// 결제 진행
function proceedToPayment() {
    const cart = getCartFromStorage();
    
    if (cart.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // 모바일 장바구니 페이지로 이동
    window.location.href = `/menu/${window.storeId}/m/cart/`;
} 
