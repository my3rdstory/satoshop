/* 데스크톱 메뉴판 전용 JavaScript */

// 전역 변수
let currentView = 'menu-grid';
let currentCategory = 'all';

// 뷰 전환 함수
function showView(viewName, categoryId = null) {
    // 모든 뷰 숨기기
    document.querySelectorAll('.content-view').forEach(view => {
        view.classList.remove('active');
    });
    
    // 선택된 뷰 보이기
    const targetView = document.getElementById(viewName + '-view');
    if (targetView) {
        targetView.classList.add('active');
        currentView = viewName;
    }
    
    // 카테고리 상태 업데이트
    if (categoryId !== null) {
        currentCategory = categoryId;
        updateCategoryFilter(categoryId);
    }
    
    // 카테고리 아이템 활성화 상태 업데이트
    updateCategoryActiveState(viewName, categoryId);
}

// 카테고리 필터 업데이트
function updateCategoryFilter(categoryId) {
    if (currentView === 'menu-grid') {
        const menuCards = document.querySelectorAll('.menu-card');
        menuCards.forEach(card => {
            if (categoryId === 'all') {
                card.style.display = 'block';
            } else {
                const categories = JSON.parse(card.dataset.categories || '[]');
                card.style.display = categories.includes(parseInt(categoryId)) ? 'block' : 'none';
            }
        });
    }
}

// 카테고리 아이템 활성화 상태 업데이트
function updateCategoryActiveState(viewName, categoryId) {
    document.querySelectorAll('.category-item').forEach(item => {
        item.classList.remove('active');
    });
    
    if (viewName === 'menu-grid') {
        const targetCategory = document.querySelector(`[data-category="${categoryId}"][data-view="menu-grid"]`);
        if (targetCategory) {
            targetCategory.classList.add('active');
        }
    } else {
        const targetView = document.querySelector(`[data-view="${viewName}"]`);
        if (targetView) {
            targetView.classList.add('active');
        }
    }
}

// 메뉴 상세 보기
function showMenuDetail(menuId) {
    const storeId = window.storeId;
    
    // AJAX로 메뉴 상세 정보 로드
    fetch(`/menu/${storeId}/detail/${menuId}/ajax/`)
        .then(response => response.text())
        .then(html => {
            const menuDetailView = document.getElementById('menu-detail-view');
            menuDetailView.innerHTML = html;
            
            // 로드된 HTML 내의 스크립트 실행
            const scripts = menuDetailView.querySelectorAll('script');
            scripts.forEach(oldScript => {
                try {
                    // 새로운 script 엘리먼트 생성하여 실행
                    const newScript = document.createElement('script');
                    newScript.textContent = oldScript.textContent;
                    document.head.appendChild(newScript);
                    
                    // 실행 후 제거
                    setTimeout(() => {
                        if (document.head.contains(newScript)) {
                            document.head.removeChild(newScript);
                        }
                    }, 100);
                } catch (error) {
                    console.error('스크립트 실행 오류:', error);
                }
            });
            
            showView('menu-detail');
        })
        .catch(error => {
            console.error('메뉴 상세 로드 오류:', error);
        });
}

// 메뉴 그리드로 돌아가기
function backToMenuGrid() {
    showView('menu-grid', currentCategory);
}

// 전역 함수들 미리 정의 (AJAX 로드 전까지 임시)
window.addMenuToCart = function() {
    // 메뉴 상세 정보가 아직 로드되지 않았습니다.
};

window.changeQuantity = function(delta) {
    // 메뉴 상세 정보가 아직 로드되지 않았습니다.
};

window.toggleOption = function(element) {
    // 메뉴 상세 정보가 아직 로드되지 않았습니다.
};

window.changeMainImage = function(url) {
    // 메뉴 상세 정보가 아직 로드되지 않았습니다.
};

// 전역 함수들 노출
window.showView = showView;
window.showMenuDetail = showMenuDetail;
window.backToMenuGrid = backToMenuGrid;
window.updateCategoryFilter = updateCategoryFilter;
window.updateCategoryActiveState = updateCategoryActiveState;

// DOM 로드 완료 시 이벤트 바인딩
document.addEventListener('DOMContentLoaded', function() {
    // 카테고리 이벤트
    document.querySelectorAll('.category-item').forEach(item => {
        item.addEventListener('click', function() {
            const viewType = this.dataset.view;
            const categoryId = this.dataset.category;
            
            if (viewType === 'menu-grid') {
                showView('menu-grid', categoryId);
            } else {
                showView(viewType);
            }
        });
    });
    
    // 초기 상태 설정
    showView('menu-grid', 'all');
}); 