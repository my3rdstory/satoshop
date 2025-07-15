// edit_file.js - 파일 수정 기능을 위한 JavaScript

// EasyMDE 에디터 변수들
let descriptionEditor;
let purchaseMessageEditor;

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const priceDisplay = document.getElementById('id_price_display');
    const satsPriceSection = document.getElementById('sats-price-section');
    const krwPriceSection = document.getElementById('krw-price-section');
    const fileInput = document.getElementById('id_file');
    const previewImageInput = document.getElementById('id_preview_image');
    const removePreviewCheckbox = document.getElementById('id_remove_preview_image');
    const currentPreviewDiv = document.getElementById('current-preview');
    
    // 마크다운 에디터 초기화
    initializeMarkdownEditors();
    
    // Flatpickr 초기화
    if (typeof flatpickr !== 'undefined') {
    }

    // 마크다운 에디터 초기화 함수
    function initializeMarkdownEditors() {
        // 파일 설명 에디터
        const descriptionTextarea = document.getElementById('id_description');
        if (descriptionTextarea && typeof EasyMDE !== 'undefined') {
            descriptionEditor = new EasyMDE({
                element: descriptionTextarea,
                spellChecker: false,
                toolbar: ['bold', 'italic', 'strikethrough', '|', 'heading-1', 'heading-2', 'heading-3', '|', 
                         'unordered-list', 'ordered-list', '|', 'link', 'image', 'quote', 'code', '|',
                         'preview', 'side-by-side', 'fullscreen'],
                placeholder: '파일에 대한 자세한 설명을 마크다운 형식으로 작성하세요',
                autosave: {
                    enabled: true,
                    uniqueId: "file_description_edit",
                    delay: 1000,
                }
            });
            
            // 변경 감지
            descriptionEditor.codemirror.on("change", function() {
                hasChanges = true;
            });
        }
        
        // 구매완료 메시지 에디터
        const purchaseMessageTextarea = document.getElementById('id_purchase_message');
        if (purchaseMessageTextarea && typeof EasyMDE !== 'undefined') {
            purchaseMessageEditor = new EasyMDE({
                element: purchaseMessageTextarea,
                spellChecker: false,
                toolbar: ['bold', 'italic', '|', 'heading-2', 'heading-3', '|', 
                         'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code', '|',
                         'preview', 'side-by-side', 'fullscreen'],
                placeholder: '구매 완료 후 보여줄 메시지를 작성하세요',
                autosave: {
                    enabled: true,
                    uniqueId: "file_purchase_message_edit",
                    delay: 1000,
                }
            });
            
            // 변경 감지
            purchaseMessageEditor.codemirror.on("change", function() {
                hasChanges = true;
            });
        }
    }
    
    // 가격 표시 방식에 따른 입력 필드 표시/숨김
    function updatePriceSections() {
        const value = priceDisplay.value;
        
        if (value === 'free') {
            satsPriceSection.style.display = 'none';
            krwPriceSection.style.display = 'none';
        } else if (value === 'sats') {
            satsPriceSection.style.display = 'block';
            krwPriceSection.style.display = 'none';
        } else if (value === 'krw') {
            satsPriceSection.style.display = 'none';
            krwPriceSection.style.display = 'block';
        }
    }


    // 미리보기 이미지 제거 체크박스 처리
    function handlePreviewRemoval() {
        if (removePreviewCheckbox && currentPreviewDiv) {
            if (removePreviewCheckbox.checked) {
                currentPreviewDiv.style.opacity = '0.5';
                if (previewImageInput) {
                    previewImageInput.disabled = true;
                }
            } else {
                currentPreviewDiv.style.opacity = '1';
                if (previewImageInput) {
                    previewImageInput.disabled = false;
                }
            }
        }
    }

    // 파일 크기 검증
    function validateFileSize(file, maxSizeMB = 100) {
        const maxSize = maxSizeMB * 1024 * 1024; // MB to bytes
        if (file.size > maxSize) {
            alert(`파일 크기가 ${maxSizeMB}MB를 초과합니다. 현재 파일 크기: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
            return false;
        }
        return true;
    }

    // 이미지 파일 검증
    function validateImageFile(file) {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            alert('이미지 파일은 JPG, PNG, GIF, WEBP 형식만 업로드 가능합니다.');
            return false;
        }
        return true;
    }

    // 이벤트 리스너
    if (priceDisplay) {
        priceDisplay.addEventListener('change', updatePriceSections);
        updatePriceSections();
    }


    if (removePreviewCheckbox) {
        removePreviewCheckbox.addEventListener('change', handlePreviewRemoval);
        handlePreviewRemoval();
    }

    // 파일 입력 검증
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                if (!validateFileSize(file)) {
                    e.target.value = '';
                    return;
                }
                
                // 파일 변경 경고
                if (confirm('파일을 변경하면 기존 구매자들도 새 파일을 다운로드하게 됩니다. 계속하시겠습니까?')) {
                    // 파일 정보 표시
                    const fileInfo = document.getElementById('new-file-info');
                    if (fileInfo) {
                        fileInfo.innerHTML = `
                            <div class="mt-2 p-3 bg-blue-50 dark:bg-blue-900 rounded-lg">
                                <p class="text-sm text-blue-700 dark:text-blue-300">
                                    <i class="fas fa-info-circle mr-1"></i>
                                    새 파일: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)
                                </p>
                            </div>
                        `;
                    }
                } else {
                    e.target.value = '';
                }
            }
        });
    }

    // 미리보기 이미지 검증
    if (previewImageInput) {
        previewImageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                if (!validateImageFile(file) || !validateFileSize(file, 10)) {
                    e.target.value = '';
                    return;
                }
                
                // 미리보기 표시
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.getElementById('new-preview-image');
                    if (preview) {
                        preview.innerHTML = `<img src="${e.target.result}" class="max-w-xs rounded-lg shadow-md" alt="새 미리보기">`;
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 변경 사항 추적
    let hasChanges = false;
    const form = document.querySelector('form');
    const originalValues = {};

    if (form) {
        // 원본 값 저장
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            if (input.type !== 'file' && input.type !== 'hidden') {
                originalValues[input.name] = input.type === 'checkbox' ? input.checked : input.value;
            }
        });

        // 변경 감지
        inputs.forEach(input => {
            input.addEventListener('change', function() {
                if (input.type !== 'file' && input.type !== 'hidden') {
                    const currentValue = input.type === 'checkbox' ? input.checked : input.value;
                    if (currentValue !== originalValues[input.name]) {
                        hasChanges = true;
                    }
                }
            });
        });

        // 폼 제출 전 검증
        form.addEventListener('submit', function(e) {
            // 가격 검증
            if (priceDisplay.value === 'sats') {
                const priceInput = document.getElementById('id_price');
                if (priceInput && (!priceInput.value || priceInput.value <= 0)) {
                    alert('사토시 가격을 입력해주세요.');
                    e.preventDefault();
                    return;
                }
            } else if (priceDisplay.value === 'krw') {
                const priceKrwInput = document.getElementById('id_price_krw');
                if (priceKrwInput && (!priceKrwInput.value || priceKrwInput.value <= 0)) {
                    alert('원화 가격을 입력해주세요.');
                    e.preventDefault();
                    return;
                }
            }


            // 제출 시 변경 사항 표시
            if (hasChanges) {
                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>저장 중...';
                }
            }
        });
    }

    // 페이지 떠나기 경고
    window.addEventListener('beforeunload', function(e) {
        if (hasChanges) {
            e.preventDefault();
            e.returnValue = '변경사항이 저장되지 않았습니다. 페이지를 떠나시겠습니까?';
        }
    });

});