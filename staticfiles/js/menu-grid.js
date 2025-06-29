// 메뉴 그리드 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소들
    const menuCards = document.querySelectorAll('.menu-card');
    const menuGrid = document.querySelector('.menu-grid-container');

    // 메뉴 카드 초기화
    initializeMenuCards();

    // 메뉴 카드 호버 효과
    function initializeMenuCards() {
        menuCards.forEach(card => {
            // 호버 효과
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
                this.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
            });

            // 이미지 로드 에러 처리
            const menuImage = card.querySelector('.menu-image');
            if (menuImage) {
                menuImage.addEventListener('error', function() {
                    this.style.display = 'none';
                    const placeholder = this.parentElement.querySelector('.menu-image-placeholder');
                    if (placeholder) {
                        placeholder.style.display = 'flex';
                    }
                });
            }
        });
    }

    // 메뉴 상세보기 함수
    window.viewMenuDetail = function(menuId, storeId, isPublicView = false) {
        const baseUrl = isPublicView ? '/stores' : '/menu';
        const url = `${baseUrl}/${storeId}/menu/${menuId}/`;
        window.location.href = url;
    };

    // 메뉴 수정 함수
    window.editMenu = function(menuId, storeId) {
        const url = `/menu/${storeId}/${menuId}/edit/`;
        window.location.href = url;
    };

    // 메뉴 관리 함수
    window.manageMenu = function(menuId, storeId) {
        const url = `/menu/${storeId}/${menuId}/manage/`;
        window.location.href = url;
    };

    // 메뉴 삭제 함수
    window.deleteMenu = function(menuId, menuName, storeId) {
        if (confirm(`"${menuName}" 메뉴를 정말 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
            fetch(`/menu/${storeId}/${menuId}/delete/`, {
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
                    // 메뉴 카드 제거 애니메이션
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

    // 일시품절 토글 함수 (전역으로 노출)
    window.toggleTemporaryOutOfStock = function(menuId, menuName) {
        const menuCard = document.querySelector(`[data-menu-id="${menuId}"]`);
        const button = document.querySelector(`button[onclick*="${menuId}"]`);
        
        if (!button) return;
        
        const isCurrentlyOutOfStock = button.textContent.includes('해제');
        const action = isCurrentlyOutOfStock ? '해제' : '설정';
        
        if (confirm(`"${menuName}" 메뉴를 일시품절 ${action}하시겠습니까?`)) {
            const url = `/menu/${getStoreIdFromUrl()}/${menuId}/toggle-temporary-out-of-stock/`;
            
            // 버튼 비활성화
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>처리중...';
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message, 'success');
                    // 페이지 새로고침 대신 동적 업데이트
                    updateMenuCardStatus(menuCard, !isCurrentlyOutOfStock);
                } else {
                    showNotification('오류가 발생했습니다: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('네트워크 오류가 발생했습니다.', 'error');
            })
            .finally(() => {
                // 버튼 복원
                button.disabled = false;
                updateToggleButton(button, !isCurrentlyOutOfStock);
            });
        }
    };

    // 장바구니 추가 함수
    window.addToCart = function(menuId, menuName, storeId) {
        if (confirm(`"${menuName}" 메뉴를 장바구니에 추가하시겠습니까?`)) {
            fetch(`/menu/${storeId}/${menuId}/add-to-cart/`, {
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

    // 도우미 함수들
    function updateMenuCardStatus(menuCard, isOutOfStock) {
        if (!menuCard) return;

        const statusTag = menuCard.querySelector('.menu-tag.out-of-stock');
        const statusText = menuCard.querySelector('.menu-status-text');
        const viewButton = menuCard.querySelector('.menu-btn-view');

        if (isOutOfStock) {
            // 일시품절 상태로 변경
            if (!statusTag) {
                const tagsContainer = menuCard.querySelector('.menu-tags');
                const newTag = document.createElement('div');
                newTag.className = 'menu-tag out-of-stock';
                newTag.textContent = '일시품절';
                tagsContainer.appendChild(newTag);
            }

            if (statusText) {
                statusText.textContent = '일시 품절';
                statusText.className = 'menu-status-text out-of-stock';
            }

            if (viewButton) {
                viewButton.className = 'menu-btn menu-btn-disabled out-of-stock';
                viewButton.innerHTML = '<i class="fas fa-pause mr-1"></i>일시품절';
                viewButton.disabled = true;
            }
        } else {
            // 정상 상태로 변경
            if (statusTag) {
                statusTag.remove();
            }

            if (statusText) {
                statusText.textContent = '주문 가능';
                statusText.className = 'menu-status-text available';
            }

            if (viewButton) {
                viewButton.className = 'menu-btn menu-btn-view';
                viewButton.innerHTML = '<i class="fas fa-eye mr-1"></i>메뉴보기';
                viewButton.disabled = false;
            }
        }
    }

    function updateToggleButton(button, isOutOfStock) {
        if (isOutOfStock) {
            button.className = button.className.replace('inactive', 'active');
            button.innerHTML = '<i class="fas fa-play mr-1"></i><span>일시품절 해제</span>';
        } else {
            button.className = button.className.replace('active', 'inactive');
            button.innerHTML = '<i class="fas fa-pause mr-1"></i><span>일시품절</span>';
        }
    }

    function getStoreIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[2]; // /menu/{store_id}/... 형태에서 store_id 추출
    }

    function checkEmptyState() {
        const visibleCards = Array.from(menuCards).filter(card => 
            card.style.display !== 'none' && card.style.opacity !== '0'
        );

        if (visibleCards.length === 0) {
            const emptyState = document.querySelector('.menu-empty-state');
            if (!emptyState) {
                const emptyStateHtml = `
                    <div class="menu-empty-state">
                        <div class="menu-empty-icon">
                            <i class="fas fa-utensils"></i>
                        </div>
                        <h3 class="menu-empty-title">메뉴가 없습니다</h3>
                        <p class="menu-empty-description">등록된 메뉴가 없습니다.</p>
                    </div>
                `;
                if (menuGrid) {
                    menuGrid.insertAdjacentHTML('afterend', emptyStateHtml);
                }
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
        notification.className = `notification fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // 애니메이션
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        }, 10);

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
            const countMatch = cartButton.textContent.match(/\((\d+)\)/);
            if (countMatch) {
                cartButton.textContent = cartButton.textContent.replace(/\(\d+\)/, `(${count})`);
            }
        }
    }

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
    }

    // 이미지 지연 로딩
    function setupLazyLoading() {
        const images = document.querySelectorAll('.menu-image[data-src]');
        
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // 초기화
    setupLazyLoading();
    checkEmptyState();
});

// 키보드 네비게이션
document.addEventListener('keydown', function(e) {
    if (e.target.closest('.menu-card')) {
        const cards = Array.from(document.querySelectorAll('.menu-card'));
        const currentIndex = cards.indexOf(e.target.closest('.menu-card'));
        
        let nextIndex;
        switch(e.key) {
            case 'ArrowRight':
                nextIndex = (currentIndex + 1) % cards.length;
                break;
            case 'ArrowLeft':
                nextIndex = (currentIndex - 1 + cards.length) % cards.length;
                break;
            case 'ArrowDown':
                nextIndex = Math.min(currentIndex + 4, cards.length - 1);
                break;
            case 'ArrowUp':
                nextIndex = Math.max(currentIndex - 4, 0);
                break;
            default:
                return;
        }
        
        if (nextIndex !== undefined) {
            cards[nextIndex].focus();
            e.preventDefault();
        }
    }
}); 