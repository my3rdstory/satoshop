// file_complete.js - 파일 구매 완료 페이지를 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const downloadButton = document.getElementById('download-button');
    const downloadInfo = document.getElementById('download-info');
    const copyButtons = document.querySelectorAll('.copy-button');
    const purchaseMessage = document.querySelector('.purchase-message');
    
    // 다운로드 버튼 클릭 처리
    if (downloadButton) {
        downloadButton.addEventListener('click', function(e) {
            // 다운로드 시작 표시
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>다운로드 준비 중...';
            this.disabled = true;
            
            // 다운로드 완료 후 복구 (실제 다운로드는 href로 처리됨)
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
                
                // 다운로드 완료 메시지 표시
                showDownloadSuccess();
            }, 2000);
        });
    }
    
    // 복사 버튼 기능
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.dataset.copyTarget;
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                copyToClipboard(targetElement.textContent.trim(), this);
            }
        });
    });
    
    // 클립보드 복사 함수
    function copyToClipboard(text, button) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        
        try {
            textarea.select();
            document.execCommand('copy');
            
            // 피드백 표시
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check mr-1"></i>복사됨!';
            button.classList.add('bg-green-500', 'hover:bg-green-600');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('bg-green-500', 'hover:bg-green-600');
            }, 2000);
        } catch (err) {
            console.error('복사 실패:', err);
            alert('복사에 실패했습니다.');
        } finally {
            document.body.removeChild(textarea);
        }
    }
    
    // 다운로드 성공 메시지 표시
    function showDownloadSuccess() {
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed bottom-4 right-4 bg-green-100 dark:bg-green-900 border border-green-400 dark:border-green-700 text-green-700 dark:text-green-200 px-6 py-4 rounded-lg shadow-lg max-w-md animate-slide-in';
        successMessage.innerHTML = `
            <div class="flex items-start">
                <i class="fas fa-check-circle text-green-500 text-xl mr-3 mt-1"></i>
                <div>
                    <p class="font-semibold">다운로드 시작됨</p>
                    <p class="text-sm mt-1">파일이 다운로드 폴더에 저장됩니다.</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(successMessage);
        
        // 5초 후 자동 제거
        setTimeout(() => {
            successMessage.classList.add('animate-slide-out');
            setTimeout(() => {
                document.body.removeChild(successMessage);
            }, 300);
        }, 5000);
    }
    
    // 다운로드 정보 카운트다운 (유효기간이 있는 경우)
    const expiryElement = document.querySelector('[data-expiry-time]');
    if (expiryElement) {
        const expiryTime = new Date(expiryElement.dataset.expiryTime);
        
        function updateCountdown() {
            const now = new Date();
            const remaining = expiryTime - now;
            
            if (remaining <= 0) {
                expiryElement.innerHTML = '<span class="text-red-500">다운로드 기간이 만료되었습니다.</span>';
                if (downloadButton) {
                    downloadButton.disabled = true;
                    downloadButton.classList.add('opacity-50', 'cursor-not-allowed');
                    downloadButton.innerHTML = '<i class="fas fa-times-circle mr-2"></i>다운로드 만료';
                }
                return;
            }
            
            const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
            const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
            
            let timeString = '';
            if (days > 0) timeString += `${days}일 `;
            if (hours > 0) timeString += `${hours}시간 `;
            if (days === 0) timeString += `${minutes}분`;
            
            expiryElement.innerHTML = `다운로드 가능 기간: <span class="font-semibold">${timeString}</span> 남음`;
            
            // 24시간 미만 남았을 때 경고 표시
            if (remaining < 24 * 60 * 60 * 1000) {
                expiryElement.classList.add('text-orange-500', 'dark:text-orange-400');
            }
        }
        
        updateCountdown();
        setInterval(updateCountdown, 60000); // 1분마다 업데이트
    }
    
    // 마크다운 렌더링 (구매 완료 메시지)
    if (purchaseMessage && typeof marked !== 'undefined') {
        const content = purchaseMessage.dataset.markdown;
        if (content) {
            purchaseMessage.innerHTML = marked.parse(content);
        }
    }
    
    // 공유 기능
    const shareButtons = document.querySelectorAll('.share-button');
    shareButtons.forEach(button => {
        button.addEventListener('click', function() {
            const platform = this.dataset.platform;
            const url = window.location.href;
            const title = document.title;
            
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
                case 'copy':
                    copyToClipboard(url, this);
                    return;
            }
            
            if (shareUrl) {
                window.open(shareUrl, '_blank', 'width=600,height=400');
            }
        });
    });
    
    // 인쇄 기능
    const printButton = document.getElementById('print-receipt');
    if (printButton) {
        printButton.addEventListener('click', function() {
            window.print();
        });
    }
    
    // 주문 정보 저장 (로컬 스토리지)
    const orderInfo = {
        orderId: document.querySelector('[data-order-id]')?.dataset.orderId,
        fileName: document.querySelector('[data-file-name]')?.dataset.fileName,
        purchaseDate: new Date().toISOString(),
        downloadUrl: downloadButton?.href
    };
    
    if (orderInfo.orderId) {
        // 기존 주문 목록 가져오기
        const orders = JSON.parse(localStorage.getItem('fileOrders') || '[]');
        
        // 중복 확인
        if (!orders.find(order => order.orderId === orderInfo.orderId)) {
            orders.unshift(orderInfo); // 최신 주문을 앞에 추가
            
            // 최대 50개까지만 저장
            if (orders.length > 50) {
                orders.pop();
            }
            
            localStorage.setItem('fileOrders', JSON.stringify(orders));
        }
    }
    
    // 페이지 떠나기 경고 (다운로드하지 않은 경우)
    let hasDownloaded = false;
    
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            hasDownloaded = true;
        });
    }
    
    window.addEventListener('beforeunload', function(e) {
        if (!hasDownloaded && downloadButton && !downloadButton.disabled) {
            e.preventDefault();
            e.returnValue = '아직 파일을 다운로드하지 않았습니다. 페이지를 떠나시겠습니까?';
        }
    });
});

// CSS 애니메이션 스타일 추가
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
    
    @media print {
        .no-print {
            display: none !important;
        }
        
        .print-only {
            display: block !important;
        }
    }
`;
document.head.appendChild(style);