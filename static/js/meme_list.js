// 밈 갤러리 리스트 JavaScript

// 이미지 복사 기능
async function copyMemeImage(imageUrl, title) {
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
        
        // 성공 메시지
        showNotification('이미지가 클립보드에 복사되었습니다!', 'success');
    } catch (error) {
        console.error('이미지 복사 실패:', error);
        
        // 대체 방법: 새 탭에서 이미지 열기
        window.open(imageUrl, '_blank');
        showNotification('이미지를 새 탭에서 열었습니다. 직접 복사해주세요.', 'info');
    }
}

// 크게보기 모달 표시
function showMemeModal(imageUrl, title, memeId) {
    const modal = document.getElementById('memeModal');
    const modalImage = document.getElementById('modalImage');
    const modalTitle = document.getElementById('modalTitle');
    const modalDetailLink = document.getElementById('modalDetailLink');
    
    modalImage.src = imageUrl;
    modalImage.alt = title;
    modalTitle.textContent = title;
    modalDetailLink.href = `/boards/meme/${memeId}/`;
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

// 크게보기 모달 닫기
function closeMemeModal(event) {
    if (event.target.classList.contains('meme-modal') || 
        event.target.classList.contains('modal-close') ||
        event.target.closest('.modal-close')) {
        const modal = document.getElementById('memeModal');
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// 태그 클라우드 표시
async function showTagCloud() {
    const modal = document.getElementById('tagCloudModal');
    const body = document.getElementById('tagCloudBody');
    
    try {
        const response = await fetch('/boards/meme/tags/');
        const data = await response.json();
        
        // 태그 클라우드 렌더링
        body.innerHTML = '';
        data.tags.forEach(tag => {
            const tagElement = document.createElement('a');
            tagElement.href = tag.url;
            tagElement.className = 'tag-item';
            tagElement.innerHTML = `
                ${tag.name}
                <span class="tag-count">(${tag.count})</span>
            `;
            body.appendChild(tagElement);
        });
        
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    } catch (error) {
        console.error('태그 클라우드 로드 실패:', error);
        showNotification('태그를 불러오는데 실패했습니다.', 'error');
    }
}

// 태그 클라우드 닫기
function closeTagCloud(event) {
    if (event.target.classList.contains('tag-cloud-modal') || 
        event.target.classList.contains('modal-close') ||
        event.target.closest('.modal-close')) {
        const modal = document.getElementById('tagCloudModal');
        modal.classList.remove('show');
        document.body.style.overflow = '';
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
    
    // 스타일 추가
    notification.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // 3초 후 제거
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        const memeModal = document.getElementById('memeModal');
        const tagModal = document.getElementById('tagCloudModal');
        
        if (memeModal.classList.contains('show')) {
            memeModal.classList.remove('show');
            document.body.style.overflow = '';
        }
        
        if (tagModal.classList.contains('show')) {
            tagModal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
});

// 애니메이션 스타일 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);