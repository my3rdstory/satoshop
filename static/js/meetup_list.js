// 밋업 목록 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 카테고리 필터 버튼들
    const categoryFilterBtns = document.querySelectorAll('.category-filter-btn');
    const meetupCards = document.querySelectorAll('.meetup-card');

    // 카테고리 필터 기능
    categoryFilterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const categoryId = this.getAttribute('data-category');
            
            // 모든 버튼에서 active 클래스 제거
            categoryFilterBtns.forEach(b => b.classList.remove('active'));
            
            // 클릭된 버튼에 active 클래스 추가
            this.classList.add('active');
            
            // 밋업 카드 필터링
            filterMeetups(categoryId);
        });
    });

    function filterMeetups(categoryId) {
        meetupCards.forEach(card => {
            if (categoryId === 'all') {
                // 모든 밋업 표시
                card.style.display = 'block';
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 10);
            } else {
                // 특정 카테고리만 표시
                const categories = JSON.parse(card.getAttribute('data-categories') || '[]');
                
                if (categories.includes(parseInt(categoryId))) {
                    card.style.display = 'block';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, 10);
                } else {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    setTimeout(() => {
                        card.style.display = 'none';
                    }, 300);
                }
            }
        });
    }

    // 카드 호버 효과 개선
    meetupCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
        });
    });

    // 반응형 그리드 조정
    function adjustGrid() {
        const grid = document.querySelector('.meetup-grid');
        if (!grid) return;

        const containerWidth = grid.offsetWidth;
        const cardMinWidth = 300;
        const gap = 24; // 1.5rem
        
        const columns = Math.floor((containerWidth + gap) / (cardMinWidth + gap));
        const actualColumns = Math.max(1, Math.min(columns, meetupCards.length));
        
        grid.style.gridTemplateColumns = `repeat(${actualColumns}, 1fr)`;
    }

    // 윈도우 리사이즈 시 그리드 조정
    window.addEventListener('resize', adjustGrid);
    
    // 초기 그리드 조정
    adjustGrid();

    // 이미지 로딩 에러 처리
    const meetupImages = document.querySelectorAll('.meetup-image');
    meetupImages.forEach(img => {
        img.addEventListener('error', function() {
            const placeholder = document.createElement('div');
            placeholder.className = 'meetup-image-placeholder';
            placeholder.innerHTML = '<i class="fas fa-users"></i>';
            
            this.parentNode.replaceChild(placeholder, this);
        });
    });

    // 스크롤 시 카드 애니메이션
    function animateOnScroll() {
        const cards = document.querySelectorAll('.meetup-card');
        const windowHeight = window.innerHeight;
        
        cards.forEach(card => {
            const cardTop = card.getBoundingClientRect().top;
            
            if (cardTop < windowHeight - 100) {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }
        });
    }

    // 초기 카드 상태 설정
    meetupCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.3s ease';
        
        // 순차적으로 애니메이션
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // 스크롤 이벤트 리스너
    window.addEventListener('scroll', animateOnScroll);
    
    // 초기 애니메이션 실행
    animateOnScroll();

    // 검색 기능 (향후 추가용)
    function searchMeetups(query) {
        const normalizedQuery = query.toLowerCase().trim();
        
        meetupCards.forEach(card => {
            const title = card.querySelector('.meetup-name').textContent.toLowerCase();
            const description = card.querySelector('.meetup-description').textContent.toLowerCase();
            
            if (title.includes(normalizedQuery) || description.includes(normalizedQuery)) {
                card.style.display = 'block';
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 10);
            } else {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    card.style.display = 'none';
                }, 300);
            }
        });
    }

    // 전역 함수로 노출 (향후 사용용)
    window.searchMeetups = searchMeetups;

    // 카테고리 버튼 키보드 접근성
    categoryFilterBtns.forEach(btn => {
        btn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });

    // 로딩 상태 처리
    const grid = document.querySelector('.meetup-grid');
    if (grid && meetupCards.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full flex justify-center items-center py-12">
                <div class="text-center">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
                    <p class="text-gray-500 dark:text-gray-400">밋업을 불러오는 중...</p>
                </div>
            </div>
        `;
    }

    // 다크모드 토글 감지 (있는 경우)
    const darkModeToggle = document.querySelector('.dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            setTimeout(() => {
                // 다크모드 전환 후 스타일 재조정
                adjustGrid();
            }, 300);
        });
    }
}); 