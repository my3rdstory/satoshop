// 밋업 추가 폼 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소들
    const meetupForm = document.getElementById('meetupForm');
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

    // 이미지 업로드 처리
    if (imageDropArea && imageInput) {
        // 드래그 앤 드롭
        imageDropArea.addEventListener('click', () => imageInput.click());
        
        imageDropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageDropArea.classList.add('border-purple-500', 'bg-purple-50');
        });

        imageDropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            imageDropArea.classList.remove('border-purple-500', 'bg-purple-50');
        });

        imageDropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            imageDropArea.classList.remove('border-purple-500', 'bg-purple-50');
            
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
    if (meetupForm) {
        meetupForm.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            }
        });
    }

    // 카테고리 로드
    loadCategories();

    // 마크다운 에디터 초기화
    if (document.getElementById('description')) {
        const easyMDE = new EasyMDE({
            element: document.getElementById('description'),
            placeholder: '밋업에 대한 자세한 설명을 마크다운 형식으로 작성하세요...',
            spellChecker: false,
            toolbar: [
                'bold', 'italic', 'heading', '|',
                'unordered-list', 'ordered-list', '|',
                'link', 'image', '|',
                'preview', 'side-by-side', 'fullscreen', '|',
                'guide'
            ],
            status: false,
            autofocus: false,
            renderingConfig: {
                singleLineBreaks: false,
            },
        });
    }

    // 함수들
    function handleImageFiles(files) {
        // 1장만 허용
        if (files.length > 1) {
            alert('밋업 이미지는 1장만 업로드할 수 있습니다.');
            return;
        }
        
        // 기존 이미지 제거
        selectedImages = [];
        imagePreview.innerHTML = '';
        
        const file = files[0];
        if (file && file.type.startsWith('image/')) {
            if (file.size <= 10 * 1024 * 1024) { // 10MB 제한
                selectedImages.push(file);
                displayImagePreview(file);
                updateImageInput();
            } else {
                alert('이미지 크기는 10MB 이하여야 합니다.');
            }
        } else {
            alert('이미지 파일만 업로드할 수 있습니다.');
        }
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

        const optionSection = document.createElement('div');
        optionSection.className = 'option-section bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4';
        optionSection.innerHTML = `
            <div class="flex items-center gap-4">
                <div class="flex-1">
                    <input class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                           type="text" name="options[${optionCount}][name]" required
                           placeholder="옵션명 (예: 참가 유형, 식사 옵션)">
                </div>
                <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                        onclick="this.closest('.option-section').remove()">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div class="option-choices-container space-y-3">
                <div class="flex items-center gap-3">
                    <input class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                           type="text" name="options[${optionCount}][choices][0][name]" required
                           placeholder="선택지명 (예: 온라인 참가)">
                    <div class="relative">
                        <input class="w-32 px-3 py-2 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                               type="number" name="options[${optionCount}][choices][0][price]" min="0"
                               placeholder="추가금액">
                        <span class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 text-xs">sats</span>
                    </div>
                    <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                            onclick="this.closest('.flex').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <button type="button" class="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-800 rounded-lg transition-colors" 
                    onclick="addOptionChoice(this)">
                <i class="fas fa-plus text-sm"></i>
                <span>선택지 추가</span>
            </button>
        `;
        
        optionsContainer.appendChild(optionSection);
        optionCount++;
    }

    // 전역 함수로 노출
    window.addOptionChoice = function(button) {
        const choicesContainer = button.parentElement.querySelector('.option-choices-container');
        const optionIndex = optionCount - 1;
        const choiceIndex = choicesContainer.children.length;
        
        const choiceDiv = document.createElement('div');
        choiceDiv.className = 'flex items-center gap-3';
        choiceDiv.innerHTML = `
            <input class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                   type="text" name="options[${optionIndex}][choices][${choiceIndex}][name]" required
                   placeholder="선택지명">
            <div class="relative">
                <input class="w-32 px-3 py-2 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                       type="number" name="options[${optionIndex}][choices][${choiceIndex}][price]" min="0"
                       placeholder="추가금액">
                <span class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 text-xs">sats</span>
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
        const price = parseFloat(document.getElementById('price').value);
        
        if (!name) {
            alert('밋업명을 입력해주세요.');
            return false;
        }
        
        if (!description) {
            alert('밋업 설명을 입력해주세요.');
            return false;
        }
        
        if (isNaN(price) || price < 0) {
            alert('올바른 참가비를 입력해주세요.');
            return false;
        }
        
        // 할인가 검증
        if (isDiscountedCheckbox.checked) {
            const discountedPrice = parseFloat(discountedPriceInput.value);
            if (isNaN(discountedPrice) || discountedPrice <= 0) {
                alert('올바른 할인가를 입력해주세요.');
                return false;
            }
            if (discountedPrice >= price) {
                alert('할인가는 정가보다 낮아야 합니다.');
                return false;
            }
        }
        
        // 옵션 검증
        const optionSections = document.querySelectorAll('.option-section');
        for (let section of optionSections) {
            const optionName = section.querySelector('input[name*="[name]"]').value.trim();
            if (!optionName) {
                alert('모든 옵션명을 입력해주세요.');
                return false;
            }
            
            const choices = section.querySelectorAll('input[name*="[choices]"][name*="[name]"]');
            if (choices.length === 0) {
                alert('각 옵션마다 최소 1개의 선택지가 있어야 합니다.');
                return false;
            }
            
            for (let choice of choices) {
                if (!choice.value.trim()) {
                    alert('모든 옵션 선택지명을 입력해주세요.');
                    return false;
                }
            }
        }
        
        return true;
    }

    function loadCategories() {
        const storeId = getStoreIdFromUrl();
        if (!storeId) return;

        fetch(`/meetup/${storeId}/categories/`)
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
                document.getElementById('categorySelection').innerHTML = '<p class="text-gray-500 dark:text-gray-400 text-sm">카테고리를 불러올 수 없습니다.</p>';
            });
    }

    function renderCategorySelection(categories) {
        const container = document.getElementById('categorySelection');
        
        if (categories.length === 0) {
            container.innerHTML = '<p class="text-gray-500 dark:text-gray-400 text-sm">등록된 카테고리가 없습니다.</p>';
            return;
        }

        container.innerHTML = categories.map(category => `
            <label class="flex items-center">
                <input type="checkbox" name="categories" value="${category.id}" 
                       class="w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin dark:focus:ring-bitcoin dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600">
                <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">${category.name}</span>
            </label>
        `).join('');
    }

    function getStoreIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        const storeIndex = pathParts.indexOf('store');
        if (storeIndex !== -1 && storeIndex + 1 < pathParts.length) {
            return pathParts[storeIndex + 1];
        }
        return null;
    }
}); 