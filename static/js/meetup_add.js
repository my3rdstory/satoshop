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
    const locationTbdCheckbox = document.getElementById('location_tbd');
    const locationPostalCode = document.getElementById('location_postal_code');
    const locationAddress = document.getElementById('location_address');
    const locationDetailAddress = document.getElementById('location_detail_address');
    const locationTbdSearchBtn = document.getElementById('location-address-search-btn');

    let selectedImages = [];
    let optionCount = 0;

    // 할인 체크박스 처리
    if (isDiscountedCheckbox) {
        const earlyBirdEndDate = document.getElementById('early_bird_end_date');
        const earlyBirdEndTime = document.getElementById('early_bird_end_time');
        
        // 초기 로드 시 할인 체크박스 상태에 따라 required 속성 설정
        if (isDiscountedCheckbox.checked) {
            if (earlyBirdEndDate) {
                earlyBirdEndDate.setAttribute('required', 'required');
            }
        } else {
            if (earlyBirdEndDate) {
                earlyBirdEndDate.removeAttribute('required');
            }
        }
        
        isDiscountedCheckbox.addEventListener('change', function() {
            if (this.checked) {
                discountSection.classList.remove('hidden');
                // 할인 적용 시 조기등록 종료일 필수로 설정
                if (earlyBirdEndDate) {
                    earlyBirdEndDate.setAttribute('required', 'required');
                }
            } else {
                discountSection.classList.add('hidden');
                discountedPriceInput.value = '';
                // 조기등록 종료 날짜/시간 필드도 초기화
                if (earlyBirdEndDate) {
                    earlyBirdEndDate.value = '';
                    earlyBirdEndDate.removeAttribute('required');
                }
                if (earlyBirdEndTime) earlyBirdEndTime.value = '23:59';
            }
        });
    }

    // 장소 추후 공지 체크박스 처리
    if (locationTbdCheckbox) {
        const locationFieldsContainer = document.getElementById('location-fields-container');
        const locationTbdNotice = document.getElementById('location-tbd-notice');
        
        locationTbdCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            
            // 체크되면 장소 관련 필드들 숨김 및 초기화
            if (isChecked) {
                if (locationFieldsContainer) {
                    locationFieldsContainer.classList.add('hidden');
                }
                if (locationTbdNotice) {
                    locationTbdNotice.classList.remove('hidden');
                }
                
                // 장소 관련 필드 값 초기화
                if (locationPostalCode) {
                    locationPostalCode.value = '';
                }
                if (locationAddress) {
                    locationAddress.value = '';
                }
                if (locationDetailAddress) {
                    locationDetailAddress.value = '';
                }
            } else {
                // 체크 해제하면 장소 관련 필드들 보이기
                if (locationFieldsContainer) {
                    locationFieldsContainer.classList.remove('hidden');
                }
                if (locationTbdNotice) {
                    locationTbdNotice.classList.add('hidden');
                }
            }
        });
        
        // 페이지 로드 시 초기 상태 설정
        if (locationTbdCheckbox.checked) {
            locationTbdCheckbox.dispatchEvent(new Event('change'));
        }
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

    // 마크다운 에디터 초기화
    let easyMDE = null;
    if (document.getElementById('description')) {
        easyMDE = new EasyMDE({
            element: document.getElementById('description'),
            placeholder: '밋업에 대한 자세한 설명을 마크다운 형식으로 작성하세요...',
            spellChecker: false,
            toolbar: [
                'bold', 'italic', 'heading', '|',
                'unordered-list', 'ordered-list', '|',
                'link', 'image'
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

    function collectOptionsData() {
        const optionSections = document.querySelectorAll('.option-section');
        const options = [];
        
        optionSections.forEach((section, optionIndex) => {
            const optionName = section.querySelector('input[name*="[name]"]').value.trim();
            if (!optionName) return;
            
            const choices = [];
            const choiceInputs = section.querySelectorAll('.option-choices-container > div');
            
            choiceInputs.forEach((choiceDiv, choiceIndex) => {
                const nameInput = choiceDiv.querySelector('input[name*="[name]"]');
                const priceInput = choiceDiv.querySelector('input[name*="[price]"]');
                
                if (nameInput && nameInput.value.trim()) {
                    choices.push({
                        name: nameInput.value.trim(),
                        additional_price: parseInt(priceInput.value) || 0,
                        order: choiceIndex
                    });
                }
            });
            
            if (choices.length > 0) {
                options.push({
                    name: optionName,
                    is_required: false, // 추후 필요시 체크박스 추가
                    order: optionIndex,
                    choices: choices
                });
            }
        });
        
        return options;
    }

    function validateForm() {
        const name = document.getElementById('name').value.trim();
        // EasyMDE 에디터에서 값 가져오기
        const description = easyMDE ? easyMDE.value().trim() : document.getElementById('description').value.trim();
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
            const earlyBirdEndDate = document.getElementById('early_bird_end_date').value;
            
            if (isNaN(discountedPrice) || discountedPrice <= 0) {
                alert('올바른 할인가를 입력해주세요.');
                return false;
            }
            if (discountedPrice >= price) {
                alert('할인가는 정가보다 낮아야 합니다.');
                return false;
            }
            if (!earlyBirdEndDate) {
                alert('조기등록 종료 날짜를 선택해주세요.');
                return false;
            }
            
            // 조기등록 종료 날짜가 오늘 이전인지 검증
            const today = new Date().toISOString().split('T')[0];
            if (earlyBirdEndDate < today) {
                alert('조기등록 종료 날짜는 오늘 이후여야 합니다.');
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

    // 폼 제출 시 옵션 데이터 전송
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
            
            // 옵션 데이터 수집 및 JSON으로 변환
            const optionsData = collectOptionsData();
            
            // 숨겨진 input 필드에 JSON 데이터 저장
            let optionsInput = document.querySelector('input[name="options_json"]');
            if (!optionsInput) {
                optionsInput = document.createElement('input');
                optionsInput.type = 'hidden';
                optionsInput.name = 'options_json';
                form.appendChild(optionsInput);
            }
            optionsInput.value = JSON.stringify(optionsData);
            
                         console.log('전송될 옵션 데이터:', optionsData); // 디버깅용
         });
     }

    // 기존 옵션 로드 함수 (수정 페이지용)
    function loadExistingOption(option) {
        const optionSection = document.createElement('div');
        optionSection.className = 'option-section bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4';
        
        // 기본 옵션 구조 생성
        optionSection.innerHTML = `
            <div class="flex items-center gap-4">
                <div class="flex-1">
                    <input class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                           type="text" name="options[${optionCount}][name]" required
                           placeholder="옵션명 (예: 참가 유형, 식사 옵션)" value="${option.name}">
                </div>
                <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                        onclick="this.closest('.option-section').remove()">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div class="option-choices-container space-y-3">
            </div>
            <button type="button" class="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-800 rounded-lg transition-colors" 
                    onclick="addOptionChoice(this)">
                <i class="fas fa-plus text-sm"></i>
                <span>선택지 추가</span>
            </button>
        `;
        
        const choicesContainer = optionSection.querySelector('.option-choices-container');
        
        // 기존 선택지들 추가
        option.choices.forEach((choice, choiceIndex) => {
            const choiceDiv = document.createElement('div');
            choiceDiv.className = 'flex items-center gap-3';
            choiceDiv.innerHTML = `
                <input class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                       type="text" name="options[${optionCount}][choices][${choiceIndex}][name]" required
                       placeholder="선택지명" value="${choice.name}">
                <div class="relative">
                    <input class="w-32 px-3 py-2 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                           type="number" name="options[${optionCount}][choices][${choiceIndex}][price]" min="0"
                           placeholder="추가금액" value="${choice.additional_price || 0}">
                    <span class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 text-xs">sats</span>
                </div>
                <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                        onclick="this.closest('.flex').remove()">
                    <i class="fas fa-times"></i>
                </button>
            `;
            choicesContainer.appendChild(choiceDiv);
        });
        
        optionsContainer.appendChild(optionSection);
        optionCount++;
    }

    // 기존 옵션 로드 (수정 페이지용)
    if (window.existingOptions && window.existingOptions.length > 0) {
        window.existingOptions.forEach(option => {
            loadExistingOption(option);
        });
    }

    // 주소 검색 기능
    const locationAddressModal = document.getElementById('location-address-modal');
    const closeLocationModalBtn = document.getElementById('close-location-address-modal');
    const locationPostalCodeField = document.getElementById('location_postal_code');
    const locationAddressField = document.getElementById('location_address');
    
    let currentLocationPostcodeInstance = null;
    
    // 모달 열기/닫기 함수
    function openLocationAddressModal() {
        if (locationAddressModal) {
            locationAddressModal.classList.remove('hidden');
            locationAddressModal.classList.add('flex');
            document.body.style.overflow = 'hidden';
        }
    }
    
    function closeLocationAddressModal() {
        if (locationAddressModal) {
            locationAddressModal.classList.add('hidden');
            locationAddressModal.classList.remove('flex');
            document.body.style.overflow = '';
        }
        
        setTimeout(() => {
            const container = document.getElementById('location-address-search-container');
            if (container) {
                container.innerHTML = '';
            }
            currentLocationPostcodeInstance = null;
        }, 300);
    }

    // 주소 검색 기능
    function execLocationDaumPostcode() {
        if (!locationAddressModal) {
            console.error('location-address-modal 요소를 찾을 수 없습니다.');
            return;
        }
        
        if (!locationAddressModal.classList.contains('hidden')) {
            return;
        }
        
        openLocationAddressModal();
        
        const container = document.getElementById('location-address-search-container');
        if (!container) {
            console.error('location-address-search-container 요소를 찾을 수 없습니다.');
            return;
        }
        
        if (currentLocationPostcodeInstance || container.children.length > 0) {
            container.innerHTML = '';
            currentLocationPostcodeInstance = null;
            setTimeout(() => {
                createLocationPostcodeInstance(container);
            }, 100);
        } else {
            createLocationPostcodeInstance(container);
        }
    }
    
    function createLocationPostcodeInstance(container) {
        const isDarkMode = document.documentElement.classList.contains('dark') || 
                          window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        currentLocationPostcodeInstance = new daum.Postcode({
            oncomplete: function(data) {
                var addr = '';
                var extraAddr = '';

                if (data.userSelectedType === 'R') {
                    addr = data.roadAddress;
                } else {
                    addr = data.jibunAddress;
                }

                if(data.userSelectedType === 'R'){
                    if(data.bname !== '' && /[동|로|가]$/g.test(data.bname)){
                        extraAddr += data.bname;
                    }
                    if(data.buildingName !== '' && data.apartment === 'Y'){
                        extraAddr += (extraAddr !== '' ? ', ' + data.buildingName : data.buildingName);
                    }
                    if(extraAddr !== ''){
                        extraAddr = ' (' + extraAddr + ')';
                    }
                    addr += extraAddr;
                }

                document.getElementById('location_postal_code').value = data.zonecode;
                document.getElementById('location_address').value = addr;

                closeLocationAddressModal();

                setTimeout(() => {
                    const detailField = document.getElementById('location_detail_address');
                    if (detailField) {
                        detailField.focus();
                    }
                }, 200);
            },
            theme: isDarkMode ? {
                bgColor: "#1F2937",
                searchBgColor: "#374151",
                contentBgColor: "#1F2937",
                pageBgColor: "#111827",
                textColor: "#F9FAFB",
                queryTextColor: "#F9FAFB",
                postcodeTextColor: "#F59E0B",
                emphTextColor: "#60A5FA",
                outlineColor: "#4B5563"
            } : {
                bgColor: "#FFFFFF",
                searchBgColor: "#0052CC",
                contentBgColor: "#FFFFFF",
                pageBgColor: "#FAFAFA",
                textColor: "#333333",
                queryTextColor: "#FFFFFF",
                postcodeTextColor: "#0052CC",
                emphTextColor: "#0052CC",
                outlineColor: "#E0E0E0"
            },
            width: '100%',
            height: '100%',
            animation: false,
            hideMapBtn: false,
            hideEngBtn: false,
            autoMapping: true,
            shorthand: true
        });
        
        currentLocationPostcodeInstance.embed(container);
    }
    
    // 이벤트 리스너 등록
    if (locationTbdSearchBtn) {
        locationTbdSearchBtn.addEventListener('click', execLocationDaumPostcode);
    }
    
    if (locationPostalCodeField) {
        locationPostalCodeField.addEventListener('click', execLocationDaumPostcode);
    }
    
    if (locationAddressField) {
        locationAddressField.addEventListener('click', execLocationDaumPostcode);
    }
    
    if (closeLocationModalBtn) {
        closeLocationModalBtn.addEventListener('click', closeLocationAddressModal);
    }
    
    if (locationAddressModal) {
        locationAddressModal.addEventListener('click', function(e) {
            if (e.target === locationAddressModal) {
                closeLocationAddressModal();
            }
        });
    }
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && locationAddressModal && !locationAddressModal.classList.contains('hidden')) {
            closeLocationAddressModal();
        }
    });

}); 