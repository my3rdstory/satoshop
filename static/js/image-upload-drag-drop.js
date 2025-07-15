// 이미지 업로드 드래그 & 드롭 기능
document.addEventListener('DOMContentLoaded', function() {
    // 최대 파일 크기 설정
    const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
    const VALID_IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    
    // DOM 요소 선택
    const previewImageInput = document.getElementById('id_preview_image');
    if (!previewImageInput) return;
    
    const dropZone = createImageDropZone();
    const previewContainer = createPreviewContainer();
    
    // 기존 파일 입력 요소 숨기고 드롭존으로 대체
    const imageInputWrapper = previewImageInput.parentElement;
    previewImageInput.style.display = 'none';
    
    imageInputWrapper.appendChild(dropZone);
    imageInputWrapper.appendChild(previewContainer);
    
    // 드롭존 생성
    function createImageDropZone() {
        const dropZone = document.createElement('div');
        dropZone.className = 'image-drop-zone';
        dropZone.innerHTML = `
            <div class="drop-zone-content">
                <i class="fas fa-image drop-zone-icon"></i>
                <p class="drop-zone-text">커버 이미지를 드래그하여 놓거나 클릭하여 선택하세요</p>
                <p class="drop-zone-subtext">JPG, PNG, GIF, WEBP (최대 10MB)</p>
                <button type="button" class="btn-select-image">이미지 선택</button>
            </div>
        `;
        
        // 클릭 이벤트
        const selectBtn = dropZone.querySelector('.btn-select-image');
        selectBtn.addEventListener('click', () => previewImageInput.click());
        dropZone.addEventListener('click', (e) => {
            if (e.target === dropZone || e.target.classList.contains('drop-zone-content')) {
                previewImageInput.click();
            }
        });
        
        // 파일 선택 이벤트
        previewImageInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleImageSelect(e.target.files[0]);
            }
        });
        
        // 드래그 이벤트
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
        
        return dropZone;
    }
    
    // 미리보기 컨테이너 생성
    function createPreviewContainer() {
        const container = document.createElement('div');
        container.className = 'image-preview-container';
        container.style.display = 'none';
        return container;
    }
    
    // 드래그 오버 처리
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('drag-over');
    }
    
    // 드래그 리브 처리
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        if (e.target === dropZone) {
            dropZone.classList.remove('drag-over');
        }
    }
    
    // 드롭 처리
    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleImageSelect(files[0]);
        }
    }
    
    // 이미지 선택 처리
    function handleImageSelect(file) {
        if (!validateImage(file)) {
            return;
        }
        
        // FileReader로 미리보기 생성
        const reader = new FileReader();
        reader.onload = function(e) {
            showPreview(e.target.result, file.name);
        };
        reader.readAsDataURL(file);
        
        // 실제 파일 입력에 설정
        const dt = new DataTransfer();
        dt.items.add(file);
        previewImageInput.files = dt.files;
    }
    
    // 이미지 유효성 검사
    function validateImage(file) {
        // 파일 타입 검사
        if (!VALID_IMAGE_TYPES.includes(file.type)) {
            alert('이미지 파일은 JPG, PNG, GIF, WEBP 형식만 업로드 가능합니다.');
            return false;
        }
        
        // 크기 검사
        if (file.size > MAX_IMAGE_SIZE) {
            alert(`이미지 크기가 10MB를 초과합니다. (${(file.size / 1024 / 1024).toFixed(2)}MB)`);
            return false;
        }
        
        return true;
    }
    
    // 미리보기 표시
    function showPreview(imageSrc, fileName) {
        previewContainer.innerHTML = `
            <div class="image-preview-item">
                <img src="${imageSrc}" alt="미리보기" class="preview-image">
                <div class="preview-info">
                    <p class="preview-filename">${escapeHtml(fileName)}</p>
                    <button type="button" class="btn-remove-image">
                        <i class="fas fa-times"></i> 제거
                    </button>
                </div>
            </div>
        `;
        previewContainer.style.display = 'block';
        
        // 제거 버튼 이벤트
        const removeBtn = previewContainer.querySelector('.btn-remove-image');
        removeBtn.addEventListener('click', removeImage);
    }
    
    // 이미지 제거
    function removeImage() {
        previewImageInput.value = '';
        previewContainer.innerHTML = '';
        previewContainer.style.display = 'none';
    }
    
    // HTML 이스케이프
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
});