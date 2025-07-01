/**
 * 모바일 장바구니 관리 시스템
 * 바텀 시트 형태의 모바일 최적화된 장바구니 UI 관리
 */

class MobileCartManager {
    constructor() {
        this.cart = {};
        this.isOpen = false;
        this.isLoading = false;
        this.touchStartY = 0;
        this.touchCurrentY = 0;
        this.isDragging = false;
        this.startHeight = 0;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateMobileCartDisplay();
        console.log('MobileCartManager 초기화 완료');
    }

    bindEvents() {
        // 모바일 장바구니 토글 버튼
        const cartToggleBtn = document.getElementById('mobile-cart-toggle');
        if (cartToggleBtn) {
            cartToggleBtn.addEventListener('click', () => this.toggleCart());
        }

        // 바텀 시트 닫기 버튼
        const closeBtn = document.querySelector('#mobile-cart-bottom-sheet .close-cart');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeCart());
        }

        // 오버레이 클릭으로 닫기
        const overlay = document.getElementById('mobile-cart-overlay');
        if (overlay) {
            overlay.addEventListener('click', () => this.closeCart());
        }

        // 드래그 핸들 터치 이벤트
        const handle = document.querySelector('.mobile-cart-handle');
        if (handle) {
            handle.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
            handle.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
            handle.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
        }

        // ESC 키로 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeCart();
            }
        });

        // 전체 삭제 버튼
        const clearAllBtn = document.querySelector('.mobile-clear-all-btn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAllItems());
        }
    }

    // 터치 이벤트 핸들러
    handleTouchStart(e) {
        this.touchStartY = e.touches[0].clientY;
        this.isDragging = true;
        const bottomSheet = document.getElementById('mobile-cart-bottom-sheet');
        this.startHeight = bottomSheet.offsetHeight;
    }

    handleTouchMove(e) {
        if (!this.isDragging) return;
        
        e.preventDefault();
        this.touchCurrentY = e.touches[0].clientY;
        const deltaY = this.touchCurrentY - this.touchStartY;
        
        if (deltaY > 0) { // 아래로 드래그
            const bottomSheet = document.getElementById('mobile-cart-bottom-sheet');
            const newHeight = Math.max(200, this.startHeight - deltaY);
            bottomSheet.style.height = `${newHeight}px`;
            
            // 임계값을 넘으면 투명도 조절
            if (deltaY > 100) {
                const opacity = Math.max(0.3, 1 - (deltaY - 100) / 200);
                bottomSheet.style.opacity = opacity;
            }
        }
    }

    handleTouchEnd(e) {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        const deltaY = this.touchCurrentY - this.touchStartY;
        const bottomSheet = document.getElementById('mobile-cart-bottom-sheet');
        
        if (deltaY > 150) { // 충분히 아래로 드래그하면 닫기
            this.closeCart();
        } else {
            // 원래 상태로 복구
            bottomSheet.style.height = '';
            bottomSheet.style.opacity = '';
        }
    }

    // 장바구니 열기/닫기
    toggleCart() {
        if (this.isOpen) {
            this.closeCart();
        } else {
            this.openCart();
        }
    }

    openCart() {
        const overlay = document.getElementById('mobile-cart-overlay');
        const bottomSheet = document.getElementById('mobile-cart-bottom-sheet');
        
        if (overlay && bottomSheet) {
            overlay.classList.remove('hidden');
            bottomSheet.classList.remove('translate-y-full');
            document.body.style.overflow = 'hidden';
            this.isOpen = true;
        }
    }

    closeCart() {
        const overlay = document.getElementById('mobile-cart-overlay');
        const bottomSheet = document.getElementById('mobile-cart-bottom-sheet');
        
        if (overlay && bottomSheet) {
            bottomSheet.classList.add('translate-y-full');
            setTimeout(() => {
                overlay.classList.add('hidden');
                document.body.style.overflow = '';
                // 스타일 초기화
                bottomSheet.style.height = '';
                bottomSheet.style.opacity = '';
            }, 300);
            this.isOpen = false;
        }
    }

    // 장바구니에 아이템 추가
    addToCart(menuId, name, price, options = {}) {
        const key = this.getCartKey(menuId, options);
        
        if (this.cart[key]) {
            this.cart[key].quantity += 1;
        } else {
            this.cart[key] = {
                menuId: menuId,
                name: name,
                price: price,
                quantity: 1,
                options: options
            };
        }
        
        this.updateMobileCartDisplay();
        this.showAddToCartFeedback(name);
        this.saveCartToStorage();
    }

    // 장바구니에서 아이템 제거
    removeFromCart(key) {
        if (confirm('이 상품을 장바구니에서 제거하시겠습니까?')) {
            delete this.cart[key];
            this.updateMobileCartDisplay();
            this.saveCartToStorage();
        }
    }

    // 수량 변경
    updateQuantity(key, change) {
        if (this.cart[key]) {
            this.cart[key].quantity += change;
            if (this.cart[key].quantity <= 0) {
                this.removeFromCart(key);
            } else {
                this.updateMobileCartDisplay();
                this.saveCartToStorage();
            }
        }
    }

    // 전체 삭제
    clearAllItems() {
        if (Object.keys(this.cart).length === 0) return;
        
        if (confirm('장바구니를 비우시겠습니까?')) {
            this.cart = {};
            this.updateMobileCartDisplay();
            this.saveCartToStorage();
        }
    }

    // 장바구니 키 생성
    getCartKey(menuId, options) {
        const optionsStr = Object.keys(options).sort().map(key => `${key}:${options[key]}`).join('|');
        return `${menuId}_${optionsStr}`;
    }

    // 모바일 장바구니 디스플레이 업데이트
    updateMobileCartDisplay() {
        this.updateCartBadge();
        this.updateCartItems();
        this.updateCartSummary();
    }

    // 장바구니 배지 업데이트
    updateCartBadge() {
        const badge = document.getElementById('mobile-cart-badge');
        const totalItems = Object.values(this.cart).reduce((sum, item) => sum + item.quantity, 0);
        
        if (badge) {
            if (totalItems > 0) {
                badge.textContent = totalItems;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    // 장바구니 아이템 목록 업데이트
    updateCartItems() {
        const container = document.getElementById('mobile-cart-items');
        if (!container) return;

        container.innerHTML = '';

        if (Object.keys(this.cart).length === 0) {
            container.innerHTML = `
                <div class="empty-cart-state text-center py-8">
                    <div class="text-6xl mb-4">🛒</div>
                    <p class="text-gray-500">장바구니가 비어있습니다</p>
                </div>
            `;
            return;
        }

        Object.entries(this.cart).forEach(([key, item]) => {
            const itemElement = this.createMobileCartItemElement(key, item);
            container.appendChild(itemElement);
        });
    }

    // 모바일 장바구니 아이템 요소 생성
    createMobileCartItemElement(key, item) {
        const div = document.createElement('div');
        div.className = 'mobile-cart-item bg-white rounded-lg p-3 shadow-sm';
        
        const optionsText = Object.keys(item.options).length > 0 
            ? Object.entries(item.options).map(([k, v]) => `${k}: ${v}`).join(', ')
            : '';

        div.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0">
                    <h4 class="font-medium text-gray-900 truncate">${item.name}</h4>
                    ${optionsText ? `<p class="text-sm text-gray-500 truncate">${optionsText}</p>` : ''}
                    <p class="text-lg font-bold text-blue-600">${item.price.toLocaleString()}원</p>
                </div>
                <div class="flex items-center space-x-2 ml-4">
                    <button onclick="window.mobileCartManager.updateQuantity('${key}', -1)" 
                            class="mobile-cart-button quantity-button bg-gray-100 text-gray-600 rounded-full w-8 h-8 flex items-center justify-center"
                            ${item.quantity <= 1 ? 'disabled' : ''}>
                        <i class="fas fa-minus text-xs"></i>
                    </button>
                    <span class="mx-2 min-w-[2rem] text-center font-semibold">${item.quantity}</span>
                    <button onclick="window.mobileCartManager.updateQuantity('${key}', 1)" 
                            class="mobile-cart-button quantity-button bg-blue-500 text-white rounded-full w-8 h-8 flex items-center justify-center">
                        <i class="fas fa-plus text-xs"></i>
                    </button>
                    <button onclick="window.mobileCartManager.removeFromCart('${key}')" 
                            class="mobile-cart-button delete-button ml-2 rounded-lg px-2 py-1">
                        <i class="fas fa-trash text-sm"></i>
                    </button>
                </div>
            </div>
        `;
        
        return div;
    }

    // 장바구니 요약 업데이트
    updateCartSummary() {
        const summaryContainer = document.getElementById('mobile-cart-summary');
        const clearAllBtn = document.querySelector('.mobile-clear-all-btn');
        
        if (!summaryContainer) return;

        const totalItems = Object.values(this.cart).reduce((sum, item) => sum + item.quantity, 0);
        const totalPrice = Object.values(this.cart).reduce((sum, item) => sum + (item.price * item.quantity), 0);

        // 전체 삭제 버튼 표시/숨김
        if (clearAllBtn) {
            if (totalItems > 0) {
                clearAllBtn.classList.remove('hidden');
            } else {
                clearAllBtn.classList.add('hidden');
            }
        }

        if (totalItems === 0) {
            summaryContainer.innerHTML = '';
            return;
        }

        summaryContainer.innerHTML = `
            <div class="cart-summary p-4 mb-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-gray-600">총 수량</span>
                    <span class="font-semibold">${totalItems}개</span>
                </div>
                <div class="flex justify-between items-center text-lg font-bold">
                    <span>총 금액</span>
                    <span class="text-blue-600">${totalPrice.toLocaleString()}원</span>
                </div>
            </div>
            <button onclick="window.mobileCartManager.proceedToCheckout()" 
                    class="checkout-button w-full bg-blue-500 text-white py-4 rounded-lg font-semibold text-lg">
                <i class="fas fa-credit-card mr-2"></i>
                결제하기
            </button>
        `;
    }

    // 장바구니 추가 피드백
    showAddToCartFeedback(itemName) {
        // 간단한 토스트 메시지
        const toast = document.createElement('div');
        toast.className = 'fixed top-20 left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        toast.textContent = `${itemName}이(가) 장바구니에 추가되었습니다`;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translate(-50%, -20px)';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 2000);
    }

    // 결제 진행
    proceedToCheckout() {
        if (Object.keys(this.cart).length === 0) {
            alert('장바구니가 비어있습니다.');
            return;
        }

        this.setLoading(true);
        
        // 결제 데이터 준비
        const orderData = {
            items: Object.values(this.cart),
            totalAmount: Object.values(this.cart).reduce((sum, item) => sum + (item.price * item.quantity), 0),
            timestamp: new Date().toISOString()
        };

        // 실제 결제 처리 로직 호출
        if (typeof window.processCheckout === 'function') {
            window.processCheckout(orderData);
        } else {
            console.log('결제 처리:', orderData);
            alert('결제 기능이 준비 중입니다.');
        }
        
        this.setLoading(false);
    }

    // 로딩 상태 설정
    setLoading(loading) {
        this.isLoading = loading;
        const checkoutBtn = document.querySelector('.checkout-button');
        
        if (checkoutBtn) {
            if (loading) {
                checkoutBtn.classList.add('loading');
                checkoutBtn.disabled = true;
            } else {
                checkoutBtn.classList.remove('loading');
                checkoutBtn.disabled = false;
            }
        }
    }

    // 로컬 스토리지에 장바구니 저장
    saveCartToStorage() {
        try {
            localStorage.setItem('mobileCart', JSON.stringify(this.cart));
        } catch (error) {
            console.warn('장바구니 저장 실패:', error);
        }
    }

    // 로컬 스토리지에서 장바구니 로드
    loadCartFromStorage() {
        try {
            const savedCart = localStorage.getItem('mobileCart');
            if (savedCart) {
                this.cart = JSON.parse(savedCart);
                this.updateMobileCartDisplay();
            }
        } catch (error) {
            console.warn('장바구니 로드 실패:', error);
            this.cart = {};
        }
    }

    // 장바구니 동기화 (데스크톱 버전과)
    syncWithDesktopCart(desktopCart) {
        if (desktopCart && typeof desktopCart === 'object') {
            this.cart = { ...desktopCart };
            this.updateMobileCartDisplay();
            this.saveCartToStorage();
        }
    }

    // 외부에서 호출할 수 있는 메서드들
    getCart() {
        return this.cart;
    }

    getCartCount() {
        return Object.values(this.cart).reduce((sum, item) => sum + item.quantity, 0);
    }

    getTotalPrice() {
        return Object.values(this.cart).reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }
}

// 전역 함수들 (HTML에서 직접 호출용)
function addToMobileCart(menuId, name, price, options = {}) {
    if (window.mobileCartManager) {
        window.mobileCartManager.addToCart(menuId, name, price, options);
    }
}

function toggleMobileCart() {
    if (window.mobileCartManager) {
        window.mobileCartManager.toggleCart();
    }
}

function updateMobileCartFromDesktop(cart) {
    if (window.mobileCartManager) {
        window.mobileCartManager.syncWithDesktopCart(cart);
    }
}

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 모바일 장바구니 요소가 존재하는지 확인
    const mobileCartElement = document.getElementById('mobile-cart-bottom-sheet');
    
    if (mobileCartElement) {
        // 약간의 지연을 두고 초기화 (다른 스크립트 로드 완료 대기)
        setTimeout(() => {
            try {
                window.mobileCartManager = new MobileCartManager();
                window.mobileCartManager.loadCartFromStorage();
                console.log('모바일 장바구니 시스템 초기화 완료');
            } catch (error) {
                console.error('모바일 장바구니 초기화 실패:', error);
            }
        }, 100);
    }
});

// 화면 크기 변경 감지
window.addEventListener('resize', function() {
    if (window.mobileCartManager && window.mobileCartManager.isOpen) {
        // 데스크톱으로 전환되면 모바일 장바구니 닫기
        if (window.innerWidth >= 768) {
            window.mobileCartManager.closeCart();
        }
    }
});

// 페이지 언로드 시 장바구니 저장
window.addEventListener('beforeunload', function() {
    if (window.mobileCartManager) {
        window.mobileCartManager.saveCartToStorage();
    }
}); 