// 밈 상세 페이지 JavaScript

// 통계 업데이트 함수
async function updateMemeStats(memeId, statType) {
    try {
        const response = await fetch(`/boards/meme/${memeId}/stat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ type: statType })
        });
        
        if (!response.ok) {
            throw new Error('통계 업데이트 실패');
        }
        
        const data = await response.json();
        console.log(`${statType} count updated:`, data.count);
    } catch (error) {
        console.error('통계 업데이트 오류:', error);
    }
}

// CSRF 토큰 가져오기
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 이미지 복사 기능
async function copyMemeImage(imageUrl, title, memeId) {
    try {
        // 이미지를 fetch로 가져오기
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        
        // blob을 image/png로 변환 (더 나은 호환성을 위해)
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        // 이미지 로드 완료를 기다림
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = URL.createObjectURL(blob);
        });
        
        // 캔버스에 이미지 그리기
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        // 캔버스를 blob으로 변환
        const pngBlob = await new Promise(resolve => {
            canvas.toBlob(resolve, 'image/png');
        });
        
        // 클립보드에 이미지 복사
        const item = new ClipboardItem({ 'image/png': pngBlob });
        await navigator.clipboard.write([item]);
        
        // 메모리 정리
        URL.revokeObjectURL(img.src);
        
        // 통계 업데이트
        if (memeId) {
            updateMemeStats(memeId, 'detail_copy');
        }
        
        // 성공 메시지
        showNotification('이미지가 클립보드에 복사되었습니다!', 'success');
    } catch (error) {
        console.error('이미지 복사 실패:', error);
        
        // 대체 방법: 새 탭에서 이미지 열기
        window.open(imageUrl, '_blank');
        showNotification('이미지를 새 탭에서 열었습니다. 직접 복사해주세요.', 'info');
    }
}

// 알림 표시
function showNotification(message, type = 'info') {
    // 기존 알림 제거
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 새 알림 생성
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 3초 후 제거
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 이미지 클릭시 확대
document.addEventListener('DOMContentLoaded', function() {
    const memeImage = document.querySelector('.meme-image');
    
    if (memeImage) {
        memeImage.style.cursor = 'zoom-in';
        
        memeImage.addEventListener('click', function() {
            // 전체화면 모달 생성
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                cursor: zoom-out;
                padding: 2rem;
            `;
            
            const modalImage = document.createElement('img');
            modalImage.src = this.src;
            modalImage.alt = this.alt;
            modalImage.style.cssText = `
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            `;
            
            modal.appendChild(modalImage);
            document.body.appendChild(modal);
            document.body.style.overflow = 'hidden';
            
            // 클릭시 닫기
            modal.addEventListener('click', function() {
                modal.remove();
                document.body.style.overflow = '';
            });
            
            // ESC 키로 닫기
            const handleEsc = function(e) {
                if (e.key === 'Escape') {
                    modal.remove();
                    document.body.style.overflow = '';
                    document.removeEventListener('keydown', handleEsc);
                }
            };
            document.addEventListener('keydown', handleEsc);
        });
    }
});