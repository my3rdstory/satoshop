document.addEventListener('DOMContentLoaded', function() {
    // 전역 변수
    let optionCount = window.optionCount || 0;
    let currentPriceDisplay = 'sats';
    let exchangeRate = null;
    let easyMDE = null;

    // DOM 요소
    const priceDisplayRadios = document.querySelectorAll('input[name="price_display"]');
    const priceInput = document.getElementById('price');
    const discountedPriceInput = document.getElementById('discounted_price');
    const isDiscountedCheckbox = document.getElementById('is_discounted');
    const discountSection = document.getElementById('discountSection');
    const addOptionBtn = document.getElementById('addOptionBtn');
    const optionsContainer = document.getElementById('optionsContainer');
    const imageDropArea = document.getElementById('imageDropArea');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const menuForm = document.getElementById('menuForm');

    // 초기화
    init();

    function init() {
        // 가격 표시 방식 초기화
        initializePriceDisplay();
        
        // 마크다운 에디터 초기화
        initMarkdownEditor();
        
        // 이벤트 리스너 설정
        setupEventListeners();
        
        // 환율 정보 로드 (원화 모드인 경우)
        if (currentPriceDisplay === 'krw') {
            fetchExchangeRate();
        }
    }

    function initializePriceDisplay() {
        // 현재 가격 표시 방식 확인
        currentPriceDisplay = window.menuPriceDisplay || 'sats';
        const checkedRadio = document.querySelector('input[name="price_display"]:checked');
        if (checkedRadio) {
            currentPriceDisplay = checkedRadio.value;
        }
        
        // 초기 가격 정보 업데이트
        updatePriceInfo();
        
        // 할인 섹션 초기 상태 설정
        updateDiscountSection();
    }

    function initMarkdownEditor() {
        const descriptionTextarea = document.getElementById('description');
        if (descriptionTextarea) {
            easyMDE = new EasyMDE({
                element: descriptionTextarea,
                placeholder: '메뉴에 대한 자세한 설명을 마크다운 형식으로 작성하세요...',
                spellChecker: false,
                status: false,
                toolbar: [
                    'bold', 'italic', 'heading', '|',
                    'quote', 'unordered-list', 'ordered-list', '|',
                    'link', 'image', '|',
                    'preview', 'side-by-side', 'fullscreen', '|',
                    'guide'
                ]
            });
        }
    }

    function setupEventListeners() {
        // 할인 체크박스
        if (isDiscountedCheckbox) {
            isDiscountedCheckbox.addEventListener('change', updateDiscountSection);
        }

        // 가격 입력 필드
        if (priceInput) {
            priceInput.addEventListener('input', updatePriceInfo);
        }

        if (discountedPriceInput) {
            discountedPriceInput.addEventListener('input', updateDiscountPriceInfo);
        }

        // 옵션 추가 버튼
        if (addOptionBtn) {
            addOptionBtn.addEventListener('click', addOption);
        }

        // 이미지 업로드
        if (imageDropArea && imageInput) {
            setupImageUpload();
        }

        // 폼 제출
        if (menuForm) {
            menuForm.addEventListener('submit', handleFormSubmit);
        }

        // 카테고리 로드
        loadCategories();
    }

    function fetchExchangeRate() {
        // 환율 API 호출
        fetch('/api/exchange-rate/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    exchangeRate = data.btc_krw_rate;
                    console.log('환율 정보 로드됨:', exchangeRate);
                    updatePriceInfo();
                    updateDiscountPriceInfo();
                } else {
                    console.error('환율 정보 로드 실패:', data.error);
                }
            })
            .catch(error => {
                console.error('환율 정보를 가져오는데 실패했습니다:', error);
            });
    }

    function updatePriceInfo() {
        if (!priceInput) return;

        const price = parseFloat(priceInput.value);
        const priceUnit = document.querySelector('.price-unit');
        const priceHelpText = document.querySelector('.price-help-text');
        const exchangeInfo = document.querySelector('.exchange-info');
        const convertedAmount = document.querySelector('.converted-amount');

        // 가격 단위 업데이트
        if (priceUnit) {
            priceUnit.textContent = currentPriceDisplay === 'sats' ? 'sats' : '원';
        }

        // 도움말 텍스트 업데이트
        if (priceHelpText) {
            priceHelpText.textContent = currentPriceDisplay === 'sats' 
                ? '가격은 사토시 단위로 입력하세요' 
                : '가격은 원화 단위로 입력하세요';
        }

        // 환율 정보 표시 (원화 모드일 때만)
        if (currentPriceDisplay === 'krw' && exchangeInfo && convertedAmount) {
            if (exchangeRate && !isNaN(price) && price > 0) {
                const convertedValue = Math.round(price / exchangeRate * 100000000);
                convertedAmount.textContent = `약 ${convertedValue.toLocaleString()} sats`;
                exchangeInfo.classList.remove('hidden');
            } else if (!exchangeRate && !isNaN(price) && price > 0) {
                // 환율 데이터가 없으면 로딩
                convertedAmount.textContent = '환율 정보 로딩 중...';
                exchangeInfo.classList.remove('hidden');
                if (!exchangeRate) {
                    fetchExchangeRate();
                }
            } else {
                exchangeInfo.classList.add('hidden');
            }
        } else if (exchangeInfo) {
            exchangeInfo.classList.add('hidden');
        }
    }

    function updateDiscountPriceInfo() {
        if (!discountedPriceInput) return;

        const discountPrice = parseFloat(discountedPriceInput.value);
        const discountExchangeInfo = document.querySelector('.discount-exchange-info');
        const discountConvertedAmount = document.querySelector('.discount-converted-amount');

        // 환율 정보 표시 (원화 모드일 때만)
        if (currentPriceDisplay === 'krw' && discountExchangeInfo && discountConvertedAmount) {
            if (exchangeRate && !isNaN(discountPrice) && discountPrice > 0) {
                const convertedValue = Math.round(discountPrice / exchangeRate * 100000000);
                discountConvertedAmount.textContent = `약 ${convertedValue.toLocaleString()} sats`;
                discountExchangeInfo.classList.remove('hidden');
            } else if (!exchangeRate && !isNaN(discountPrice) && discountPrice > 0) {
                // 환율 데이터가 없으면 로딩
                discountConvertedAmount.textContent = '환율 정보 로딩 중...';
                discountExchangeInfo.classList.remove('hidden');
                if (!exchangeRate) {
                    fetchExchangeRate();
                }
            } else {
                discountExchangeInfo.classList.add('hidden');
            }
        } else if (discountExchangeInfo) {
            discountExchangeInfo.classList.add('hidden');
        }
    }

    function updateDiscountSection() {
        if (!isDiscountedCheckbox || !discountSection) return;

        if (isDiscountedCheckbox.checked) {
            discountSection.classList.remove('hidden');
            discountedPriceInput.required = true;
        } else {
            discountSection.classList.add('hidden');
            discountedPriceInput.required = false;
            discountedPriceInput.value = '';
        }
    }

    function addOption() {
        if (optionCount >= 20) {
            alert('옵션은 최대 20개까지만 추가할 수 있습니다.');
            return;
        }

        // 현재 선택된 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
        const isKrwMode = currentPriceDisplay === 'krw';
        const priceUnit = isKrwMode ? '원' : 'sats';
        const exchangeInfoClass = isKrwMode ? '' : 'hidden';

        const optionSection = document.createElement('div');
        optionSection.className = 'option-section bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4';
        optionSection.setAttribute('data-option-index', optionCount);
        optionSection.innerHTML = `
            <div class="flex items-center justify-between">
                <h4 class="text-lg font-semibold text-gray-900 dark:text-white">옵션 ${optionCount + 1}</h4>
                <button type="button" class="text-red-500 hover:text-red-700 transition-colors" onclick="removeOption(this.closest('.option-section'))">
                    <i class="fas fa-trash text-sm"></i>
                </button>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">옵션명</label>
                <input type="text" name="options[${optionCount}][name]" 
                       class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                       placeholder="예: 사이즈, 맵기 정도" required>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">옵션 선택지</label>
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
                                   placeholder="추가 가격" value="0">
                        </div>
                        <div class="relative w-16">
                            <span class="text-sm text-gray-500 dark:text-gray-400 option-price-unit">${priceUnit}</span>
                            <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 option-exchange-info ${exchangeInfoClass}">
                                <span class="option-converted-amount"></span>
                            </div>
                        </div>
                        <button type="button" class="text-red-500 hover:text-red-700 transition-colors" onclick="removeOptionChoice(this)">
                            <i class="fas fa-minus-circle text-sm"></i>
                        </button>
                    </div>
                </div>
                
                <button type="button" class="mt-3 inline-flex items-center gap-2 px-3 py-2 bg-bitcoin/10 hover:bg-bitcoin/20 text-bitcoin border border-bitcoin/20 rounded-lg transition-colors text-sm" onclick="addOptionChoice(this.closest('.option-section'))">
                    <i class="fas fa-plus text-xs"></i>
                    <span>선택지 추가</span>
                </button>
            </div>
        `;
        
        optionsContainer.appendChild(optionSection);
        optionCount++;
    }

    // 전역 함수들 정의
    window.addOptionChoice = function(optionSection) {
        const optionIndex = parseInt(optionSection.getAttribute('data-option-index'));
        const choicesContainer = optionSection.querySelector('.space-y-3');
        const choiceCount = choicesContainer.children.length;

        if (choiceCount >= 20) {
            alert('옵션 종류는 최대 20개까지만 추가할 수 있습니다.');
            return;
        }

        // 현재 선택된 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
        const isKrwMode = currentPriceDisplay === 'krw';
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
                       placeholder="추가 가격" value="0">
            </div>
            <div class="relative w-16">
                <span class="text-sm text-gray-500 dark:text-gray-400 option-price-unit">${priceUnit}</span>
                <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 option-exchange-info ${exchangeInfoClass}">
                    <span class="option-converted-amount"></span>
                </div>
            </div>
            <button type="button" class="text-red-500 hover:text-red-700 transition-colors" onclick="removeOptionChoice(this)">
                <i class="fas fa-minus-circle text-sm"></i>
            </button>
        `;
        choicesContainer.appendChild(choiceDiv);
    };

    window.removeOption = function(optionSection) {
        if (optionSection) {
            optionSection.style.transition = 'all 0.3s ease';
            optionSection.style.opacity = '0';
            optionSection.style.transform = 'scale(0.95)';
            
            setTimeout(() => {
                optionSection.remove();
            }, 300);
        }
    };

    window.removeOptionChoice = function(button) {
        const choiceDiv = button.closest('.flex');
        if (choiceDiv) {
            choiceDiv.style.transition = 'all 0.3s ease';
            choiceDiv.style.opacity = '0';
            choiceDiv.style.transform = 'scale(0.95)';
            
            setTimeout(() => {
                choiceDiv.remove();
            }, 300);
        }
    };

    function setupImageUpload() {
        // 드래그 앤 드롭 이벤트
        imageDropArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            imageDropArea.classList.add('drag-over');
        });

        imageDropArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            imageDropArea.classList.remove('drag-over');
        });

        imageDropArea.addEventListener('drop', function(e) {
            e.preventDefault();
            imageDropArea.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            handleImageFiles(files);
        });

        // 클릭으로 파일 선택
        imageDropArea.addEventListener('click', function() {
            imageInput.click();
        });

        imageInput.addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            handleImageFiles(files);
        });
    }

    function handleImageFiles(files) {
        // 1장만 허용
        if (files.length > 1) {
            showNotification('메뉴 이미지는 1장만 업로드할 수 있습니다.', 'error');
            return;
        }
        
        // 기존 미리보기 제거
        imagePreview.innerHTML = '';
        
        const file = files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                showNotification('이미지 파일만 업로드할 수 있습니다.', 'error');
                return;
            }
            if (file.size > 10 * 1024 * 1024) {
                showNotification('파일 크기는 10MB 이하여야 합니다.', 'error');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = function(e) {
                addImagePreview(e.target.result, file.name);
            };
            reader.readAsDataURL(file);
            
            // 파일 input에 파일 설정
            const dt = new DataTransfer();
            dt.items.add(file);
            imageInput.files = dt.files;
        }
    }

    function addImagePreview(src, fileName) {
        const previewHtml = `
            <div class="image-preview-item">
                <img src="${src}" alt="${fileName}" class="w-full h-full object-cover">
                <button type="button" class="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600" onclick="removeImagePreview(this)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        imagePreview.insertAdjacentHTML('beforeend', previewHtml);
    }

    // 전역 함수로 이미지 미리보기 제거
    window.removeImagePreview = function(button) {
        const previewItem = button.closest('.image-preview-item');
        if (previewItem) {
            previewItem.style.transition = 'all 0.3s ease';
            previewItem.style.opacity = '0';
            previewItem.style.transform = 'scale(0.9)';
            
            setTimeout(() => {
                previewItem.remove();
            }, 300);
        }
    };

    function handleFormSubmit(e) {
        e.preventDefault();

        // 폼 유효성 검사
        if (!validateForm()) {
            return;
        }

        // 로딩 상태 설정
        setLoadingState(true);

        // 마크다운 에디터 내용 동기화
        if (easyMDE) {
            easyMDE.codemirror.save();
        }

        // 폼 제출
        menuForm.submit();
    }

    function validateForm() {
        let isValid = true;
        const errors = [];

        // 메뉴명 검사
        const name = document.getElementById('name').value.trim();
        if (!name) {
            errors.push('메뉴명을 입력해주세요.');
            isValid = false;
        }

        // 설명 검사
        const description = easyMDE ? easyMDE.value().trim() : document.getElementById('description').value.trim();
        if (!description) {
            errors.push('메뉴 설명을 입력해주세요.');
            isValid = false;
        }

        // 가격 검사
        const price = parseFloat(priceInput.value);
        if (!price || price <= 0) {
            errors.push('올바른 가격을 입력해주세요.');
            isValid = false;
        }

        // 할인가 검사
        if (isDiscountedCheckbox.checked) {
            const discountPrice = parseFloat(discountedPriceInput.value);
            if (!discountPrice || discountPrice <= 0) {
                errors.push('올바른 할인가를 입력해주세요.');
                isValid = false;
            } else if (discountPrice >= price) {
                errors.push('할인가는 정가보다 낮아야 합니다.');
                isValid = false;
            }
        }

        // 에러 메시지 표시
        if (errors.length > 0) {
            showNotification(errors.join('\n'), 'error');
        }

        return isValid;
    }

    function setLoadingState(loading) {
        const submitBtn = document.querySelector('button[type="submit"]');
        if (loading) {
            menuForm.classList.add('loading');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>수정 중...';
            }
        } else {
            menuForm.classList.remove('loading');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '메뉴 수정';
            }
        }
    }

    function showNotification(message, type = 'info') {
        // 간단한 알림 표시 (실제 구현에서는 더 나은 알림 시스템 사용)
        if (type === 'error') {
            alert('오류: ' + message);
        } else {
            alert(message);
        }
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

        // 현재 메뉴의 카테고리 정보 가져오기 (템플릿에서 전달된 데이터)
        const currentCategories = window.menuCategories || [];

        const categoryHtml = categories.map(category => {
            // 타입을 맞춰서 비교 (숫자로 변환하여 비교)
            const isChecked = currentCategories.includes(parseInt(category.id));
            return `
                <label class="inline-flex items-center space-x-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors">
                    <input type="checkbox" name="categories" value="${category.id}" 
                           ${isChecked ? 'checked' : ''}
                           class="w-4 h-4 text-purple-500 bg-gray-100 border-gray-300 rounded focus:ring-purple-500 dark:focus:ring-purple-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600">
                    <span class="text-sm font-medium text-gray-900 dark:text-white">${category.name}</span>
                </label>
            `;
        }).join('');

        categorySelection.innerHTML = categoryHtml;
    }

    function getStoreIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const menuIndex = pathParts.indexOf('menu');
        return menuIndex !== -1 && pathParts[menuIndex + 1] ? pathParts[menuIndex + 1] : null;
    }

        // 페이지 언로드 시 확인 제거됨 (사용자 요청)
  }); 