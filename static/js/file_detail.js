// file_detail.js - 파일 상세 페이지를 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const downloadButton = document.querySelector('.download-button');
    const purchaseButton = document.querySelector('.purchase-button');
    const previewImage = document.querySelector('.preview-image');
    const descriptionContent = document.querySelector('.markdown-content');
    const shareButtons = document.querySelectorAll('.share-button');
    const favoriteButton = document.getElementById('favorite-button');
    
    // 이미지 라이트박스 기능
    if (previewImage) {
        previewImage.addEventListener('click', function() {
            createLightbox(this.src, this.alt);
        });
        
        // 커서 스타일 변경
        previewImage.style.cursor = 'zoom-in';
    }
    
    // 라이트박스 생성 함수
    function createLightbox(imageSrc, imageAlt) {
        const lightbox = document.createElement('div');
        lightbox.className = 'fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4';
        lightbox.innerHTML = `
            <img src="${imageSrc}" alt="${imageAlt}" class="max-w-full max-h-full object-contain">
            <button class="absolute top-4 right-4 text-white text-3xl hover:text-gray-300">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // 클릭으로 닫기
        lightbox.addEventListener('click', function(e) {
            if (e.target === lightbox || e.target.closest('button')) {
                document.body.removeChild(lightbox);
            }
        });
        
        // ESC 키로 닫기
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                document.body.removeChild(lightbox);
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
        
        document.body.appendChild(lightbox);
    }
    
    // 마크다운 내용 렌더링
    if (descriptionContent && typeof marked !== 'undefined') {
        const markdownText = descriptionContent.dataset.markdown;
        if (markdownText) {
            // marked 설정
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false
            });
            
            descriptionContent.innerHTML = marked.parse(markdownText);
            
            // 렌더링된 이미지에 라이트박스 추가
            const renderedImages = descriptionContent.querySelectorAll('img');
            renderedImages.forEach(img => {
                img.style.cursor = 'zoom-in';
                img.addEventListener('click', function() {
                    createLightbox(this.src, this.alt);
                });
            });
        }
    }
    
    // 구매/다운로드 버튼 상태 관리
    if (purchaseButton) {
        purchaseButton.addEventListener('click', function(e) {
            // 로그인 체크
            if (this.href.includes('login')) {
                e.preventDefault();
                const currentUrl = window.location.href;
                window.location.href = this.href + '?next=' + encodeURIComponent(currentUrl);
            }
        });
    }
    
    if (downloadButton) {
        downloadButton.addEventListener('click', function(e) {
            // 다운로드 시작 표시
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>다운로드 준비 중...';
            
            setTimeout(() => {
                this.innerHTML = originalText;
                showNotification('다운로드가 시작되었습니다.', 'success');
            }, 1000);
        });
    }
    
    // 공유 기능
    shareButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const platform = this.dataset.platform;
            const url = window.location.href;
            const title = document.querySelector('h1').textContent;
            
            shareContent(platform, url, title);
        });
    });
    
    // 공유 함수
    function shareContent(platform, url, title) {
        let shareUrl = '';
        
        switch(platform) {
            case 'twitter':
                shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`;
                break;
            case 'facebook':
                shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
                break;
            case 'telegram':
                shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;
                break;
            case 'whatsapp':
                shareUrl = `https://wa.me/?text=${encodeURIComponent(title + ' ' + url)}`;
                break;
            case 'copy':
                copyToClipboard(url);
                return;
        }
        
        if (shareUrl) {
            window.open(shareUrl, '_blank', 'width=600,height=400');
        }
    }
    
    // 클립보드 복사
    function copyToClipboard(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        
        try {
            textarea.select();
            document.execCommand('copy');
            showNotification('링크가 복사되었습니다.', 'success');
        } catch (err) {
            showNotification('복사에 실패했습니다.', 'error');
        } finally {
            document.body.removeChild(textarea);
        }
    }
    
    // 즐겨찾기 기능
    if (favoriteButton) {
        // 로컬 스토리지에서 즐겨찾기 상태 확인
        const fileId = favoriteButton.dataset.fileId;
        const favorites = JSON.parse(localStorage.getItem('fileFavorites') || '[]');
        
        if (favorites.includes(fileId)) {
            favoriteButton.classList.add('favorited');
            favoriteButton.innerHTML = '<i class="fas fa-heart text-red-500"></i>';
        }
        
        favoriteButton.addEventListener('click', function() {
            const favorites = JSON.parse(localStorage.getItem('fileFavorites') || '[]');
            const index = favorites.indexOf(fileId);
            
            if (index === -1) {
                // 즐겨찾기 추가
                favorites.push(fileId);
                this.classList.add('favorited');
                this.innerHTML = '<i class="fas fa-heart text-red-500"></i>';
                showNotification('즐겨찾기에 추가되었습니다.', 'success');
            } else {
                // 즐겨찾기 제거
                favorites.splice(index, 1);
                this.classList.remove('favorited');
                this.innerHTML = '<i class="far fa-heart"></i>';
                showNotification('즐겨찾기에서 제거되었습니다.', 'info');
            }
            
            localStorage.setItem('fileFavorites', JSON.stringify(favorites));
        });
    }
    
    // 가격 변동 알림 (할인 종료 시간)
    const discountEndElement = document.querySelector('[data-discount-end]');
    if (discountEndElement) {
        const discountEnd = new Date(discountEndElement.dataset.discountEnd);
        
        function updateDiscountTimer() {
            const now = new Date();
            const remaining = discountEnd - now;
            
            if (remaining <= 0) {
                discountEndElement.innerHTML = '<span class="text-red-500">할인이 종료되었습니다.</span>';
                location.reload(); // 페이지 새로고침으로 가격 업데이트
                return;
            }
            
            const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
            const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
            
            let timeString = '할인 종료까지: ';
            if (days > 0) timeString += `${days}일 `;
            timeString += `${hours}시간 ${minutes}분`;
            
            discountEndElement.textContent = timeString;
            
            // 1시간 미만 남았을 때 강조
            if (remaining < 60 * 60 * 1000) {
                discountEndElement.classList.add('text-red-500', 'font-bold', 'animate-pulse');
            }
        }
        
        updateDiscountTimer();
        setInterval(updateDiscountTimer, 60000); // 1분마다 업데이트
    }
    
    // 알림 표시 함수
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed bottom-4 right-4 px-6 py-4 rounded-lg shadow-lg max-w-md animate-slide-in z-50`;
        
        const colors = {
            success: 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800',
            error: 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800',
            info: 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-800'
        };
        
        notification.className += ' ' + colors[type];
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-3"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('animate-slide-out');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    // 파일 정보 툴팁
    const infoTooltips = document.querySelectorAll('[data-tooltip]');
    infoTooltips.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute z-10 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg';
            tooltip.textContent = this.dataset.tooltip;
            
            // 위치 계산
            const rect = this.getBoundingClientRect();
            tooltip.style.top = `${rect.top - 40}px`;
            tooltip.style.left = `${rect.left + rect.width / 2}px`;
            tooltip.style.transform = 'translateX(-50%)';
            
            document.body.appendChild(tooltip);
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                document.body.removeChild(this._tooltip);
                delete this._tooltip;
            }
        });
    });
    
    // 스크롤 시 구매 버튼 고정
    const stickyPurchaseSection = document.querySelector('.sticky');
    if (stickyPurchaseSection) {
        let lastScrollTop = 0;
        
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            if (scrollTop > lastScrollTop && scrollTop > 200) {
                // 스크롤 다운
                stickyPurchaseSection.style.transform = 'translateY(-100%)';
            } else {
                // 스크롤 업
                stickyPurchaseSection.style.transform = 'translateY(0)';
            }
            
            lastScrollTop = scrollTop;
        });
    }
});

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slide-in {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slide-out {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .animate-slide-in {
        animation: slide-in 0.3s ease-out;
    }
    
    .animate-slide-out {
        animation: slide-out 0.3s ease-in;
    }
    
    .favorited {
        animation: heartBeat 0.3s ease-in-out;
    }
    
    @keyframes heartBeat {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.2); }
    }
`;
document.head.appendChild(style);