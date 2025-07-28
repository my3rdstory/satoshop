// 밈 등록/수정 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const dropZoneContent = document.querySelector('.drop-zone-content');
    
    // 드롭존 클릭시 파일 선택
    dropZone.addEventListener('click', function(e) {
        if (!e.target.closest('.remove-image')) {
            imageInput.click();
        }
    });
    
    // 파일 선택시
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleFile(file);
        }
    });
    
    // 드래그 오버
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    // 드래그 떠남
    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });
    
    // 드롭
    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            handleFile(file);
        }
    });
    
    // 클립보드 붙여넣기 이벤트 (Ctrl+V)
    document.addEventListener('paste', function(e) {
        const items = e.clipboardData.items;
        
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            
            // 이미지 타입 체크
            if (item.type.indexOf('image') !== -1) {
                e.preventDefault();
                
                // 클립보드의 이미지를 File 객체로 변환
                const blob = item.getAsFile();
                if (blob) {
                    // 파일명 생성
                    const filename = 'clipboard_' + new Date().getTime() + '.' + blob.type.split('/')[1];
                    const file = new File([blob], filename, { type: blob.type });
                    
                    // 기존 파일 처리 함수 사용
                    handleFile(file);
                }
                break;
            }
        }
    });
    
    // 파일 처리
    function handleFile(file) {
        // 파일 타입 체크
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            alert('JPG, JPEG, PNG, GIF, WebP 파일만 업로드 가능합니다.');
            return;
        }
        
        // 파일 크기 체크 (10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('파일 크기는 10MB를 초과할 수 없습니다.');
            return;
        }
        
        // 미리보기 표시
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            dropZoneContent.classList.add('hidden');
            imagePreview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
        
        // 파일 입력에 설정
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        imageInput.files = dataTransfer.files;
    }
    
    // 이미지 제거
    window.removeImage = function() {
        imageInput.value = '';
        previewImg.src = '';
        dropZoneContent.classList.remove('hidden');
        imagePreview.classList.add('hidden');
    };
    
    // 폼 제출 전 검증
    const form = document.querySelector('.meme-form');
    form.addEventListener('submit', function(e) {
        const submitBtn = form.querySelector('.btn-submit');
        
        // 이미지 필수 체크
        if (!imageInput.files.length) {
            e.preventDefault();
            alert('이미지를 선택해주세요.');
            return;
        }
        
        // 제목 필수 체크
        const titleInput = document.getElementById('id_title');
        if (!titleInput.value.trim()) {
            e.preventDefault();
            alert('제목을 입력해주세요.');
            titleInput.focus();
            return;
        }
        
        // 로딩 상태 표시
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        submitBtn.innerHTML = `
            <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            업로드 중...
        `;
    });
    
    // 태그 입력 개선
    const newTagsInput = document.querySelector('input[name="new_tags"]');
    if (newTagsInput) {
        newTagsInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                // 쉼표 추가
                const value = this.value.trim();
                if (value && !value.endsWith(',')) {
                    this.value = value + ', ';
                }
            }
        });
    }
});

// 애니메이션 스타일 추가
const style = document.createElement('style');
style.textContent = `
    .animate-spin {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
`;
document.head.appendChild(style);