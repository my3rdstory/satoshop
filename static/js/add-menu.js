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

    // 카테고리 로드
    loadCategories();

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

        // 옵션 가격 단위도 업데이트
        const optionUnits = document.querySelectorAll('.option-price-unit');
        const optionExchangeInfos = document.querySelectorAll('.option-exchange-info');
        
        if (selectedType === 'sats') {
            optionUnits.forEach(unit => unit.textContent = 'sats');
            optionExchangeInfos.forEach(info => info.classList.add('hidden'));
        } else {
            optionUnits.forEach(unit => unit.textContent = '원');
            optionExchangeInfos.forEach(info => info.classList.remove('hidden'));
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
        if (optionCount >= 20) {
            alert('옵션은 최대 20개까지만 추가할 수 있습니다.');
            return;
        }

        // 현재 선택된 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
        const checkedRadio = document.querySelector('input[name="price_display"]:checked');
        const isKrwMode = checkedRadio ? checkedRadio.value === 'krw' : false;
        const priceUnit = isKrwMode ? '원' : 'sats';
        const exchangeInfoClass = isKrwMode ? '' : 'hidden';

        const optionSection = document.createElement('div');
        optionSection.className = 'option-section bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4';
        optionSection.innerHTML = `
            <div class="flex items-center gap-4">
                <div class="flex-1">
                    <input class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                           type="text" name="options[${optionCount}][name]" required
                           placeholder="옵션명 (예: 색상, 사이즈)">
                </div>
                <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                        onclick="this.closest('.option-section').remove()">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            
            <div class="space-y-3">
                <div class="flex items-center gap-3">
                    <div class="flex-1">
                        <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                               type="text" name="options[${optionCount}][choices][0][name]" required
                               placeholder="옵션 종류 (예: 빨강, 파랑)">
                    </div>
                    <div class="w-32">
                        <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                               type="number" name="options[${optionCount}][choices][0][price]" min="0"
                               placeholder="추가 가격">
                    </div>
                    <div class="relative w-16">
                        <span class="text-sm text-gray-500 dark:text-gray-400 option-price-unit">${priceUnit}</span>
                        <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 option-exchange-info ${exchangeInfoClass}">
                            <span class="option-converted-amount"></span>
                        </div>
                    </div>
                    <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                            onclick="this.closest('.flex').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            
            <button type="button" class="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 rounded-lg transition-colors" 
                    onclick="addOptionChoice(this)">
                <i class="fas fa-plus text-sm"></i>
                <span>옵션 종류 추가</span>
            </button>
        `;
        optionsContainer.appendChild(optionSection);
        optionCount++;
    }

    // addOptionChoice 함수를 전역으로 정의
    window.addOptionChoice = function(button) {
        const optionSection = button.closest('.option-section');
        const optionIndex = Array.from(optionsContainer.children).indexOf(optionSection);
        const choicesContainer = optionSection.querySelector('.space-y-3');
        const choiceCount = choicesContainer.children.length;

        if (choiceCount >= 20) {
            alert('옵션 종류는 최대 20개까지만 추가할 수 있습니다.');
            return;
        }

        // 현재 선택된 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
        const checkedRadio = document.querySelector('input[name="price_display"]:checked');
        const isKrwMode = checkedRadio ? checkedRadio.value === 'krw' : false;
        const priceUnit = isKrwMode ? '원' : 'sats';
        const exchangeInfoClass = isKrwMode ? '' : 'hidden';

        const choiceDiv = document.createElement('div');
        choiceDiv.className = 'flex items-center gap-3';
        choiceDiv.innerHTML = `
            <div class="flex-1">
                <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                       type="text" name="options[${optionIndex}][choices][${choiceCount}][name]" required
                       placeholder="옵션 종류 (예: 빨강, 파랑)">
            </div>
            <div class="w-32">
                <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                       type="number" name="options[${optionIndex}][choices][${choiceCount}][price]" min="0"
                       placeholder="추가 가격">
            </div>
            <div class="relative w-16">
                <span class="text-sm text-gray-500 dark:text-gray-400 option-price-unit">${priceUnit}</span>
                <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 option-exchange-info ${exchangeInfoClass}">
                    <span class="option-converted-amount"></span>
                </div>
            </div>
            <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                    onclick="this.closest('.flex').remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        choicesContainer.appendChild(choiceDiv);
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

    // 카테고리 관련 함수들
    function loadCategories() {
        const storeId = getStoreIdFromUrl();
        if (!storeId) return;

        fetch(`/menu/${storeId}/categories/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderCategorySelection(data.categories);
            } else {
                document.getElementById('categorySelection').innerHTML = '<p class="text-gray-500 dark:text-gray-400 text-sm">카테고리를 불러올 수 없습니다.</p>';
            }
        })
        .catch(error => {
            console.error('카테고리 로드 오류:', error);
            document.getElementById('categorySelection').innerHTML = '<p class="text-red-500 text-sm">카테고리 로드 중 오류가 발생했습니다.</p>';
        });
    }

    function renderCategorySelection(categories) {
        const categorySelection = document.getElementById('categorySelection');
        if (!categorySelection) return;

        if (categories.length === 0) {
            categorySelection.innerHTML = '<p class="text-gray-500 dark:text-gray-400 text-sm">등록된 카테고리가 없습니다.</p>';
            return;
        }

        const categoryHtml = categories.map(category => `
            <label class="inline-flex items-center space-x-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                <input type="checkbox" name="categories" value="${category.id}" 
                       class="w-4 h-4 text-purple-500 bg-gray-100 border-gray-300 rounded focus:ring-purple-500 dark:focus:ring-purple-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600">
                <span class="text-sm font-medium text-gray-900 dark:text-white">${category.name}</span>
            </label>
        `).join('');

        categorySelection.innerHTML = categoryHtml;
    }

    function getStoreIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const menuIndex = pathParts.indexOf('menu');
        return menuIndex !== -1 && pathParts[menuIndex + 1] ? pathParts[menuIndex + 1] : null;
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