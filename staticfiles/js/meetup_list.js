// 밋업 목록 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 밋업 카드들 (헤더 제외)
    const meetupCards = document.querySelectorAll('.grid .bg-white.dark\\:bg-gray-800');

    // 카드 호버 효과
    meetupCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('opacity-70')) {
                this.style.transform = 'translateY(-4px)';
                this.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
            }
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });

    // 이미지 로딩 에러 처리
    const meetupImages = document.querySelectorAll('img[alt*="밋업"]');
    meetupImages.forEach(img => {
        img.addEventListener('error', function() {
            const placeholder = document.createElement('div');
            placeholder.className = 'w-full h-full bg-gradient-to-br from-purple-50 to-indigo-50 dark:bg-gray-700 flex flex-col items-center justify-center';
            placeholder.innerHTML = '<i class="fas fa-users text-purple-400 dark:text-purple-300 text-4xl mb-2"></i><span class="text-purple-500 dark:text-purple-400 text-sm">이미지 없음</span>';
            
            this.parentNode.replaceChild(placeholder, this);
        });
    });

    // 반응형 그리드 조정 - Tailwind CSS 클래스 기반
    function adjustGrid() {
        const grid = document.querySelector('.grid.grid-cols-1');
        if (!grid) return;

        // Tailwind CSS 클래스가 이미 반응형 처리를 하므로 
        // 추가적인 JavaScript 조작은 불필요
        // grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 구조 사용
    }

    // 윈도우 리사이즈 시 그리드 조정
    window.addEventListener('resize', adjustGrid);
    
    // 초기 그리드 조정
    adjustGrid();

    // 스크롤 시 카드 애니메이션
    function animateOnScroll() {
        const cards = document.querySelectorAll('.grid .bg-white.dark\\:bg-gray-800');
        const windowHeight = window.innerHeight;
        
        cards.forEach(card => {
            const cardTop = card.getBoundingClientRect().top;
            
            if (cardTop < windowHeight - 100) {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }
        });
    }

    // 초기 카드 상태 설정 및 순차 애니메이션
    meetupCards.forEach((card, index) => {
        if (!card.classList.contains('opacity-70')) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.3s ease';
            
            // 순차적으로 애니메이션
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        }
    });

    // 스크롤 이벤트 리스너
    window.addEventListener('scroll', animateOnScroll);
    
    // 초기 애니메이션 실행
    animateOnScroll();

    // 밋업 검색/필터링 기능
    function filterMeetups(searchTerm) {
        const normalizedQuery = searchTerm.toLowerCase().trim();
        
        meetupCards.forEach(card => {
            const titleElement = card.querySelector('a[class*="text-lg"]');
            const descriptionElement = card.querySelector('p[class*="text-sm"]');
            
            if (titleElement && descriptionElement) {
                const title = titleElement.textContent.toLowerCase();
                const description = descriptionElement.textContent.toLowerCase();
                
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
            }
        });
    }

    // 전역 함수로 노출 (향후 사용용)
    window.filterMeetups = filterMeetups;

    // 버튼 키보드 접근성
    const actionButtons = document.querySelectorAll('button, a');
    actionButtons.forEach(btn => {
        btn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                if (this.tagName === 'BUTTON') {
                    e.preventDefault();
                    this.click();
                }
            }
        });
    });

    // 로딩 상태 처리
    const grid = document.querySelector('.grid.grid-cols-1');
    if (grid && meetupCards.length === 0) {
        const loadingHTML = `
            <div class="col-span-full flex justify-center items-center py-12">
                <div class="text-center">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
                    <p class="text-gray-500 dark:text-gray-400">밋업을 불러오는 중...</p>
                </div>
            </div>
        `;
        grid.innerHTML = loadingHTML;
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

    // 카드 클릭 시 상세 페이지로 이동 (이미지나 제목 클릭 시)
    meetupCards.forEach(card => {
        const imageLink = card.querySelector('a[href*="meetup_detail"]');
        const titleLink = card.querySelector('a[class*="text-lg"]');
        
        if (imageLink && titleLink) {
            card.addEventListener('click', function(e) {
                // 버튼 클릭이 아닌 경우에만 상세 페이지로 이동
                if (!e.target.closest('button') && !e.target.closest('a[class*="bg-"]')) {
                    window.location.href = imageLink.href;
                }
            });
            
            // 카드에 포인터 커서 추가
            card.style.cursor = 'pointer';
        }
    });

    // 가격 표시 포맷팅 (천단위 콤마)
    const priceElements = document.querySelectorAll('[class*="text-purple-600"], [class*="text-purple-400"]');
    priceElements.forEach(priceEl => {
        const text = priceEl.textContent;
        if (text.includes('sats')) {
            const number = text.replace(/[^\d]/g, '');
            if (number) {
                const formatted = parseInt(number).toLocaleString();
                priceEl.textContent = text.replace(number, formatted);
            }
        }
    });

    // 날짜 표시 상대시간으로 변환 (선택사항)
    const dateElements = document.querySelectorAll('[class*="fa-calendar"] + span');
    dateElements.forEach(dateEl => {
        const dateText = dateEl.textContent.trim();
        if (dateText) {
            // 필요시 상대시간 라이브러리 활용
            // 예: moment.js, date-fns 등
        }
    });

}); 