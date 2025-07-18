// 파일 업로드 드래그 & 드롭 기능
document.addEventListener('DOMContentLoaded', function() {
    // 최대 파일 개수 및 크기 설정
    const MAX_FILES = 1;
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    
    // 파일 목록 관리
    let selectedFiles = [];
    let fileIdCounter = 0;
    
    // DOM 요소 선택
    const fileInput = document.getElementById('id_file');
    const dropZone = createDropZone();
    const fileListContainer = createFileListContainer();
    
    // 기존 파일 입력 요소 숨기고 드롭존으로 대체
    if (fileInput) {
        const fileInputWrapper = fileInput.parentElement;
        fileInput.style.display = 'none';
        fileInput.removeAttribute('required'); // 기존 required 속성 제거
        
        fileInputWrapper.appendChild(dropZone);
        fileInputWrapper.appendChild(fileListContainer);
    }
    
    // 드롭존 생성
    function createDropZone() {
        const dropZone = document.createElement('div');
        dropZone.className = 'file-drop-zone';
        dropZone.innerHTML = `
            <div class="drop-zone-content">
                <i class="fas fa-cloud-upload-alt drop-zone-icon"></i>
                <p class="drop-zone-text">파일을 드래그하여 놓거나 클릭하여 선택하세요</p>
                <p class="drop-zone-subtext">파일 1개, 최대 10MB까지</p>
                <button type="button" class="btn-select-files">파일 선택</button>
            </div>
            <input type="file" id="multi-file-input" multiple style="display: none;" accept="*/*">
        `;
        
        // 클릭 이벤트
        const selectBtn = dropZone.querySelector('.btn-select-files');
        const multiFileInput = dropZone.querySelector('#multi-file-input');
        
        selectBtn.addEventListener('click', () => multiFileInput.click());
        dropZone.addEventListener('click', (e) => {
            if (e.target === dropZone || e.target.classList.contains('drop-zone-content')) {
                multiFileInput.click();
            }
        });
        
        // 파일 선택 이벤트
        multiFileInput.addEventListener('change', (e) => {
            handleFileSelect(e.target.files);
            e.target.value = ''; // 같은 파일 재선택 가능하도록
        });
        
        // 드래그 이벤트
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
        
        return dropZone;
    }
    
    // 파일 목록 컨테이너 생성
    function createFileListContainer() {
        const container = document.createElement('div');
        container.className = 'file-list-container';
        container.style.display = 'none';
        container.innerHTML = `
            <h4 class="file-list-title">선택된 파일 (<span class="file-count">0</span>/${MAX_FILES})</h4>
            <div class="file-list"></div>
        `;
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
        handleFileSelect(files);
    }
    
    // 파일 선택 처리
    function handleFileSelect(files) {
        const fileArray = Array.from(files);
        const availableSlots = MAX_FILES - selectedFiles.length;
        
        if (availableSlots <= 0) {
            alert(`최대 ${MAX_FILES}개의 파일만 업로드할 수 있습니다.`);
            return;
        }
        
        if (fileArray.length > availableSlots) {
            alert(`${availableSlots}개의 파일만 추가할 수 있습니다.`);
            fileArray.splice(availableSlots);
        }
        
        // 파일 검증 및 추가
        fileArray.forEach(file => {
            if (validateFile(file)) {
                addFile(file);
            }
        });
        
        updateFileList();
        updateFormData();
    }
    
    // 파일 유효성 검사
    function validateFile(file) {
        // 크기 검사
        if (file.size > MAX_FILE_SIZE) {
            alert(`"${file.name}" 파일이 10MB를 초과합니다. (${(file.size / 1024 / 1024).toFixed(2)}MB)`);
            return false;
        }
        
        // 중복 검사
        const isDuplicate = selectedFiles.some(f => 
            f.file.name === file.name && f.file.size === file.size
        );
        if (isDuplicate) {
            alert(`"${file.name}" 파일은 이미 추가되었습니다.`);
            return false;
        }
        
        return true;
    }
    
    // 파일 추가
    function addFile(file) {
        const fileId = `file-${fileIdCounter++}`;
        selectedFiles.push({
            id: fileId,
            file: file
        });
    }
    
    // 파일 제거
    function removeFile(fileId) {
        selectedFiles = selectedFiles.filter(f => f.id !== fileId);
        updateFileList();
        updateFormData();
    }
    
    // 파일 목록 업데이트
    function updateFileList() {
        const fileList = fileListContainer.querySelector('.file-list');
        const fileCount = fileListContainer.querySelector('.file-count');
        
        fileCount.textContent = selectedFiles.length;
        
        if (selectedFiles.length === 0) {
            fileListContainer.style.display = 'none';
            fileList.innerHTML = '';
            return;
        }
        
        fileListContainer.style.display = 'block';
        fileList.innerHTML = selectedFiles.map(({id, file}) => `
            <div class="file-item" data-file-id="${id}">
                <div class="file-info">
                    <i class="fas fa-file file-icon"></i>
                    <div class="file-details">
                        <p class="file-name">${escapeHtml(file.name)}</p>
                        <p class="file-size">${formatFileSize(file.size)}</p>
                    </div>
                </div>
                <button type="button" class="btn-remove-file" data-file-id="${id}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
        
        // 제거 버튼 이벤트
        fileList.querySelectorAll('.btn-remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileId = btn.getAttribute('data-file-id');
                removeFile(fileId);
            });
        });
    }
    
    // 폼 데이터 업데이트
    function updateFormData() {
        // 단일 파일만 처리하는 경우 (기본 폼 제출)
        if (selectedFiles.length === 1) {
            const dt = new DataTransfer();
            dt.items.add(selectedFiles[0].file);
            fileInput.files = dt.files;
        } else if (selectedFiles.length === 0) {
            fileInput.value = '';
        }
        // 다중 파일의 경우 AJAX로 처리할 예정
    }
    
    // 유틸리티 함수들
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
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
    
    // 다중 파일 업로드를 위한 폼 제출 오버라이드
    const form = fileInput.closest('form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            // 다중 파일이 선택된 경우
            if (selectedFiles.length > 1) {
                e.preventDefault();
                
                const formData = new FormData(form);
                formData.delete('file'); // 기존 파일 필드 제거
                
                // 다중 파일 추가
                selectedFiles.forEach(({file}) => {
                    formData.append('files[]', file);
                });
                
                // 로딩 표시
                const submitBtn = form.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>파일 업로드 중...';
                
                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // 성공 메시지 표시 후 리다이렉트
                        window.location.href = form.action.replace('/add/', '/manage/');
                    } else {
                        alert(data.error || '파일 업로드 중 오류가 발생했습니다.');
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }
                } catch (error) {
                    console.error('Upload error:', error);
                    alert('파일 업로드 중 오류가 발생했습니다.');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
            // 단일 파일의 경우 기본 폼 제출 동작
        });
    }
});