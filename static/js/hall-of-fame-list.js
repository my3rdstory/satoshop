document.addEventListener('DOMContentLoaded', function() {
    // 이미지 로딩 에러 처리만 남김
    document.querySelectorAll('.hall-of-fame-image').forEach(img => {
        img.addEventListener('error', function() {
            this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iI2Y4ZjlmYSIvPjx0ZXh0IHRleHQtYW5jaG9yPSJtaWRkbGUiIHg9IjIwMCIgeT0iMjAwIiBzdHlsZT0iZmlsbDojNmM3NTdkO2ZvbnQtd2VpZ2h0OmJvbGQ7Zm9udC1zaXplOjIwcHg7Zm9udC1mYW1pbHk6QXJpYWwsc2Fucy1zZXJpZiI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+';
        });
    });

    // 비동기 필터링 기능
    initAsyncFiltering();
});

function initAsyncFiltering() {
    const filterTags = document.querySelectorAll('.filter-tag');
    const hallOfFameGrid = document.querySelector('.hall-of-fame-grid');
    let currentYear = '';
    let currentMonth = '';
    
    // 초기 상태 설정
    const activeYearTag = document.querySelector('.filter-group:first-child .filter-tag.active');
    const activeMonthTag = document.querySelector('.filter-group:last-child .filter-tag.active');
    
    if (activeYearTag) {
        const url = new URL(activeYearTag.href);
        currentYear = url.searchParams.get('year') || '';
    }
    if (activeMonthTag) {
        const url = new URL(activeMonthTag.href);
        currentMonth = url.searchParams.get('month') || '';
    }
    
    filterTags.forEach(tag => {
        tag.addEventListener('click', function(e) {
            e.preventDefault();
            
            const url = new URL(this.href);
            const clickedYear = url.searchParams.get('year') || '';
            const clickedMonth = url.searchParams.get('month') || '';
            
            // 년도 필터 클릭
            if (clickedYear !== undefined && this.closest('.filter-group:first-child')) {
                // 년도 태그 활성화
                document.querySelectorAll('.filter-group:first-child .filter-tag').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                currentYear = clickedYear;
                
                // 해당 년도의 월 목록 업데이트
                updateMonthFilters(currentYear);
                
                // 월 선택 초기화 (전체로 설정)
                document.querySelectorAll('.filter-group:last-child .filter-tag').forEach(t => t.classList.remove('active'));
                document.querySelector('.filter-group:last-child .filter-tag[href*="전체"]').classList.add('active');
                currentMonth = '';
            }
            // 월 필터 클릭
            else if (clickedMonth !== undefined && this.closest('.filter-group:last-child')) {
                // 월 태그 활성화
                document.querySelectorAll('.filter-group:last-child .filter-tag').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                currentMonth = clickedMonth;
            }
            
            // 비동기로 데이터 로드
            loadHallOfFameData(currentYear, currentMonth, hallOfFameGrid);
        });
    });
}

function updateMonthFilters(selectedYear) {
    const monthFilterContainer = document.querySelector('.filter-group:last-child .filter-tags');
    
    // 로딩 상태 표시
    monthFilterContainer.innerHTML = '<span class="text-muted">로딩중...</span>';
    
    // 선택된 년도의 월 목록 가져오기
    const params = selectedYear ? `?year=${selectedYear}` : '';
    
    fetch(`/boards/api/hall-of-fame/months/${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let monthsHtml = `
                    <a href="/boards/hall-of-fame/${selectedYear ? '?year=' + selectedYear : ''}" 
                       class="filter-tag active">전체</a>
                `;
                
                data.months.forEach(month => {
                    const href = selectedYear 
                        ? `/boards/hall-of-fame/?year=${selectedYear}&month=${month}`
                        : `/boards/hall-of-fame/?month=${month}`;
                    
                    monthsHtml += `
                        <a href="${href}" class="filter-tag">
                            ${month}월
                        </a>
                    `;
                });
                
                monthFilterContainer.innerHTML = monthsHtml;
                
                // 새로 생성된 월 필터에 이벤트 리스너 추가
                monthFilterContainer.querySelectorAll('.filter-tag').forEach(tag => {
                    tag.addEventListener('click', function(e) {
                        e.preventDefault();
                        
                        const url = new URL(this.href);
                        const clickedMonth = url.searchParams.get('month') || '';
                        
                        // 월 태그 활성화
                        monthFilterContainer.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
                        this.classList.add('active');
                        
                        // 현재 선택된 년도와 함께 데이터 로드
                        const currentYear = document.querySelector('.filter-group:first-child .filter-tag.active');
                        const yearParam = currentYear && currentYear.href.includes('year=') 
                            ? new URL(currentYear.href).searchParams.get('year') 
                            : '';
                        
                        loadHallOfFameData(yearParam, clickedMonth, document.querySelector('.hall-of-fame-grid'));
                    });
                });
                
            } else {
                monthFilterContainer.innerHTML = '<span class="text-danger">월 목록 로드 실패</span>';
            }
        })
        .catch(error => {
            console.error('Error loading months:', error);
            monthFilterContainer.innerHTML = '<span class="text-danger">월 목록 로드 실패</span>';
        });
}

function loadHallOfFameData(year, month, container) {
    // 로딩 상태 표시
    container.innerHTML = '<div class="text-center p-4"><div class="spinner-border" role="status"><span class="sr-only">로딩중...</span></div></div>';
    
    // API 호출
    const params = new URLSearchParams();
    if (year) params.append('year', year);
    if (month) params.append('month', month);
    
    fetch(`/boards/api/hall-of-fame/list/?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                container.innerHTML = data.html;
                
                // 이미지 에러 처리 다시 적용
                container.querySelectorAll('.hall-of-fame-image').forEach(img => {
                    img.addEventListener('error', function() {
                        this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iI2Y4ZjlmYSIvPjx0ZXh0IHRleHQtYW5jaG9yPSJtaWRkbGUiIHg9IjIwMCIgeT0iMjAwIiBzdHlsZT0iZmlsbDojNmM3NTdkO2ZvbnQtd2VpZ2h0OmJvbGQ7Zm9udC1zaXplOjIwcHg7Zm9udC1mYW1pbHk6QXJpYWwsc2Fucy1zZXJpZiI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+';
                    });
                });
            } else {
                container.innerHTML = '<div class="text-center text-danger">데이터 로드 중 오류가 발생했습니다.</div>';
            }
        })
        .catch(error => {
            console.error('Error loading Hall of Fame data:', error);
            container.innerHTML = '<div class="text-center text-danger">데이터 로드 중 오류가 발생했습니다.</div>';
        });
}