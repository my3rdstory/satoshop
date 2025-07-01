// 메뉴 판매 현황 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeMenuOrders();
});

function initializeMenuOrders() {
    // 메뉴 카드 호버 효과
    setupMenuCardHovers();
    
    // 검색 및 필터 기능 (추후 확장용)
    setupSearchAndFilter();
    
    // 반응형 처리
    handleResponsive();
}

// 통계 카드 애니메이션 제거됨

// 메뉴 카드 호버 효과
function setupMenuCardHovers() {
    const menuCards = document.querySelectorAll('a[href*="menu_orders_detail"]');
    
    menuCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('menu-card');
            
            // 이미지 확대 효과
            const image = this.querySelector('img');
            if (image) {
                image.classList.add('menu-image');
            }
        });
        
        card.addEventListener('mouseleave', function() {
            const image = this.querySelector('img');
            if (image) {
                image.classList.remove('menu-image');
            }
        });
    });
}

// 검색 및 필터 기능 (추후 확장용)
function setupSearchAndFilter() {
    // 메뉴 검색 기능
    const searchInput = document.getElementById('menu-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            filterMenus(this.value);
        }, 300));
    }
    
    // 상태 필터 기능
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            filterMenusByStatus(this.value);
        });
    }
}

// 메뉴 필터링 함수
function filterMenus(searchTerm) {
    const menuCards = document.querySelectorAll('[href*="menu_orders_detail"]');
    const searchLower = searchTerm.toLowerCase();
    
    menuCards.forEach(card => {
        const menuName = card.querySelector('h3').textContent.toLowerCase();
        const shouldShow = menuName.includes(searchLower);
        
        card.style.display = shouldShow ? 'block' : 'none';
        
        // 부모 그리드 아이템도 처리
        const gridItem = card.closest('.grid > div');
        if (gridItem) {
            gridItem.style.display = shouldShow ? 'block' : 'none';
        }
    });
    
    // 검색 결과 없음 메시지 표시
    updateEmptyState();
}

// 상태별 메뉴 필터링
function filterMenusByStatus(status) {
    const menuCards = document.querySelectorAll('[href*="menu_orders_detail"]');
    
    menuCards.forEach(card => {
        let shouldShow = true;
        
        if (status === 'active') {
            shouldShow = !card.classList.contains('menu-card-inactive');
        } else if (status === 'inactive') {
            shouldShow = card.classList.contains('menu-card-inactive');
        }
        // 'all'인 경우 모두 표시
        
        card.style.display = shouldShow ? 'block' : 'none';
        
        const gridItem = card.closest('.grid > div');
        if (gridItem) {
            gridItem.style.display = shouldShow ? 'block' : 'none';
        }
    });
    
    updateEmptyState();
}

// 빈 상태 업데이트
function updateEmptyState() {
    const menuCards = document.querySelectorAll('[href*="menu_orders_detail"]');
    const visibleCards = Array.from(menuCards).filter(card => 
        card.style.display !== 'none'
    );
    
    const emptyState = document.querySelector('.empty-state');
    const menuGrid = document.querySelector('.grid');
    
    if (visibleCards.length === 0 && menuGrid) {
        if (!emptyState) {
            showNoResultsMessage();
        }
    } else if (emptyState && visibleCards.length > 0) {
        hideNoResultsMessage();
    }
}

// 검색 결과 없음 메시지 표시
function showNoResultsMessage() {
    const menuGrid = document.querySelector('.grid');
    if (menuGrid) {
        const noResultsHtml = `
            <div class="col-span-full text-center py-12 no-results-message">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full mb-4">
                    <i class="fas fa-search text-3xl text-gray-400"></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">검색 결과가 없습니다</h3>
                <p class="text-gray-600 dark:text-gray-400">다른 검색어를 시도해보세요.</p>
            </div>
        `;
        menuGrid.insertAdjacentHTML('beforeend', noResultsHtml);
    }
}

// 검색 결과 없음 메시지 숨기기
function hideNoResultsMessage() {
    const noResultsMessage = document.querySelector('.no-results-message');
    if (noResultsMessage) {
        noResultsMessage.remove();
    }
}

// 반응형 처리
function handleResponsive() {
    // 윈도우 리사이즈 이벤트
    window.addEventListener('resize', debounce(function() {
        adjustLayoutForScreenSize();
    }, 250));
    
    // 초기 레이아웃 조정
    adjustLayoutForScreenSize();
}

// 화면 크기에 따른 레이아웃 조정
function adjustLayoutForScreenSize() {
    const screenWidth = window.innerWidth;
    const menuGrid = document.querySelector('.grid');
    
    if (menuGrid) {
        // 모바일에서는 1열, 태블릿에서는 2열, 데스크톱에서는 3열
        if (screenWidth < 768) {
            menuGrid.className = menuGrid.className.replace(/md:grid-cols-\d+|lg:grid-cols-\d+/g, '');
            menuGrid.classList.add('grid-cols-1');
        } else if (screenWidth < 1024) {
            menuGrid.className = menuGrid.className.replace(/lg:grid-cols-\d+/g, '');
            if (!menuGrid.classList.contains('md:grid-cols-2')) {
                menuGrid.classList.add('md:grid-cols-2');
            }
        }
    }
}

// 디바운스 함수
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 페이지 새로고침 함수
function refreshPage() {
    window.location.reload();
}

// 메뉴 관리 페이지로 이동
function goToMenuManagement() {
    const storeId = window.location.pathname.split('/')[2];
    window.location.href = `/menu/${storeId}/`;
}

// 스토어 관리로 돌아가기
function goToStoreManagement() {
    window.location.href = '/stores/my-stores/';
}

// 로딩 상태 표시
function showLoading() {
    const menuGrid = document.querySelector('.grid');
    if (menuGrid) {
        menuGrid.innerHTML = '';
        
        // 로딩 스켈레톤 생성
        for (let i = 0; i < 6; i++) {
            const skeletonHtml = `
                <div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-4 border border-gray-200 dark:border-gray-600">
                    <div class="flex items-start space-x-4">
                        <div class="w-16 h-16 bg-gray-200 dark:bg-gray-600 rounded-full loading-skeleton"></div>
                        <div class="flex-1 min-w-0 space-y-2">
                            <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div>
                            <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded w-3/4 loading-skeleton"></div>
                            <div class="grid grid-cols-3 gap-2 mt-3">
                                <div class="text-center">
                                    <div class="h-6 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton mb-1"></div>
                                    <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div>
                                </div>
                                <div class="text-center">
                                    <div class="h-6 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton mb-1"></div>
                                    <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div>
                                </div>
                                <div class="text-center">
                                    <div class="h-6 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton mb-1"></div>
                                    <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            menuGrid.insertAdjacentHTML('beforeend', skeletonHtml);
        }
    }
}

// 에러 상태 표시
function showError(message) {
    const container = document.querySelector('.max-w-7xl');
    if (container) {
        const errorHtml = `
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 mb-8">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <i class="fas fa-exclamation-triangle text-red-600 dark:text-red-400 text-xl"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-red-800 dark:text-red-200 font-semibold">오류가 발생했습니다</h3>
                        <p class="text-red-700 dark:text-red-300 text-sm mt-1">${message}</p>
                    </div>
                    <div class="ml-auto">
                        <button onclick="refreshPage()" class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
                            다시 시도
                        </button>
                    </div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('afterbegin', errorHtml);
    }
}

// 성공 메시지 표시
function showSuccess(message) {
    const container = document.querySelector('.max-w-7xl');
    if (container) {
        const successHtml = `
            <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-6 mb-8 success-message">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <i class="fas fa-check-circle text-green-600 dark:text-green-400 text-xl"></i>
                    </div>
                    <div class="ml-3">
                        <p class="text-green-800 dark:text-green-200 font-medium">${message}</p>
                    </div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('afterbegin', successHtml);
        
        // 3초 후 자동 제거
        setTimeout(() => {
            const successMessage = document.querySelector('.success-message');
            if (successMessage) {
                successMessage.remove();
            }
        }, 3000);
    }
} 