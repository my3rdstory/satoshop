// 비동기 주문 내역 로드
async function loadOrders(filterType, startDate = '', endDate = '', page = 1) {
    try {
        // 로딩 표시
        showLoading();
        
        // URL 파라미터 구성
        const params = new URLSearchParams({
            filter: filterType
        });
        
        // 전체 필터일 때만 페이지 파라미터 추가
        if (filterType === 'all') {
            params.append('page', page);
        }
        
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        // 현재 URL에서 store_id와 product_id 추출
        const pathParts = window.location.pathname.split('/');
        const storeId = pathParts[2]; // /orders/{store_id}/...
        const productId = pathParts[4]; // /orders/{store_id}/products/{product_id}/
        
        const requestUrl = `/orders/${storeId}/products/${productId}/orders/?${params.toString()}`;
        
        // AJAX 요청 - 올바른 URL 패턴 사용
        const response = await fetch(requestUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const html = await response.text();
        
        // 전체 페이지를 새로고침하는 방식으로 변경 (더 안전함)
        const parser = new DOMParser();
        const newDoc = parser.parseFromString(html, 'text/html');
        
        // 통계 정보 업데이트
        const newStats = newDoc.querySelector('#filter-stats');
        const currentStats = document.querySelector('#filter-stats');
        
        if (newStats) {
            if (currentStats) {
                currentStats.outerHTML = newStats.outerHTML;
            } else {
                // 통계가 새로 생긴 경우
                const filterForm = document.querySelector('#filter-form').parentNode;
                filterForm.insertAdjacentHTML('beforeend', newStats.outerHTML);
            }
        } else if (currentStats) {
            currentStats.remove();
        }
        
        // 주문 내역 섹션 업데이트
        const newOrdersSection = newDoc.querySelector('#orders-section');
        const currentOrdersSection = document.querySelector('#orders-section');
        
        if (newOrdersSection && currentOrdersSection) {
            currentOrdersSection.outerHTML = newOrdersSection.outerHTML;
            // 새로운 페이지네이션 링크에 이벤트 리스너 재연결
            attachPaginationEvents();
        }
        
        // URL 업데이트 (브라우저 히스토리에 추가하지 않고)
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newUrl);
        
        // CSV 다운로드 링크 업데이트 (URL 변경 후)
        updateCsvDownloadLink();
        
        hideLoading();
        
    } catch (error) {
        console.error('주문 내역 로드 오류:', error);
        alert('주문 내역을 불러오는데 실패했습니다.');
        hideLoading();
    }
}

// 로딩 표시
function showLoading() {
    const loadingHtml = `
        <div id="loading-overlay" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 flex items-center space-x-3">
                <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <span class="text-gray-700 dark:text-gray-300">로딩 중...</span>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', loadingHtml);
}

// 로딩 숨기기
function hideLoading() {
    const loading = document.getElementById('loading-overlay');
    if (loading) {
        loading.remove();
    }
}

// 필터 설정 함수
function setFilter(type) {
    document.getElementById('filter').value = type;
    
    if (type === 'custom') {
        document.getElementById('custom-date-range').classList.remove('hidden');
        updateFilterButtons();
    } else {
        document.getElementById('custom-date-range').classList.add('hidden');
        // 커스텀 날짜 필드 초기화
        document.getElementById('start_date').value = '';
        document.getElementById('end_date').value = '';
        // 비동기 로드
        loadOrders(type);
        updateFilterButtons();
    }
}

// 커스텀 날짜 범위 토글
function toggleCustomDate() {
    const customDateRange = document.getElementById('custom-date-range');
    const isHidden = customDateRange.classList.contains('hidden');
    
    if (isHidden) {
        setFilter('custom');
    } else {
        setFilter('all');
    }
}

// 커스텀 필터 적용
function applyCustomFilter() {
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    
    if (!startDate || !endDate) {
        alert('시작일과 종료일을 모두 입력해주세요.');
        return;
    }
    
    if (startDate > endDate) {
        alert('시작일은 종료일보다 빠를 수 없습니다.');
        return;
    }
    
    document.getElementById('filter').value = 'custom';
    // 비동기 로드
    loadOrders('custom', startDate, endDate);
    updateFilterButtons(); // 이 함수 안에서 updateCsvDownloadLink()도 호출됨
}

// 필터 버튼 스타일 업데이트
function updateFilterButtons() {
    const currentFilter = document.getElementById('filter').value;
    const buttons = document.querySelectorAll('.filter-btn');
    
    buttons.forEach(button => {
        const onclick = button.getAttribute('onclick');
        let buttonType = null;
        
        // setFilter() 형태에서 타입 추출
        const setFilterMatch = onclick.match(/setFilter\('([^']+)'\)/);
        if (setFilterMatch) {
            buttonType = setFilterMatch[1];
        }
        // toggleCustomDate()인 경우 custom으로 처리
        else if (onclick.includes('toggleCustomDate')) {
            buttonType = 'custom';
        }
        
        if (buttonType === currentFilter) {
            button.className = 'filter-btn px-4 py-2 rounded-lg border transition-colors bg-blue-600 text-white border-blue-600';
        } else {
            button.className = 'filter-btn px-4 py-2 rounded-lg border transition-colors bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600';
        }
    });
    
    // CSV 다운로드 링크 업데이트
    updateCsvDownloadLink();
}

// CSV 다운로드 링크를 현재 필터 상태에 맞게 업데이트
function updateCsvDownloadLink() {
    const csvBtn = document.getElementById('csv-download-btn');
    if (!csvBtn) return;
    
    const currentFilter = document.getElementById('filter').value;
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    
    // 현재 URL에서 store_id와 product_id 추출
    const pathParts = window.location.pathname.split('/');
    const storeId = pathParts[2]; // /orders/{store_id}/...
    const productId = pathParts[4]; // /orders/{store_id}/products/{product_id}/
    
    // 기본 URL
    let csvUrl = `/orders/${storeId}/products/${productId}/orders/export/`;
    
    // 파라미터 구성
    const params = new URLSearchParams({
        filter: currentFilter
    });
    
    if (currentFilter === 'custom' && startDate && endDate) {
        params.append('start_date', startDate);
        params.append('end_date', endDate);
    }
    
    // 전체 필터에서 페이지네이션이 있는 경우 현재 페이지 추가
    if (currentFilter === 'all') {
        const urlParams = new URLSearchParams(window.location.search);
        const currentPage = urlParams.get('page');
        if (currentPage) {
            params.append('page', currentPage);
        }
    }
    
    // 최종 URL 설정
    csvBtn.href = csvUrl + '?' + params.toString();
    
    console.log('CSV 다운로드 링크 업데이트:', csvBtn.href);
}

// 페이지네이션 링크 클릭 이벤트 처리
function handlePaginationClick(event) {
    event.preventDefault();
    
    // 클릭된 요소가 링크인지 확인하고, 부모 요소에서 링크 찾기
    let linkElement = event.target;
    if (linkElement.tagName !== 'A') {
        linkElement = linkElement.closest('a');
    }
    
    if (!linkElement || !linkElement.href) {
        console.error('링크 요소를 찾을 수 없습니다:', event.target);
        return;
    }
    
    try {
        const url = new URL(linkElement.href);
        const params = new URLSearchParams(url.search);
        
        const filterType = params.get('filter') || 'this_month';
        const startDate = params.get('start_date') || '';
        const endDate = params.get('end_date') || '';
        const page = params.get('page') || 1;
        
        loadOrders(filterType, startDate, endDate, page);
    } catch (error) {
        console.error('URL 파싱 오류:', error, 'href:', linkElement.href);
    }
}

// 페이지네이션 링크에 이벤트 리스너 추가
function attachPaginationEvents() {
    // 모든 페이지네이션 관련 링크 선택 (navigation 버튼 + 페이지 번호 링크)
    const paginationLinks = document.querySelectorAll('.pagination-link, .pagination-nav');
    paginationLinks.forEach(link => {
        link.removeEventListener('click', handlePaginationClick); // 중복 방지
        link.addEventListener('click', handlePaginationClick);
    });
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    updateFilterButtons(); // 이 함수 안에서 updateCsvDownloadLink()도 호출됨
    attachPaginationEvents();
    
    // 날짜 입력 필드에 엔터키 이벤트 추가
    document.getElementById('start_date').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyCustomFilter();
        }
    });
    
    document.getElementById('end_date').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyCustomFilter();
        }
    });
    
    // 날짜 입력 필드 변경 시에도 CSV 링크 업데이트
    document.getElementById('start_date').addEventListener('change', updateCsvDownloadLink);
    document.getElementById('end_date').addEventListener('change', updateCsvDownloadLink);
}); 