document.addEventListener('DOMContentLoaded', function() {
    // 게임 카드 클릭 이벤트
    const gameCards = document.querySelectorAll('.retro-game-card');
    
    gameCards.forEach(card => {
        card.addEventListener('click', function(e) {
            if (e.target.tagName !== 'A' && !e.target.closest('.start-button')) {
                const link = card.querySelector('a');
                if (link) {
                    // 클릭 사운드 효과 (실제로는 소리 없음, 시각 효과만)
                    card.style.animation = 'flash 0.2s';
                    setTimeout(() => {
                        card.style.animation = '';
                        window.open(link.href, '_blank');
                    }, 200);
                }
            }
        });
        
        // 호버 시 글리치 효과
        card.addEventListener('mouseenter', function() {
            const title = card.querySelector('.game-title');
            if (title) {
                title.style.animation = 'glitch 0.3s';
                setTimeout(() => {
                    title.style.animation = '';
                }, 300);
            }
        });
    });
    
    // 랜덤 글리치 효과
    setInterval(() => {
        const titles = document.querySelectorAll('.game-title');
        if (titles.length > 0) {
            const randomTitle = titles[Math.floor(Math.random() * titles.length)];
            randomTitle.style.animation = 'glitch 0.2s';
            setTimeout(() => {
                randomTitle.style.animation = '';
            }, 200);
        }
    }, 5000);
});

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes flash {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    @keyframes glitch {
        0%, 100% { 
            text-shadow: 0 0 10px #0f0; 
        }
        20% { 
            text-shadow: -2px 0 #f00, 2px 0 #00f; 
        }
        40% { 
            text-shadow: 2px 0 #f00, -2px 0 #00f; 
        }
        60% { 
            text-shadow: 0 0 10px #ff0; 
        }
        80% { 
            text-shadow: 0 0 10px #f0f; 
        }
    }
`;
document.head.appendChild(style);