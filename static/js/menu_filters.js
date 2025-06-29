// 메뉴 카테고리 필터링 JavaScript

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeCategoryFilters();
});

// 카테고리 필터 초기화
function initializeCategoryFilters() {
    const categoryItems = document.querySelectorAll('.category-item');
    
    categoryItems.forEach(item => {
        item.addEventListener('click', function() {
            const categoryId = this.dataset.category;
            
            // 활성 카테고리 스타일 업데이트
            updateActiveCategoryStyle(this);
            
            // 메뉴 필터링
            filterMenusByCategory(categoryId);
        });
    });
}

// 활성 카테고리 스타일 업데이트
function updateActiveCategoryStyle(activeItem) {
    // 모든 카테고리 아이템에서 active 클래스 제거
    document.querySelectorAll('.category-item').forEach(item => {
        item.classList.remove('active');
        const icon = item.querySelector('i');
        if (icon) {
            icon.classList.remove('text-blue-500', 'text-white');
            icon.classList.add('text-gray-500');
        }
    });
    
    // 선택된 카테고리에 active 클래스 추가
    activeItem.classList.add('active');
    const activeIcon = activeItem.querySelector('i');
    if (activeIcon) {
        activeIcon.classList.remove('text-gray-500');
        activeIcon.classList.add('text-blue-500');
    }
}

// 카테고리별 메뉴 필터링
function filterMenusByCategory(categoryId) {
    const menuCards = document.querySelectorAll('.menu-card');
    
    menuCards.forEach(card => {
        const menuCategories = JSON.parse(card.dataset.categories || '[]');
        
        if (categoryId === 'all' || menuCategories.includes(parseInt(categoryId))) {
            // 메뉴 표시 (애니메이션 효과)
            card.style.display = 'block';
            card.style.opacity = '0';
            card.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.3s ease-out';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        } else {
            // 메뉴 숨김 (애니메이션 효과)
            card.style.transition = 'all 0.3s ease-out';
            card.style.opacity = '0';
            card.style.transform = 'translateY(-10px)';
            
            setTimeout(() => {
                card.style.display = 'none';
            }, 300);
        }
    });
}

// URL 해시를 통한 카테고리 자동 선택
function handleCategoryHash() {
    const hash = window.location.hash;
    if (hash.startsWith('#category-')) {
        const categoryId = hash.replace('#category-', '');
        const categoryItem = document.querySelector(`[data-category="${categoryId}"]`);
        
        if (categoryItem) {
            categoryItem.click();
        }
    }
}

// 페이지 로드 시 URL 해시 처리
window.addEventListener('load', handleCategoryHash);

// 해시 변경 시 카테고리 선택
window.addEventListener('hashchange', handleCategoryHash); 