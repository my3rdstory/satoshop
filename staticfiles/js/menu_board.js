// 메뉴판 전용 JavaScript

// 장바구니 데이터
let cart = [];

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeCategoryFilters();
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

// 장바구니에 메뉴 추가
function addToCart(menuId, menuName, price) {
    const existingItem = cart.find(item => item.menuId === menuId);
    
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({
            menuId: menuId,
            menuName: menuName,
            price: price,
            quantity: 1
        });
    }
    
    updateCartDisplay();
}

// 장바구니에서 메뉴 제거
function removeFromCart(menuId) {
    cart = cart.filter(item => item.menuId !== menuId);
    updateCartDisplay();
}

// 수량 업데이트
function updateQuantity(menuId, quantity) {
    const item = cart.find(item => item.menuId === menuId);
    if (item) {
        if (quantity <= 0) {
            removeFromCart(menuId);
        } else {
            item.quantity = quantity;
            updateCartDisplay();
        }
    }
}

// 장바구니 화면 업데이트
function updateCartDisplay() {
    const cartItemsContainer = document.getElementById('cart-items');
    const emptyCart = document.getElementById('empty-cart');
    const cartTotal = document.getElementById('cart-total');
    const totalAmount = document.getElementById('total-amount');
    
    if (cart.length === 0) {
        // 장바구니가 비어있을 때
        cartItemsContainer.innerHTML = '<div id="empty-cart" class="text-center py-8"><i class="fas fa-shopping-cart text-gray-400 text-3xl mb-3"></i><p class="text-gray-500 text-sm">장바구니가 비어있습니다</p></div>';
        cartTotal.classList.add('hidden');
    } else {
        // 장바구니에 아이템이 있을 때
        cartTotal.classList.remove('hidden');
        
        let total = 0;
        let cartHTML = '';
        
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            total += itemTotal;
            
            cartHTML += `
                <div class="bg-white p-3 rounded-lg border border-gray-200">
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-medium text-sm">${escapeHtml(item.menuName)}</h4>
                        <button onclick="removeFromCart(${item.menuId})" class="text-red-500 hover:text-red-700">
                            <i class="fas fa-times text-xs"></i>
                        </button>
                    </div>
                    <div class="flex justify-between items-center">
                        <div class="flex items-center space-x-2">
                            <button onclick="updateQuantity(${item.menuId}, ${item.quantity - 1})" 
                                    class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors">-</button>
                            <span class="text-sm font-medium">${item.quantity}</span>
                            <button onclick="updateQuantity(${item.menuId}, ${item.quantity + 1})" 
                                    class="w-6 h-6 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors">+</button>
                        </div>
                        <span class="text-sm font-semibold">${formatNumber(itemTotal)} sats</span>
                    </div>
                </div>
            `;
        });
        
        cartItemsContainer.innerHTML = cartHTML;
        totalAmount.textContent = `${formatNumber(total)} sats`;
    }
}

// 주문 처리
function processOrder() {
    if (cart.length === 0) {
        alert('장바구니가 비어있습니다.');
        return;
    }
    
    // 주문 확인
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const itemCount = cart.reduce((sum, item) => sum + item.quantity, 0);
    
    const confirmMessage = `총 ${itemCount}개 메뉴, ${formatNumber(total)} sats를 주문하시겠습니까?`;
    
    if (confirm(confirmMessage)) {
        // 여기에 실제 주문 처리 로직 구현 (나중에)
        alert('주문 기능은 아직 구현되지 않았습니다.');
        
        // 주문 완료 후 장바구니 비우기 (실제 구현 시)
        // cart = [];
        // updateCartDisplay();
    }
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