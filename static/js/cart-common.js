// 장바구니 관련 공통 함수들

// 장바구니 배지 업데이트
function updateCartBadge(itemCount) {
    const cartBadge = document.getElementById('cartBadge');
    const cartToggleBtn = document.getElementById('cartToggleBtn');
    
    if (!cartToggleBtn) return;

    if (itemCount > 0) {
        if (cartBadge) {
            cartBadge.textContent = itemCount;
            cartBadge.style.display = 'flex';
        } else {
            // 배지가 없으면 새로 생성
            const badge = document.createElement('span');
            badge.id = 'cartBadge';
            badge.className = 'absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center';
            badge.textContent = itemCount;
            cartToggleBtn.appendChild(badge);
        }
        // 애니메이션 효과
        cartToggleBtn.classList.add('animate-pulse');
        setTimeout(() => {
            cartToggleBtn.classList.remove('animate-pulse');
        }, 1000);
    } else {
        if (cartBadge) {
            cartBadge.style.display = 'none';
        }
    }
}

// 성공 메시지 표시
function showSuccessMessage(message) {
    // 기존 메시지가 있으면 제거
    const existingMessage = document.getElementById('successMessage');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.id = 'successMessage';
    messageDiv.className = 'fixed top-20 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform translate-x-0 transition-transform duration-300';
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        messageDiv.classList.add('translate-x-full');
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 300);
    }, 3000);
}

// 장바구니 내용 업데이트
async function updateCartContent() {
    try {
        const response = await fetch('/orders/cart/api/');
        const data = await response.json();
        
        // console.log('장바구니 API 응답:', data); // 디버깅용
        
        if (data.success) {
            // 장바구니 HTML 업데이트
            const cartContent = document.getElementById('cartContent');
            if (cartContent) {
                cartContent.innerHTML = generateCartHTML(data.cart_items, data.total_amount);
            }
            
            // 액션 버튼 표시/숨김
            const cartActions = document.getElementById('cartActions');
            if (cartActions) {
                if (data.cart_items && data.cart_items.length > 0) {
                    cartActions.style.display = 'block';
                } else {
                    cartActions.style.display = 'none';
                }
            }
        } else {
            console.error('장바구니 API 오류:', data.error);
        }
    } catch (error) {
        console.error('장바구니 내용 업데이트 오류:', error);
    }
}

// 장바구니 HTML 생성
function generateCartHTML(cartItems, totalAmount) {
    if (!cartItems || cartItems.length === 0) {
        return `
            <div class="flex flex-col items-center justify-center h-full p-6 text-center">
                <div class="text-6xl mb-4">🛒</div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">장바구니가 비어있습니다</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">다양한 스토어에서 상품을 추가해보세요!</p>
                <div class="text-xs text-gray-400 dark:text-gray-500">
                    <p>• 여러 스토어의 상품을 함께 담을 수 있습니다</p>
                    <p>• 스토어별로 정리되어 표시됩니다</p>
                </div>
            </div>
        `;
    }
    
    let totalItems = cartItems.reduce((sum, store) => sum + store.items.length, 0);
    
    let html = `
        <!-- 장바구니 요약 -->
        <div class="p-3 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-600">
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <i class="fas fa-shopping-bag mr-2 text-bitcoin"></i>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">총 ${totalItems}개 상품</span>
                </div>
                <span class="text-lg font-bold text-bitcoin">${totalAmount.toLocaleString()} sats</span>
            </div>
        </div>
        
        <!-- 스토어별 상품 리스트 -->
        <div class="p-2 space-y-2">
    `;
    
    cartItems.forEach(store => {
        html += `
            <!-- 스토어 그룹 컨테이너 -->
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
                <!-- 스토어 헤더 -->
                <div class="bg-gray-50 dark:bg-gray-700 px-3 py-2 border-b border-gray-200 dark:border-gray-600">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <i class="fas fa-store mr-2 text-bitcoin"></i>
                            <span class="text-sm font-semibold text-gray-900 dark:text-white">${store.store_name}</span>
                        </div>
                        <span class="text-xs text-gray-500 dark:text-gray-400">${store.items.length}개</span>
                    </div>
                </div>
                
                <!-- 스토어 상품 목록 -->
                <div class="p-1.5 space-y-1.5">
        `;
        
        store.items.forEach(item => {
            html += `
                <div class="flex items-start space-x-2 p-1.5 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-100 dark:border-gray-600">
                    <!-- 상품 이미지 -->
                    <div class="flex-shrink-0 w-10 h-10">
                        ${item.product && item.product.images && item.product.images.first && item.product.images.first.file_url ? 
                            `<img src="${item.product.images.first.file_url}" alt="${item.product.title || ''}" class="w-full h-full object-cover rounded">` :
                            `<div class="w-full h-full bg-gray-200 dark:bg-gray-600 rounded flex items-center justify-center">
                                <i class="fas fa-image text-gray-400 text-xs"></i>
                            </div>`
                        }
                    </div>
                    
                    <!-- 상품 정보 -->
                    <div class="flex-1 min-w-0">
                        <!-- 상품명과 삭제 버튼 -->
                        <div class="flex items-start justify-between">
                            <h4 class="text-xs font-medium text-gray-900 dark:text-white truncate pr-2">
                                ${item.product && item.product.title ? 
                                    (item.product.title.length > 20 ? item.product.title.substring(0, 20) + '...' : item.product.title) : 
                                    '상품명 없음'
                                }
                            </h4>
                            <button class="flex-shrink-0 text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors rounded p-0.5" 
                                    onclick="removeFromCart(${item.id})" title="삭제">
                                <i class="fas fa-times text-xs"></i>
                            </button>
                        </div>
                        
                        <!-- 수량과 가격 -->
                        <div class="flex items-center justify-between mt-1">
                            <div class="flex items-center text-xs text-gray-500 dark:text-gray-400">
                                <i class="fas fa-box mr-1"></i>
                                <span>${item.quantity}개</span>
                            </div>
                            <span class="text-xs font-medium text-gray-900 dark:text-white">
                                ${item.total_price ? item.total_price.toLocaleString() : '0'} sats
                            </span>
                        </div>
                        
                        <!-- 옵션 정보 -->
                        ${item.options_display && item.options_display.length > 0 ? 
                            `<div class="mt-1 flex flex-wrap gap-1">
                                ${item.options_display.map(option => 
                                    `<span class="inline-block px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded text-xs">
                                        ${option.option_name || ''}: ${option.choice_name || ''}
                                        ${option.choice_price && option.choice_price > 0 ? `(+${option.choice_price.toLocaleString()}sats)` : ''}
                                    </span>`
                                ).join('')}
                            </div>` : 
                            ''
                        }
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
    `;
    
    return html;
}

// 장바구니에서 아이템 삭제 (비동기)
async function removeFromCart(itemId) {
    if (!confirm('이 상품을 장바구니에서 삭제하시겠습니까?')) {
        return;
    }

    // CSRF 토큰 가져오기 (Django 표준 방법)
    function getCookie(name) {
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
    
    const csrfToken = getCookie('csrftoken');
    
    if (!csrfToken) {
        alert('CSRF 토큰을 찾을 수 없습니다. 페이지를 새로고침해주세요.');
        return;
    }

    try {
        const response = await fetch('/orders/cart/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                'item_id': itemId
            })
        });

        const data = await response.json();
        
        if (data.success) {
            // 사이드바 장바구니가 있으면 비동기 업데이트
            if (document.getElementById('cartContent')) {
                // 장바구니 내용 비동기 업데이트
                await updateCartContent();
                
                // 장바구니 배지 업데이트 (총 개수 다시 계산)
                const cartResponse = await fetch('/orders/cart/api/');
                const cartData = await cartResponse.json();
                if (cartData.success) {
                    updateCartBadge(cartData.total_items);
                }
                
                // 성공 메시지
                showSuccessMessage('상품이 삭제되었습니다.');
            } else {
                // 일반 장바구니 페이지에서는 새로고침
                location.reload();
            }
        } else {
            alert('삭제 중 오류가 발생했습니다: ' + (data.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('삭제 중 오류가 발생했습니다.');
    }
} 