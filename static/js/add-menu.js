// 메뉴 추가 폼 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소들
    const menuForm = document.getElementById('menuForm');
    const priceDisplayRadios = document.querySelectorAll('input[name="price_display"]');
    const priceInput = document.getElementById('price');
    const discountedPriceInput = document.getElementById('discounted_price');
    const isDiscountedCheckbox = document.getElementById('is_discounted');
    const discountSection = document.getElementById('discountSection');
    const imageDropArea = document.getElementById('imageDropArea');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const addOptionBtn = document.getElementById('addOptionBtn');
    const optionsContainer = document.getElementById('optionsContainer');

    let selectedImages = [];
    let optionCount = 0;

    // 가격 표시 방식 변경 처리
    priceDisplayRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updatePriceDisplay();
        });
    });

    // 할인 체크박스 처리
    if (isDiscountedCheckbox) {
        isDiscountedCheckbox.addEventListener('change', function() {
            if (this.checked) {
                discountSection.classList.remove('hidden');
            } else {
                discountSection.classList.add('hidden');
                discountedPriceInput.value = '';
            }
        });
    }

    // 가격 입력 시 실시간 환율 변환
    if (priceInput) {
        priceInput.addEventListener('input', function() {
            updateExchangeRate(this.value, 'price');
        });
    }

    if (discountedPriceInput) {
        discountedPriceInput.addEventListener('input', function() {
            updateExchangeRate(this.value, 'discounted_price');
        });
    }

    // 이미지 업로드 처리
    if (imageDropArea && imageInput) {
        // 드래그 앤 드롭
        imageDropArea.addEventListener('click', () => imageInput.click());
        
        imageDropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageDropArea.classList.add('border-green-500', 'bg-green-50');
        });

        imageDropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            imageDropArea.classList.remove('border-green-500', 'bg-green-50');
        });

        imageDropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            imageDropArea.classList.remove('border-green-500', 'bg-green-50');
            
            const files = Array.from(e.dataTransfer.files);
            handleImageFiles(files);
        });

        imageInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            handleImageFiles(files);
        });
    }

    // 옵션 추가 처리
    if (addOptionBtn) {
        addOptionBtn.addEventListener('click', addOption);
    }

    // 폼 제출 처리
    if (menuForm) {
        menuForm.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            }
        });
    }

    // 함수들
    function updatePriceDisplay() {
        const selectedType = document.querySelector('input[name="price_display"]:checked').value;
        const priceUnits = document.querySelectorAll('.price-unit');
        const helpTexts = document.querySelectorAll('.price-help-text, .discount-help-text');
        
        if (selectedType === 'sats') {
            priceUnits.forEach(unit => unit.textContent = 'sats');
            helpTexts.forEach(text => {
                if (text.classList.contains('price-help-text')) {
                    text.textContent = '가격은 사토시 단위로 입력하세요';
                } else {
                    text.textContent = '할인가는 정가보다 낮아야 합니다';
                }
            });
        } else {
            priceUnits.forEach(unit => unit.textContent = '원');
            helpTexts.forEach(text => {
                if (text.classList.contains('price-help-text')) {
                    text.textContent = '가격은 원화 단위로 입력하세요';
                } else {
                    text.textContent = '할인가는 정가보다 낮아야 합니다';
                }
            });
        }

        // 환율 정보 업데이트
        if (priceInput.value) {
            updateExchangeRate(priceInput.value, 'price');
        }
        if (discountedPriceInput.value) {
            updateExchangeRate(discountedPriceInput.value, 'discounted_price');
        }
    }

    function updateExchangeRate(value, type) {
        if (!value || value <= 0) return;

        const selectedType = document.querySelector('input[name="price_display"]:checked').value;
        const exchangeInfo = document.querySelector(`.${type === 'price' ? 'exchange-info' : 'discount-exchange-info'}`);
        const convertedAmount = document.querySelector(`.${type === 'price' ? 'converted-amount' : 'discount-converted-amount'}`);

        if (!exchangeInfo || !convertedAmount) return;

        // 환율 정보가 있다면 표시
        if (window.exchangeRates && window.exchangeRates.KRW_TO_SATS) {
            const rate = window.exchangeRates.KRW_TO_SATS;
            let converted;

            if (selectedType === 'sats') {
                // 사토시 → 원화
                converted = Math.round(value / rate);
                convertedAmount.textContent = `약 ${converted.toLocaleString()}원`;
            } else {
                // 원화 → 사토시
                converted = Math.round(value * rate);
                convertedAmount.textContent = `약 ${converted.toLocaleString()}sats`;
            }

            exchangeInfo.classList.remove('hidden');
        }
    }

    function handleImageFiles(files) {
        files.forEach(file => {
            if (file.type.startsWith('image/')) {
                if (file.size <= 10 * 1024 * 1024) { // 10MB 제한
                    selectedImages.push(file);
                    displayImagePreview(file);
                } else {
                    alert('이미지 크기는 10MB 이하여야 합니다.');
                }
            }
        });
        
        updateImageInput();
    }

    function displayImagePreview(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const previewItem = document.createElement('div');
            previewItem.className = 'relative aspect-square rounded-lg overflow-hidden border border-gray-200';
            previewItem.innerHTML = `
                <img src="${e.target.result}" alt="미리보기" class="w-full h-full object-cover">
                <button type="button" class="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600" onclick="removeImage(${selectedImages.length - 1})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            imagePreview.appendChild(previewItem);
        };
        reader.readAsDataURL(file);
    }

    function updateImageInput() {
        const dt = new DataTransfer();
        selectedImages.forEach(file => dt.items.add(file));
        imageInput.files = dt.files;
    }

    // 전역 함수로 노출 (HTML에서 호출용)
    window.removeImage = function(index) {
        selectedImages.splice(index, 1);
        imagePreview.innerHTML = '';
        selectedImages.forEach(file => displayImagePreview(file));
        updateImageInput();
    };

    function addOption() {
        optionCount++;
        const optionHtml = `
            <div class="menu-option-item" id="option-${optionCount}">
                <div class="flex items-center justify-between mb-3">
                    <h4 class="font-medium text-gray-900 dark:text-white">옵션 ${optionCount}</h4>
                    <button type="button" class="text-red-500 hover:text-red-700" onclick="removeOption(${optionCount})">
                        <i class="fas fa-trash text-sm"></i>
                    </button>
                </div>
                <div class="space-y-3">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">옵션명</label>
                        <input type="text" name="option_${optionCount}_name" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white" placeholder="예: 사이즈, 맵기 정도">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">옵션값 (콤마로 구분)</label>
                        <input type="text" name="option_${optionCount}_values" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white" placeholder="예: 소, 중, 대">
                    </div>
                </div>
            </div>
        `;
        optionsContainer.insertAdjacentHTML('beforeend', optionHtml);
    }

    // 전역 함수로 노출
    window.removeOption = function(optionId) {
        const optionElement = document.getElementById(`option-${optionId}`);
        if (optionElement) {
            optionElement.remove();
        }
    };

    function validateForm() {
        const name = document.getElementById('name').value.trim();
        const description = document.getElementById('description').value.trim();
        const price = parseFloat(priceInput.value);

        if (!name) {
            alert('메뉴명을 입력해주세요.');
            return false;
        }

        if (!description) {
            alert('메뉴 설명을 입력해주세요.');
            return false;
        }

        if (!price || price <= 0) {
            alert('올바른 가격을 입력해주세요.');
            return false;
        }

        // 할인가 검증
        if (isDiscountedCheckbox.checked) {
            const discountedPrice = parseFloat(discountedPriceInput.value);
            if (!discountedPrice || discountedPrice <= 0) {
                alert('올바른 할인가를 입력해주세요.');
                return false;
            }
            if (discountedPrice >= price) {
                alert('할인가는 정가보다 낮아야 합니다.');
                return false;
            }
        }

        return true;
    }

    // 초기화
    updatePriceDisplay();
});

// 마크다운 에디터 초기화
if (typeof EasyMDE !== 'undefined') {
    const easyMDE = new EasyMDE({
        element: document.getElementById('description'),
        placeholder: '메뉴에 대한 자세한 설명을 마크다운 형식으로 작성하세요...',
        spellChecker: false,
        toolbar: [
            'bold', 'italic', 'heading', '|',
            'quote', 'unordered-list', 'ordered-list', '|',
            'link', 'image', '|',
            'preview', 'side-by-side', 'fullscreen', '|',
            'guide'
        ]
    });
} 