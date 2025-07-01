/**
 * 모바일 메뉴판 전용 JavaScript
 * 모바일 UI 컴포넌트와 상호작용을 관리합니다.
 */

// 모바일 메뉴 관리
class MobileMenuManager {
    constructor() {
        this.overlay = document.getElementById('mobile-menu-overlay');
        this.menu = document.getElementById('mobile-menu');
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        // 터치 이벤트 리스너 추가
        this.addTouchListeners();
        
        // 키보드 이벤트 리스너 추가
        this.addKeyboardListeners();
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // 스크롤 방지
        
        setTimeout(() => {
            this.menu.classList.remove('translate-x-full');
            this.isOpen = true;
        }, 10);
    }
    
    close() {
        this.menu.classList.add('translate-x-full');
        document.body.style.overflow = ''; // 스크롤 복원
        
        setTimeout(() => {
            this.overlay.classList.add('hidden');
            this.isOpen = false;
        }, 300);
    }
    
    addTouchListeners() {
        // 스와이프로 메뉴 닫기
        let startX = 0;
        let currentX = 0;
        
        this.menu.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });
        
        this.menu.addEventListener('touchmove', (e) => {
            currentX = e.touches[0].clientX;
            const diffX = currentX - startX;
            
            if (diffX > 0) {
                this.menu.style.transform = `translateX(${diffX}px)`;
            }
        });
        
        this.menu.addEventListener('touchend', (e) => {
            const diffX = currentX - startX;
            
            if (diffX > 100) { // 100px 이상 스와이프하면 닫기
                this.close();
            } else {
                this.menu.style.transform = '';
            }
        });
    }
    
    addKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }
}

// 모바일 장바구니 관리
class MobileCartManager {
    constructor() {
        this.bottomSheet = document.getElementById('mobile-cart-bottom-sheet');
        this.cartItems = document.getElementById('mobile-cart-items');
        this.emptyCart = document.getElementById('mobile-empty-cart');
        this.cartSummary = document.getElementById('mobile-cart-summary');
        this.cartTotal = document.getElementById('mobile-cart-total');
        this.cartBadge = document.getElementById('mobile-cart-badge');
        this.clearCartBtn = document.getElementById('mobile-clear-cart-btn');
        
        this.isOpen = false;
        this.startY = 0;
        this.currentY = 0;
        
        this.init();
    }
    
    init() {
        this.addTouchListeners();
        this.addKeyboardListeners();
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.bottomSheet.classList.remove('translate-y-full');
        this.isOpen = true;
        this.update();
        
        // 바디 스크롤 방지
        document.body.style.overflow = 'hidden';
    }
    
    close() {
        this.bottomSheet.classList.add('translate-y-full');
        this.isOpen = false;
        
        // 바디 스크롤 복원
        document.body.style.overflow = '';
    }
    
    update() {
        if (!window.cartData) return;
        
        if (cartData.length === 0) {
            this.showEmptyState();
        } else {
            this.showCartItems();
        }
    }
    
    showEmptyState() {
        this.cartItems.innerHTML = '';
        this.emptyCart.classList.remove('hidden');
        this.cartSummary.classList.add('hidden');
        this.cartBadge.classList.add('hidden');
        this.clearCartBtn.classList.add('hidden');
    }
    
    showCartItems() {
        this.emptyCart.classList.add('hidden');
        this.cartSummary.classList.remove('hidden');
        this.cartBadge.classList.remove('hidden');
        this.clearCartBtn.classList.remove('hidden');
        
        let itemsHTML = '';
        let totalAmount = 0;
        let totalItems = 0;
        
        cartData.forEach(item => {
            const itemTotal = (item.totalPrice || 0) * item.quantity;
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
            
            itemsHTML += this.generateItemHTML(item, optionsText);
        });
        
        this.cartItems.innerHTML = itemsHTML;
        this.cartTotal.textContent = this.formatNumber(totalAmount) + ' sats';
        this.cartBadge.textContent = totalItems;
    }
    
    generateItemHTML(item, optionsText) {
        return `
            <div class="mobile-cart-item relative overflow-hidden bg-gray-50 rounded-lg mb-2" data-item-id="${item.id}">
                <div class="flex items-center justify-between p-3">
                    <div class="flex-1">
                        <h4 class="font-medium text-gray-900">${this.escapeHtml(item.name)}</h4>
                        ${optionsText ? `<p class="text-sm text-gray-600">${this.escapeHtml(optionsText)}</p>` : ''}
                        <p class="text-sm text-blue-600">${this.formatNumber(item.totalPrice || 0)} sats × ${item.quantity}</p>
                    </div>
                    <div class="flex items-center space-x-2">
                                                 <button onclick="updateItemQuantity('${item.id}', ${item.quantity - 1})" 
                                 class="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center text-gray-600 transition-colors">
                             <i class="fas fa-minus text-xs"></i>
                         </button>
                         <span class="font-medium text-gray-900 w-8 text-center">${item.quantity}</span>
                         <button onclick="updateItemQuantity('${item.id}', ${item.quantity + 1})" 
                                 class="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center text-gray-600 transition-colors">
                             <i class="fas fa-plus text-xs"></i>
                         </button>
                         <button onclick="confirmRemoveCartItem('${item.id}', '${this.escapeHtml(item.name)}')" 
                                 class="w-8 h-8 bg-red-100 hover:bg-red-200 rounded-full flex items-center justify-center text-red-600 ml-1 transition-colors">
                             <i class="fas fa-trash text-xs"></i>
                         </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateQuantity(itemId, newQuantity) {
        if (window.updateItemQuantity) {
            window.updateItemQuantity(itemId, newQuantity);
            // 장바구니 업데이트 후 모바일 UI 갱신
            setTimeout(() => {
                this.update();
                // 전체 장바구니 디스플레이도 업데이트
                if (window.updateAllCartDisplays) {
                    window.updateAllCartDisplays();
                }
            }, 100);
        }
    }
    
    confirmRemoveItem(itemId, itemName) {
        if (confirm(`"${itemName}"을(를) 장바구니에서 제거하시겠습니까?`)) {
            if (window.removeCartItem) {
                window.removeCartItem(itemId);
                setTimeout(() => {
                    this.update();
                    // 전체 장바구니 디스플레이도 업데이트
                    if (window.updateAllCartDisplays) {
                        window.updateAllCartDisplays();
                    }
                }, 100);
            }
        }
    }
    
    confirmClearAll() {
        if (!window.cartData || cartData.length === 0) return;
        
        if (confirm(`장바구니의 모든 상품(${cartData.length}개)을 삭제하시겠습니까?`)) {
            if (window.clearCart) {
                window.clearCart();
                this.update();
            }
        }
    }
    
    processOrder() {
        this.close();
        if (window.showPaymentModal) {
            window.showPaymentModal();
        }
    }
    
    addTouchListeners() {
        // 드래그 핸들로 장바구니 닫기
        const handle = this.bottomSheet.querySelector('.w-12.h-1');
        if (handle) {
            handle.addEventListener('touchstart', (e) => {
                this.startY = e.touches[0].clientY;
            });
            
            handle.addEventListener('touchmove', (e) => {
                this.currentY = e.touches[0].clientY;
                const diffY = this.currentY - this.startY;
                
                if (diffY > 0) {
                    this.bottomSheet.style.transform = `translateY(${diffY}px)`;
                }
            });
            
            handle.addEventListener('touchend', (e) => {
                const diffY = this.currentY - this.startY;
                
                if (diffY > 100) { // 100px 이상 드래그하면 닫기
                    this.close();
                } else {
                    this.bottomSheet.style.transform = '';
                }
            });
        }
    }
    
    addKeyboardListeners() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }
    
    formatNumber(num) {
        return Math.round(num).toLocaleString();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 모바일 카테고리 관리
class MobileCategoryManager {
    constructor() {
        this.categoryItems = document.querySelectorAll('.mobile-category-item');
        this.init();
    }
    
    init() {
        this.categoryItems.forEach(item => {
            item.addEventListener('click', (e) => {
                this.handleCategoryClick(e.currentTarget);
            });
        });
    }
    
    handleCategoryClick(item) {
        const viewType = item.dataset.view;
        const categoryId = item.dataset.category;
        
        // 모바일 메뉴 닫기
        if (window.mobileMenu) {
            mobileMenu.close();
        }
        
        // 카테고리 변경
        if (viewType === 'menu-grid') {
            if (window.showView) {
                window.showView('menu-grid', categoryId);
            }
        } else {
            if (window.showView) {
                window.showView(viewType);
            }
        }
        
        // 활성화 상태 업데이트
        this.updateActiveState(item);
    }
    
    updateActiveState(activeItem) {
        this.categoryItems.forEach(item => {
            item.classList.remove('active');
        });
        activeItem.classList.add('active');
    }
}

// 전역 변수 및 함수들
let mobileMenu;
let mobileCart;
let mobileCategory;

// 모바일 컴포넌트 초기화
function initializeMobileComponents() {
    // 모바일 요소가 존재할 때만 초기화
    const mobileHeader = document.querySelector('.mobile-header');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const mobileCartBottomSheet = document.getElementById('mobile-cart-bottom-sheet');
    
    if (mobileHeader || mobileMenuOverlay || mobileCartBottomSheet) {
        try {
            if (mobileMenuOverlay && !mobileMenu) {
                mobileMenu = new MobileMenuManager();
            }
            if (mobileCartBottomSheet && !mobileCart) {
                mobileCart = new MobileCartManager();
            }
            if (document.querySelectorAll('.mobile-category-item').length > 0 && !mobileCategory) {
                mobileCategory = new MobileCategoryManager();
            }
            
            console.log('모바일 컴포넌트 초기화 완료');
        } catch (error) {
            console.error('모바일 컴포넌트 초기화 오류:', error);
        }
    }
}

// 전역 함수들 (HTML에서 호출)
function toggleMobileMenu() {
    if (mobileMenu) {
        mobileMenu.toggle();
    }
}

function closeMobileMenu() {
    if (mobileMenu) {
        mobileMenu.close();
    }
}

function toggleMobileCart() {
    if (mobileCart) {
        mobileCart.toggle();
    }
}

function closeMobileCart() {
    if (mobileCart) {
        mobileCart.close();
    }
}

function updateMobileCart() {
    if (mobileCart) {
        mobileCart.update();
    }
}

function confirmRemoveCartItem(itemId, itemName) {
    if (confirm(`"${itemName}"을(를) 장바구니에서 제거하시겠습니까?`)) {
        if (window.removeCartItem) {
            window.removeCartItem(itemId);
            // 모바일 장바구니 업데이트
            setTimeout(() => {
                if (mobileCart) {
                    mobileCart.update();
                }
            }, 100);
        }
    }
}

function confirmClearCart() {
    if (!window.cartData || cartData.length === 0) return;
    
    if (confirm(`장바구니의 모든 상품(${cartData.length}개)을 삭제하시겠습니까?`)) {
        if (window.clearCart) {
            window.clearCart();
            if (mobileCart) {
                mobileCart.update();
            }
        }
    }
}

function processOrderFromMobile() {
    if (mobileCart) {
        mobileCart.processOrder();
    }
}

// 화면 크기 변경 감지
window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
        // 데스크톱으로 전환 시 모바일 UI 정리
        if (mobileMenu && mobileMenu.isOpen) {
            mobileMenu.close();
        }
        if (mobileCart && mobileCart.isOpen) {
            mobileCart.close();
        }
    } else if (!mobileMenu || !mobileCart) {
        // 모바일로 전환 시 컴포넌트 초기화
        initializeMobileComponents();
    }
});

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 약간의 지연을 두고 초기화 (다른 스크립트들이 로드된 후)
    setTimeout(() => {
        initializeMobileComponents();
    }, 100);
});

// 페이지가 완전히 로드된 후에도 한 번 더 확인
window.addEventListener('load', () => {
    if (!mobileMenu || !mobileCart) {
        setTimeout(() => {
            initializeMobileComponents();
        }, 200);
    }
});

// 모듈 export (필요한 경우)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MobileMenuManager,
        MobileCartManager,
        MobileCategoryManager
    };
} 