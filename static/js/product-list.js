// 상품 목록 페이지 JavaScript

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('Product list page loaded');
    
    // 상품 카드 호버 효과 초기화
    initProductCardEffects();
    
    // 이미지 로딩 처리
    initImageLoading();
    
    // 상품 카드 클릭 이벤트
    initProductCardClicks();
});

// 상품 카드 호버 효과
function initProductCardEffects() {
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        // 호버 시 그림자 효과 강화
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-2xl');
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-2xl');
            this.style.transform = 'translateY(0)';
        });
    });
}

// 이미지 로딩 처리
function initImageLoading() {
    const productImages = document.querySelectorAll('.product-card img');
    
    productImages.forEach(img => {
        // 이미지 로딩 중 스켈레톤 효과
        img.addEventListener('load', function() {
            this.classList.add('loaded');
        });
        
        // 이미지 로딩 실패 시 기본 이미지 표시
        img.addEventListener('error', function() {
            this.src = '/static/images/no-image.png';
            this.alt = '이미지를 불러올 수 없습니다';
        });
    });
}

// 상품 카드 클릭 이벤트
function initProductCardClicks() {
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        // 카드 전체 클릭 시 상품 상세 페이지로 이동
        card.addEventListener('click', function(e) {
            // 버튼이나 링크를 클릭한 경우는 제외
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || 
                e.target.closest('a') || e.target.closest('button')) {
                return;
            }
            
            // 상품 링크 찾기
            const productLink = this.querySelector('a[href*="product"]');
            if (productLink) {
                window.location.href = productLink.href;
            }
        });
    });
}

// 상품 상태 표시 업데이트
function updateProductStatus(productId, isActive) {
    const productCard = document.querySelector(`[data-product-id="${productId}"]`);
    if (!productCard) return;
    
    const statusBadge = productCard.querySelector('.status-badge');
    const actionButtons = productCard.querySelectorAll('.action-button');
    
    if (isActive) {
        productCard.classList.remove('inactive');
        if (statusBadge) statusBadge.style.display = 'none';
        actionButtons.forEach(btn => btn.disabled = false);
    } else {
        productCard.classList.add('inactive');
        if (statusBadge) statusBadge.style.display = 'block';
        actionButtons.forEach(btn => btn.disabled = true);
    }
}

// 가격 포맷팅 함수
function formatPrice(price, currency = 'sats') {
    if (currency === 'krw') {
        return new Intl.NumberFormat('ko-KR').format(price) + ' 원';
    } else {
        return new Intl.NumberFormat('ko-KR').format(price) + ' sats';
    }
}

// 할인율 계산
function calculateDiscountRate(originalPrice, discountedPrice) {
    if (originalPrice <= 0) return 0;
    return Math.round(((originalPrice - discountedPrice) / originalPrice) * 100);
}

// 상품 검색/필터링 (향후 확장용)
function filterProducts(searchTerm) {
    const productCards = document.querySelectorAll('.product-card');
    const searchLower = searchTerm.toLowerCase();
    
    productCards.forEach(card => {
        const title = card.querySelector('h4')?.textContent.toLowerCase() || '';
        const description = card.querySelector('.description')?.textContent.toLowerCase() || '';
        
        if (title.includes(searchLower) || description.includes(searchLower)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// 상품 정렬 (향후 확장용)
function sortProducts(sortBy) {
    const container = document.querySelector('.grid');
    if (!container) return;
    
    const cards = Array.from(container.querySelectorAll('.product-card'));
    
    cards.sort((a, b) => {
        switch (sortBy) {
            case 'price-low':
                return getProductPrice(a) - getProductPrice(b);
            case 'price-high':
                return getProductPrice(b) - getProductPrice(a);
            case 'name':
                return getProductName(a).localeCompare(getProductName(b));
            default:
                return 0;
        }
    });
    
    // 정렬된 순서로 다시 배치
    cards.forEach(card => container.appendChild(card));
}

// 헬퍼 함수들
function getProductPrice(card) {
    const priceText = card.querySelector('.price')?.textContent || '0';
    return parseInt(priceText.replace(/[^\d]/g, '')) || 0;
}

function getProductName(card) {
    return card.querySelector('h4')?.textContent || '';
}

// 성공 메시지 표시
function showSuccessMessage(message) {
    // 기존 메시지가 있다면 제거
    const existingMessage = document.querySelector('.success-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = 'success-message fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300';
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateX(100%)';
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

// 에러 메시지 표시
function showErrorMessage(message) {
    // 기존 메시지가 있다면 제거
    const existingMessage = document.querySelector('.error-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = 'error-message fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300';
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 5초 후 자동 제거
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateX(100%)';
        setTimeout(() => messageDiv.remove(), 300);
    }, 5000);
} 