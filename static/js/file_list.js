// file_list.js - 파일 목록 페이지를 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const sortSelect = document.querySelector('select[name="sort"]');
    const fileCards = document.querySelectorAll('.file-card');
    const searchInput = document.getElementById('file-search');
    const filterButtons = document.querySelectorAll('.filter-button');
    const gridViewButton = document.getElementById('grid-view');
    const listViewButton = document.getElementById('list-view');
    const fileContainer = document.querySelector('.grid');
    
    // 정렬 기능
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            // 폼 자동 제출 대신 AJAX로 처리
            const sortValue = this.value;
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('sort', sortValue);
            
            // 부드러운 전환 효과
            fileContainer.style.opacity = '0.5';
            window.location.href = currentUrl.toString();
        });
    }
    
    // 검색 기능
    if (searchInput) {
        let searchTimer;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const searchTerm = this.value.toLowerCase();
            
            searchTimer = setTimeout(() => {
                filterFiles(searchTerm);
            }, 300);
        });
        
        // 검색 초기화 버튼
        const clearButton = document.createElement('button');
        clearButton.className = 'absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600';
        clearButton.innerHTML = '<i class="fas fa-times"></i>';
        clearButton.style.display = 'none';
        
        clearButton.addEventListener('click', function() {
            searchInput.value = '';
            filterFiles('');
            this.style.display = 'none';
        });
        
        searchInput.parentElement.style.position = 'relative';
        searchInput.parentElement.appendChild(clearButton);
        
        searchInput.addEventListener('input', function() {
            clearButton.style.display = this.value ? 'block' : 'none';
        });
    }
    
    // 파일 필터링 함수
    function filterFiles(searchTerm) {
        let visibleCount = 0;
        
        fileCards.forEach(card => {
            const fileName = card.querySelector('h3').textContent.toLowerCase();
            const fileDescription = card.querySelector('.text-gray-600')?.textContent.toLowerCase() || '';
            
            if (fileName.includes(searchTerm) || fileDescription.includes(searchTerm)) {
                card.style.display = '';
                visibleCount++;
                // 페이드 인 효과
                setTimeout(() => {
                    card.style.opacity = '1';
                }, 50);
            } else {
                card.style.opacity = '0';
                setTimeout(() => {
                    card.style.display = 'none';
                }, 300);
            }
        });
        
        // 결과 없음 메시지
        updateNoResultsMessage(visibleCount);
    }
    
    // 결과 없음 메시지 업데이트
    function updateNoResultsMessage(count) {
        let noResultsMsg = document.getElementById('no-results-message');
        
        if (count === 0) {
            if (!noResultsMsg) {
                noResultsMsg = document.createElement('div');
                noResultsMsg.id = 'no-results-message';
                noResultsMsg.className = 'col-span-full text-center py-12';
                noResultsMsg.innerHTML = `
                    <i class="fas fa-search text-6xl text-gray-300 dark:text-gray-600 mb-4"></i>
                    <p class="text-gray-600 dark:text-gray-400">검색 결과가 없습니다.</p>
                `;
                fileContainer.appendChild(noResultsMsg);
            }
        } else if (noResultsMsg) {
            noResultsMsg.remove();
        }
    }
    
    // 필터 버튼 기능
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filterType = this.dataset.filter;
            
            // 활성 상태 토글
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // 필터 적용
            applyFilter(filterType);
        });
    });
    
    // 필터 적용 함수
    function applyFilter(filterType) {
        fileCards.forEach(card => {
            let shouldShow = true;
            
            switch(filterType) {
                case 'free':
                    shouldShow = card.querySelector('.text-green-600') !== null;
                    break;
                case 'discounted':
                    shouldShow = card.querySelector('.bg-red-500') !== null;
                    break;
                case 'limited':
                    shouldShow = card.textContent.includes('한정');
                    break;
                case 'all':
                default:
                    shouldShow = true;
            }
            
            if (shouldShow) {
                card.style.display = '';
                setTimeout(() => {
                    card.style.opacity = '1';
                }, 50);
            } else {
                card.style.opacity = '0';
                setTimeout(() => {
                    card.style.display = 'none';
                }, 300);
            }
        });
    }
    
    // 뷰 모드 전환
    if (gridViewButton && listViewButton) {
        // 저장된 뷰 모드 복원
        const savedView = localStorage.getItem('fileListView') || 'grid';
        if (savedView === 'list') {
            switchToListView();
        }
        
        gridViewButton.addEventListener('click', function() {
            switchToGridView();
            localStorage.setItem('fileListView', 'grid');
        });
        
        listViewButton.addEventListener('click', function() {
            switchToListView();
            localStorage.setItem('fileListView', 'list');
        });
    }
    
    // 그리드 뷰로 전환
    function switchToGridView() {
        fileContainer.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6';
        gridViewButton.classList.add('bg-purple-500', 'text-white');
        gridViewButton.classList.remove('bg-gray-200', 'text-gray-700');
        listViewButton.classList.remove('bg-purple-500', 'text-white');
        listViewButton.classList.add('bg-gray-200', 'text-gray-700');
    }
    
    // 리스트 뷰로 전환
    function switchToListView() {
        fileContainer.className = 'space-y-4';
        listViewButton.classList.add('bg-purple-500', 'text-white');
        listViewButton.classList.remove('bg-gray-200', 'text-gray-700');
        gridViewButton.classList.remove('bg-purple-500', 'text-white');
        gridViewButton.classList.add('bg-gray-200', 'text-gray-700');
        
        // 카드 스타일 조정
        fileCards.forEach(card => {
            card.classList.add('flex', 'items-center', 'space-x-4');
        });
    }
    
    // 무한 스크롤 (페이지네이션 대체)
    let isLoading = false;
    const loadMoreTrigger = document.getElementById('load-more-trigger');
    
    if (loadMoreTrigger) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !isLoading) {
                    loadMoreFiles();
                }
            });
        }, {
            rootMargin: '100px'
        });
        
        observer.observe(loadMoreTrigger);
    }
    
    // 추가 파일 로드
    function loadMoreFiles() {
        if (isLoading) return;
        
        isLoading = true;
        const nextPageLink = document.querySelector('.pagination .next');
        
        if (nextPageLink) {
            // 로딩 표시
            showLoadingSpinner();
            
            fetch(nextPageLink.href)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newFiles = doc.querySelectorAll('.file-card');
                    
                    newFiles.forEach(file => {
                        file.style.opacity = '0';
                        fileContainer.appendChild(file);
                        
                        // 페이드 인 효과
                        setTimeout(() => {
                            file.style.opacity = '1';
                        }, 50);
                    });
                    
                    // 페이지네이션 업데이트
                    const newPagination = doc.querySelector('.pagination');
                    if (newPagination) {
                        document.querySelector('.pagination').innerHTML = newPagination.innerHTML;
                    }
                    
                    hideLoadingSpinner();
                    isLoading = false;
                })
                .catch(error => {
                    console.error('파일 로드 실패:', error);
                    hideLoadingSpinner();
                    isLoading = false;
                });
        }
    }
    
    // 로딩 스피너 표시
    function showLoadingSpinner() {
        const spinner = document.createElement('div');
        spinner.id = 'loading-spinner';
        spinner.className = 'text-center py-8';
        spinner.innerHTML = `
            <i class="fas fa-spinner fa-spin text-3xl text-purple-500"></i>
            <p class="text-gray-600 dark:text-gray-400 mt-2">파일을 불러오는 중...</p>
        `;
        fileContainer.appendChild(spinner);
    }
    
    // 로딩 스피너 숨기기
    function hideLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) {
            spinner.remove();
        }
    }
    
    // 파일 카드 호버 효과 강화
    fileCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 10px 20px rgba(0,0,0,0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
    
    // 가격 정보 포맷팅
    document.querySelectorAll('.text-bitcoin').forEach(element => {
        const price = element.textContent.trim();
        if (price.includes('sats')) {
            element.innerHTML = `<i class="fab fa-bitcoin mr-1"></i>${price}`;
        }
    });
    
    // 툴팁 초기화
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(element => {
        const title = element.getAttribute('title');
        element.removeAttribute('title');
        element.setAttribute('data-tooltip', title);
        
        element.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute z-50 px-2 py-1 text-xs text-white bg-gray-800 rounded shadow-lg';
            tooltip.textContent = this.getAttribute('data-tooltip');
            
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
            tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
            
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                document.body.removeChild(this._tooltip);
                delete this._tooltip;
            }
        });
    });
});

// 스타일 추가
const style = document.createElement('style');
style.textContent = `
    .file-card {
        transition: all 0.3s ease;
    }
    
    .filter-button.active {
        background-color: rgb(168 85 247);
        color: white;
    }
    
    @media (max-width: 768px) {
        .file-card:hover {
            transform: none;
        }
    }
`;
document.head.appendChild(style);