// 메뉴 디바이스 선택 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 디바이스 카드 요소들 가져오기
    const deviceCards = document.querySelectorAll('.device-card');
    
    // 각 카드에 클릭 이벤트 추가
    deviceCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // 로딩 상태 추가
            this.classList.add('loading');
            
            // 사용자 선택 저장 (추후 자동 리다이렉트를 위해)
            const isDesktop = this.href.includes('/list/');
            localStorage.setItem('preferredMenuView', isDesktop ? 'desktop' : 'mobile');
            
            // 클릭 효과를 위한 짧은 지연
            setTimeout(() => {
                // 기본 동작 (페이지 이동)이 실행되도록 함
            }, 100);
        });
    });
    
    // 키보드 접근성 향상
    deviceCards.forEach(card => {
        card.addEventListener('keydown', function(e) {
            // Enter 또는 Space 키로 선택 가능
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // 페이지 로드 애니메이션
    const header = document.querySelector('.bg-white.dark\\:bg-gray-800');
    if (header) {
        header.style.opacity = '0';
        header.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            header.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            header.style.opacity = '1';
            header.style.transform = 'translateY(0)';
        }, 100);
    }
    
    // 사용자의 기기 타입 감지 및 권장 사항 표시
    function detectDevice() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isTablet = /iPad|Android/i.test(navigator.userAgent) && !/Mobile/i.test(navigator.userAgent);
        
        // 권장 카드에 하이라이트 추가
        if (isMobile && !isTablet) {
            const mobileCard = document.querySelector('a[href*="/m/"]');
            if (mobileCard) {
                mobileCard.classList.add('recommended');
                // 권장 표시 추가
                const badge = document.createElement('span');
                badge.className = 'absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full';
                badge.textContent = '권장';
                mobileCard.appendChild(badge);
            }
        } else {
            const desktopCard = document.querySelector('a[href*="/list/"]');
            if (desktopCard) {
                desktopCard.classList.add('recommended');
                // 권장 표시 추가
                const badge = document.createElement('span');
                badge.className = 'absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full';
                badge.textContent = '권장';
                desktopCard.appendChild(badge);
            }
        }
    }
    
    // 기기 감지 실행
    detectDevice();
    
    // 화면 크기 변경 감지
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            // 권장 배지 제거 후 다시 감지
            document.querySelectorAll('.recommended .absolute').forEach(badge => badge.remove());
            document.querySelectorAll('.recommended').forEach(card => card.classList.remove('recommended'));
            detectDevice();
        }, 250);
    });
});