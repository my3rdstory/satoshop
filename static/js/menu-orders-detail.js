// 메뉴별 판매 현황 상세 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeMenuOrdersDetail();
});

function initializeMenuOrdersDetail() {
    // 통계 카드 애니메이션
    animateStatCards();
    
    // 테이블 기능 초기화
    initializeTable();
    
    // 페이지네이션 처리
    setupPagination();
    
    // 반응형 테이블 처리
    handleResponsiveTable();
    
    // 키보드 단축키
    setupKeyboardShortcuts();
}

// 통계 카드 애니메이션
function animateStatCards() {
    const statCards = document.querySelectorAll('.stat-card, .text-center.p-4');
    
    statCards.forEach((card, index) => {
        // 카드 등장 애니메이션
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
            
            // 숫자 카운트업 애니메이션
            const numberElement = card.querySelector('.text-2xl');
            if (numberElement) {
                const finalNumber = parseInt(numberElement.textContent.replace(/,/g, ''));
                if (!isNaN(finalNumber)) {
                    animateNumber(numberElement, finalNumber, 1000);
                }
            }
        }, index * 150);
    });
}

// 숫자 카운트업 애니메이션
function animateNumber(element, finalNumber, duration) {
    const startNumber = 0;
    const startTime = Date.now();
    
    function updateNumber() {
        const currentTime = Date.now();
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // easeOutQuart 이징 함수
        const easeProgress = 1 - Math.pow(1 - progress, 4);
        const currentNumber = Math.floor(startNumber + (finalNumber - startNumber) * easeProgress);
        
        element.textContent = currentNumber.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        } else {
            element.textContent = finalNumber.toLocaleString();
        }
    }
    
    updateNumber();
}

// 테이블 기능 초기화
function initializeTable() {
    // 테이블 행 호버 효과
    setupTableRowHovers();
    
    // 옵션 표시 토글
    setupOptionToggle();
}

// 테이블 행 호버 효과
function setupTableRowHovers() {
    const tableRows = document.querySelectorAll('table tbody tr');
    
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.01)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

// 옵션 표시 토글
function setupOptionToggle() {
    const optionCells = document.querySelectorAll('.text-sm.text-gray-600');
    
    optionCells.forEach(cell => {
        if (cell.children.length > 3) {
            // 옵션이 많은 경우 접기/펼치기 기능 추가
            const options = Array.from(cell.children);
            const visibleOptions = options.slice(0, 3);
            const hiddenOptions = options.slice(3);
            
            // 숨겨진 옵션들 숨기기
            hiddenOptions.forEach(option => {
                option.style.display = 'none';
            });
            
            // 더보기 버튼 추가
            const toggleButton = document.createElement('button');
            toggleButton.className = 'text-blue-600 hover:text-blue-800 text-sm mt-1';
            toggleButton.textContent = `+${hiddenOptions.length}개 더보기`;
            
            toggleButton.addEventListener('click', function(e) {
                e.stopPropagation();
                const isExpanded = this.textContent.includes('접기');
                
                hiddenOptions.forEach(option => {
                    option.style.display = isExpanded ? 'none' : 'block';
                });
                
                this.textContent = isExpanded 
                    ? `+${hiddenOptions.length}개 더보기`
                    : '접기';
            });
            
            cell.appendChild(toggleButton);
        }
    });
}

// 페이지네이션 처리
function setupPagination() {
    const paginationLinks = document.querySelectorAll('nav a[href*="page="]');
    
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 로딩 상태 표시
            showTableLoading();
        });
    });
}

// 테이블 로딩 상태 표시
function showTableLoading() {
    const tbody = document.querySelector('table tbody');
    if (tbody) {
        tbody.innerHTML = '';
        
        // 로딩 행 생성
        for (let i = 0; i < 5; i++) {
            const loadingRow = document.createElement('tr');
            loadingRow.innerHTML = `
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
                <td><div class="h-4 bg-gray-200 dark:bg-gray-600 rounded loading-skeleton"></div></td>
            `;
            tbody.appendChild(loadingRow);
        }
    }
}

// 반응형 테이블 처리
function handleResponsiveTable() {
    const container = document.querySelector('.overflow-x-auto');
    
    if (container) {
        // 스크롤 그림자 효과
        container.addEventListener('scroll', function() {
            const scrollLeft = this.scrollLeft;
            const scrollWidth = this.scrollWidth;
            const clientWidth = this.clientWidth;
            
            // 왼쪽 그림자
            if (scrollLeft > 0) {
                this.classList.add('scroll-shadow-left');
            } else {
                this.classList.remove('scroll-shadow-left');
            }
            
            // 오른쪽 그림자
            if (scrollLeft < scrollWidth - clientWidth) {
                this.classList.add('scroll-shadow-right');
            } else {
                this.classList.remove('scroll-shadow-right');
            }
        });
        
        // 초기 그림자 상태 설정
        container.dispatchEvent(new Event('scroll'));
    }
    
    // 윈도우 리사이즈 시 테이블 조정
    window.addEventListener('resize', debounce(function() {
        adjustTableForScreenSize();
    }, 250));
    
    adjustTableForScreenSize();
}

// 화면 크기에 따른 테이블 조정
function adjustTableForScreenSize() {
    const table = document.querySelector('table');
    const screenWidth = window.innerWidth;
    
    if (table) {
        if (screenWidth < 768) {
            // 모바일에서는 일부 컬럼 숨기기
            hideTableColumns([3]); // 옵션가격 컬럼
        } else {
            // 데스크톱에서는 모든 컬럼 표시
            showTableColumns([3]);
        }
    }
}

// 테이블 컬럼 숨기기
function hideTableColumns(columnIndexes) {
    columnIndexes.forEach(index => {
        // 헤더 숨기기
        const header = document.querySelector(`table th:nth-child(${index + 1})`);
        if (header) header.style.display = 'none';
        
        // 데이터 셀 숨기기
        const cells = document.querySelectorAll(`table td:nth-child(${index + 1})`);
        cells.forEach(cell => cell.style.display = 'none');
    });
}

// 테이블 컬럼 표시
function showTableColumns(columnIndexes) {
    columnIndexes.forEach(index => {
        // 헤더 표시
        const header = document.querySelector(`table th:nth-child(${index + 1})`);
        if (header) header.style.display = '';
        
        // 데이터 셀 표시
        const cells = document.querySelectorAll(`table td:nth-child(${index + 1})`);
        cells.forEach(cell => cell.style.display = '');
    });
}

// 키보드 단축키 설정
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // ESC: 메뉴 판매 현황으로 돌아가기
        if (e.key === 'Escape') {
            goBackToMenuOrders();
        }
        
        // Ctrl/Cmd + R: 새로고침
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            refreshPage();
        }
    });
}

// 메뉴 판매 현황으로 돌아가기
function goBackToMenuOrders() {
    const storeId = window.location.pathname.split('/')[2];
    window.location.href = `/menu/${storeId}/orders/`;
}

// 페이지 새로고침
function refreshPage() {
    window.location.reload();
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

// 에러 처리
function handleError(error) {
    console.error('Menu Orders Detail Error:', error);
    
    const container = document.querySelector('.max-w-7xl');
    if (container) {
        const errorHtml = `
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 mb-8">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <i class="fas fa-exclamation-triangle text-red-600 dark:text-red-400 text-xl"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-red-800 dark:text-red-200 font-semibold">데이터 로드 중 오류가 발생했습니다</h3>
                        <p class="text-red-700 dark:text-red-300 text-sm mt-1">${error.message || '알 수 없는 오류입니다.'}</p>
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

// 로딩 스켈레톤 CSS 추가
const loadingSkeletonCSS = `
.loading-skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
}

.dark .loading-skeleton {
    background: linear-gradient(90deg, #374151 25%, #4b5563 50%, #374151 75%);
    background-size: 200% 100%;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.scroll-shadow-left {
    box-shadow: inset 10px 0 8px -8px rgba(0, 0, 0, 0.15);
}

.scroll-shadow-right {
    box-shadow: inset -10px 0 8px -8px rgba(0, 0, 0, 0.15);
}

.scroll-shadow-left.scroll-shadow-right {
    box-shadow: inset 10px 0 8px -8px rgba(0, 0, 0, 0.15), inset -10px 0 8px -8px rgba(0, 0, 0, 0.15);
}
`;

// CSS 동적 추가
if (!document.getElementById('menu-orders-detail-dynamic-css')) {
    const style = document.createElement('style');
    style.id = 'menu-orders-detail-dynamic-css';
    style.textContent = loadingSkeletonCSS;
    document.head.appendChild(style);
} 