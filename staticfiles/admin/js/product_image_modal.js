// 상품 이미지 모달 기능
(function() {
    'use strict';

    // 모달 HTML 생성
    function createModal() {
        const modalHtml = `
            <div id="imageModal" class="image-modal" style="display: none;">
                <div class="image-modal-backdrop" onclick="closeImageModal()"></div>
                <div class="image-modal-content">
                    <div class="image-modal-header">
                        <h3 id="imageModalTitle">이미지 보기</h3>
                        <button type="button" class="image-modal-close" onclick="closeImageModal()">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="image-modal-body">
                        <img id="imageModalImg" src="" alt="">
                    </div>
                    <div class="image-modal-footer">
                        <button type="button" class="button default" onclick="closeImageModal()">닫기</button>
                        <a id="imageModalDownload" href="" target="_blank" class="button" style="background-color: #007cba; color: white;">
                            원본 보기
                        </a>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    // 이미지 모달 표시
    window.showImageModal = function(imageUrl, imageName) {
        // 모달이 없으면 생성
        if (!document.getElementById('imageModal')) {
            createModal();
        }

        const modal = document.getElementById('imageModal');
        const modalImg = document.getElementById('imageModalImg');
        const modalTitle = document.getElementById('imageModalTitle');
        const modalDownload = document.getElementById('imageModalDownload');

        modalImg.src = imageUrl;
        modalImg.alt = imageName;
        modalTitle.textContent = imageName || '이미지 보기';
        modalDownload.href = imageUrl;

        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';

        // ESC 키로 모달 닫기
        document.addEventListener('keydown', handleEscKey);
    };

    // 이미지 모달 닫기
    window.closeImageModal = function() {
        const modal = document.getElementById('imageModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
            document.removeEventListener('keydown', handleEscKey);
        }
    };

    // ESC 키 처리
    function handleEscKey(event) {
        if (event.key === 'Escape') {
            closeImageModal();
        }
    }

    // 이미지 로드 오류 처리
    document.addEventListener('DOMContentLoaded', function() {
        document.addEventListener('error', function(event) {
            if (event.target.id === 'imageModalImg') {
                event.target.alt = '이미지를 로드할 수 없습니다';
                event.target.style.display = 'none';
                const errorMsg = document.createElement('div');
                errorMsg.className = 'image-error';
                errorMsg.textContent = '이미지를 로드할 수 없습니다';
                event.target.parentNode.appendChild(errorMsg);
            }
        }, true);
    });
})(); 