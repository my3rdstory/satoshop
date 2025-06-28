// 메뉴 목록 JavaScript
console.log('menu-list.js 파일이 로드되었습니다');
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded 이벤트가 발생했습니다');
    // DOM 요소들
    const menuCards = document.querySelectorAll('.menu-card');
    const searchInput = document.getElementById('menuSearch');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const sortSelect = document.getElementById('menuSort');
    
    // 카테고리 관련 요소들
    const categoryFilters = document.getElementById('categoryFilters');
    const clearCategoryFilter = document.getElementById('clearCategoryFilter');
    
    // 카테고리 관련 변수
    let categories = [];
    let selectedCategoryId = null;

    // 검색 기능
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            filterMenus(searchTerm);
        });
    }

    // 필터 기능
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 모든 버튼에서 active 클래스 제거
            filterButtons.forEach(btn => btn.classList.remove('active'));
            // 클릭된 버튼에 active 클래스 추가
            this.classList.add('active');
            
            const filterType = this.dataset.filter;
            filterByStatus(filterType);
        });
    });

    // 정렬 기능
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            const sortType = this.value;
            sortMenus(sortType);
        });
    }

    // 메뉴 카드 호버 효과
    if (menuCards && menuCards.length > 0) {
        menuCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    }

    // 카테고리 필터 이벤트 리스너
    if (clearCategoryFilter) {
        clearCategoryFilter.addEventListener('click', clearCategoryFilters);
    }

    // 초기화 - 카테고리 필터를 위해 항상 카테고리 로드
    console.log('초기화 시작 - loadCategories 호출');
    
    // DOM이 완전히 준비되었는지 확인 후 카테고리 로드
    if (document.readyState === 'complete') {
        loadCategories();
    } else {
        window.addEventListener('load', loadCategories);
    }

    // 장바구니 추가 기능
    window.addToCart = function(menuId, menuName) {
        if (confirm(`"${menuName}" 메뉴를 장바구니에 추가하시겠습니까?`)) {
            fetch(`/menu/add-to-cart/${menuId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    quantity: 1
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('장바구니에 추가되었습니다.', 'success');
                    updateCartCount(data.cart_count);
                } else {
                    showNotification('오류가 발생했습니다: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('네트워크 오류가 발생했습니다.', 'error');
            });
        }
    };

    // 메뉴 삭제 기능
    window.deleteMenu = function(menuId, menuName) {
        if (confirm(`"${menuName}" 메뉴를 정말 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
            fetch(`/menu/delete/${menuId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('메뉴가 삭제되었습니다.', 'success');
                    // 메뉴 카드 제거
                    const menuCard = document.querySelector(`[data-menu-id="${menuId}"]`);
                    if (menuCard) {
                        menuCard.style.opacity = '0';
                        menuCard.style.transform = 'scale(0.9)';
                        setTimeout(() => {
                            menuCard.remove();
                            checkEmptyState();
                        }, 300);
                    }
                } else {
                    showNotification('오류가 발생했습니다: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('네트워크 오류가 발생했습니다.', 'error');
            });
        }
    };

    // 함수들
    function filterMenus(searchTerm) {
        if (!menuCards || menuCards.length === 0) {
            return;
        }

        menuCards.forEach(card => {
            const menuName = card.querySelector('.menu-name')?.textContent.toLowerCase() || '';
            const menuDescription = card.querySelector('.menu-description')?.textContent.toLowerCase() || '';
            
            const matches = menuName.includes(searchTerm) || menuDescription.includes(searchTerm);
            
            if (matches) {
                card.style.display = 'block';
                card.style.opacity = '1';
            } else {
                card.style.display = 'none';
                card.style.opacity = '0';
            }
        });
        
        checkEmptyState();
    }

    function filterByStatus(filterType) {
        if (!menuCards || menuCards.length === 0) {
            return;
        }

        menuCards.forEach(card => {
            const statusBadge = card.querySelector('.menu-status-badge');
            let shouldShow = true;

            switch (filterType) {
                case 'all':
                    shouldShow = true;
                    break;
                case 'available':
                    shouldShow = statusBadge?.classList.contains('menu-status-available') || false;
                    break;
                case 'out-of-stock':
                    shouldShow = statusBadge?.classList.contains('menu-status-out-of-stock') || false;
                    break;
                case 'temporary-out':
                    shouldShow = statusBadge?.classList.contains('menu-status-temporary-out') || false;
                    break;
                case 'discounted':
                    shouldShow = card.querySelector('.menu-discount-badge') !== null;
                    break;
            }

            if (shouldShow) {
                card.style.display = 'block';
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 50);
            } else {
                card.style.opacity = '0';
                card.style.transform = 'translateY(10px)';
                setTimeout(() => {
                    card.style.display = 'none';
                }, 300);
            }
        });

        setTimeout(() => {
            checkEmptyState();
        }, 350);
    }

    function sortMenus(sortType) {
        const menuGrid = document.querySelector('.menu-grid');
        if (!menuGrid || !menuCards || menuCards.length === 0) return;

        const menuArray = Array.from(menuCards);
        
        menuArray.sort((a, b) => {
            switch (sortType) {
                case 'name-asc':
                    return getMenuName(a).localeCompare(getMenuName(b));
                case 'name-desc':
                    return getMenuName(b).localeCompare(getMenuName(a));
                case 'price-asc':
                    return getMenuPrice(a) - getMenuPrice(b);
                case 'price-desc':
                    return getMenuPrice(b) - getMenuPrice(a);
                case 'newest':
                    return getMenuDate(b) - getMenuDate(a);
                case 'oldest':
                    return getMenuDate(a) - getMenuDate(b);
                default:
                    return 0;
            }
        });

        // 정렬된 순서로 DOM에 다시 추가
        menuArray.forEach(card => {
            menuGrid.appendChild(card);
        });

        // 애니메이션 효과
        menuArray.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 50);
        });
    }

    function getMenuName(card) {
        return card.querySelector('.menu-name')?.textContent.trim() || '';
    }

    function getMenuPrice(card) {
        const priceText = card.querySelector('.menu-price')?.textContent || '0';
        return parseInt(priceText.replace(/[^\d]/g, '')) || 0;
    }

    function getMenuDate(card) {
        const dateAttr = card.dataset.createdAt;
        return dateAttr ? new Date(dateAttr).getTime() : 0;
    }

    function checkEmptyState() {
        // menuCards가 존재하지 않거나 비어있는 경우 안전하게 처리
        if (!menuCards || menuCards.length === 0) {
            return;
        }

        const visibleCards = Array.from(menuCards).filter(card => 
            card.style.display !== 'none' && card.style.opacity !== '0'
        );

        const emptyState = document.querySelector('.menu-empty-state');
        const menuGrid = document.querySelector('.menu-grid');

        if (visibleCards.length === 0) {
            if (!emptyState && menuGrid) {
                const emptyStateHtml = `
                    <div class="menu-empty-state text-center py-16">
                        <div class="menu-empty-icon">
                            <i class="fas fa-utensils"></i>
                        </div>
                        <h3 class="menu-empty-title">메뉴가 없습니다</h3>
                        <p class="menu-empty-description">검색 조건에 맞는 메뉴를 찾을 수 없습니다.</p>
                    </div>
                `;
                menuGrid.insertAdjacentHTML('afterend', emptyStateHtml);
            } else if (emptyState) {
                emptyState.style.display = 'block';
            }
        } else {
            if (emptyState) {
                emptyState.style.display = 'none';
            }
        }
    }

    function showNotification(message, type = 'info') {
        // 기존 알림 제거
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // 새 알림 생성
        const notification = document.createElement('div');
        notification.className = `notification fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // 3초 후 자동 제거
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    function updateCartCount(count) {
        const cartButton = document.querySelector('[href*="cart"]');
        if (cartButton) {
            const countElement = cartButton.querySelector('.cart-count');
            if (countElement) {
                countElement.textContent = count;
            } else {
                cartButton.innerHTML = cartButton.innerHTML.replace(/\(\d+\)/, `(${count})`);
            }
        }
    }

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // 무한 스크롤 (필요한 경우)
    function setupInfiniteScroll() {
        let loading = false;
        let page = 1;

        window.addEventListener('scroll', () => {
            if (loading) return;

            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            
            if (scrollTop + clientHeight >= scrollHeight - 1000) {
                loading = true;
                loadMoreMenus(++page);
            }
        });
    }

    function loadMoreMenus(page) {
        fetch(`?page=${page}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newMenus = doc.querySelectorAll('.menu-card');
            
            const menuGrid = document.querySelector('.menu-grid');
            newMenus.forEach(menu => {
                menuGrid.appendChild(menu);
            });
            
            loading = false;
        })
        .catch(error => {
            console.error('Error loading more menus:', error);
            loading = false;
        });
    }

    // === 카테고리 관리 함수들 ===
    
    function loadCategories() {
        const storeId = getStoreIdFromUrl();
        console.log('loadCategories 호출됨, storeId:', storeId);
        if (!storeId) {
            console.error('storeId를 찾을 수 없습니다');
            return;
        }

        fetch(`/menu/${storeId}/categories/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            console.log('카테고리 API 응답:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('카테고리 데이터:', data);
            if (data.success) {
                categories = data.categories;
                console.log('카테고리 개수:', categories.length);
                renderCategoryFilters();
            } else {
                console.error('카테고리 로드 실패:', data);
            }
        })
        .catch(error => {
            console.error('카테고리 로드 오류:', error);
        });
    }

    // 전역으로 함수 노출 (디버깅용)
    window.loadCategories = loadCategories;

    function renderCategoryFilters() {
        console.log('renderCategoryFilters 호출됨');
        console.log('categoryFilters 요소:', categoryFilters);
        console.log('categories 배열:', categories);
        
        if (!categoryFilters) {
            console.error('categoryFilters 요소를 찾을 수 없습니다');
            return;
        }

        categoryFilters.innerHTML = '';
        
        if (categories.length === 0) {
            console.log('카테고리가 없어서 "카테고리 없음" 메시지 표시');
            categoryFilters.innerHTML = '<span class="text-gray-500 dark:text-gray-400 text-sm italic">카테고리 없음</span>';
            return;
        }
        
        console.log('카테고리 버튼 생성 중...');
        categories.forEach(category => {
            const filterBtn = document.createElement('button');
            filterBtn.className = 'category-filter-btn px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900 hover:text-blue-600 dark:hover:text-blue-300 transition-colors';
            filterBtn.textContent = category.name;
            filterBtn.onclick = () => filterByCategory(category.id);
            categoryFilters.appendChild(filterBtn);
            console.log('카테고리 버튼 추가됨:', category.name);
        });
    }

    function filterByCategory(categoryId) {
        selectedCategoryId = categoryId;
        
        // 필터 버튼 활성화 상태 업데이트
        document.querySelectorAll('.category-filter-btn').forEach(btn => {
            btn.classList.remove('bg-blue-500', 'text-white');
            btn.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        });
        
        if (categoryId && event.target) {
            event.target.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
            event.target.classList.add('bg-blue-500', 'text-white');
        }

        // 메뉴 카드 필터링 (menuCards가 존재하는 경우에만)
        if (menuCards && menuCards.length > 0) {
            menuCards.forEach(card => {
                const menuCategories = JSON.parse(card.dataset.categories || '[]');
                const shouldShow = !categoryId || menuCategories.includes(categoryId);
                
                if (shouldShow) {
                    card.style.display = 'block';
                    card.style.opacity = '1';
                } else {
                    card.style.display = 'none';
                    card.style.opacity = '0';
                }
            });
        }

        checkEmptyState();
    }

    function clearCategoryFilters() {
        selectedCategoryId = null;
        
        // 모든 필터 버튼 비활성화
        document.querySelectorAll('.category-filter-btn').forEach(btn => {
            btn.classList.remove('bg-blue-500', 'text-white');
            btn.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        });

        // 모든 메뉴 카드 표시 (menuCards가 존재하는 경우에만)
        if (menuCards && menuCards.length > 0) {
            menuCards.forEach(card => {
                card.style.display = 'block';
                card.style.opacity = '1';
            });
        }

        checkEmptyState();
    }

    // 전역 함수로 노출
    window.clearCategoryFilters = clearCategoryFilters;




    function getStoreIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const menuIndex = pathParts.indexOf('menu');
        return menuIndex !== -1 && pathParts[menuIndex + 1] ? pathParts[menuIndex + 1] : null;
    }

    // 초기화
    checkEmptyState();
    
    // 무한 스크롤 활성화 (옵션)
    // setupInfiniteScroll();
}); 