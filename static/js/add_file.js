// add_file.js - 파일 추가 기능을 위한 JavaScript

// EasyMDE 에디터 변수들
let descriptionEditor;
let purchaseMessageEditor;

// 현재 선택된 가격 타입 가져오기 (전역 함수로 선언)
function getSelectedPriceType() {
    const selectedRadio = document.querySelector('input[name="price_display"]:checked');
    return selectedRadio ? selectedRadio.value : 'free';
}

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const satsPriceSection = document.getElementById('sats-price-section');
    const krwPriceSection = document.getElementById('krw-price-section');
    const fileInput = document.getElementById('id_file');
    const previewImageInput = document.getElementById('id_preview_image');
    
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
                         'unordered-list', 'ordered-list', '|', 'link', 'image', 'quote', 'code'],
                placeholder: '파일에 대한 자세한 설명을 마크다운 형식으로 작성하세요',
                autosave: {
                    enabled: true,
                    uniqueId: "file_description",
                    delay: 1000,
                }
            });
        }
        
        // 구매완료 메시지 에디터
        const purchaseMessageTextarea = document.getElementById('id_purchase_message');
        if (purchaseMessageTextarea && typeof EasyMDE !== 'undefined') {
            purchaseMessageEditor = new EasyMDE({
                element: purchaseMessageTextarea,
                spellChecker: false,
                toolbar: ['bold', 'italic', 'strikethrough', '|', 'heading-1', 'heading-2', 'heading-3', '|', 
                         'unordered-list', 'ordered-list', '|', 'link', 'image', 'quote', 'code'],
                placeholder: '구매 완료 후 보여줄 메시지를 작성하세요',
                autosave: {
                    enabled: true,
                    uniqueId: "file_purchase_message",
                    delay: 1000,
                }
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


    // 파일 입력 검증
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && !validateFileSize(file)) {
                e.target.value = '';
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
                }
            }
        });
    }

    // 폼 제출 전 검증
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // 가격 검증
            const selectedPriceType = getSelectedPriceType();
            if (selectedPriceType === 'sats') {
                const priceInput = document.getElementById('id_price');
                if (priceInput && (!priceInput.value || priceInput.value <= 0)) {
                    alert('사토시 가격을 입력해주세요.');
                    e.preventDefault();
                    return;
                }
            } else if (selectedPriceType === 'krw') {
                const priceKrwInput = document.getElementById('id_price_krw');
                if (priceKrwInput && (!priceKrwInput.value || priceKrwInput.value <= 0)) {
                    alert('원화 가격을 입력해주세요.');
                    e.preventDefault();
                    return;
                }
            }

        });
    }

    // selectPriceType 함수가 템플릿에 정의되어 있으므로 중복 제거
});