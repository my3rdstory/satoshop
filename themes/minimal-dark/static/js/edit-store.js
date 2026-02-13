document.addEventListener('DOMContentLoaded', function () {
    // EasyMDE 초기화 (더 컴팩트한 설정)
    const easyMDE = new EasyMDE({
        element: document.getElementById('store_description'),
        placeholder: '스토어에 대한 설명을 Markdown 형식으로 작성해주세요.',
        spellChecker: false,
        status: false,
        toolbar: ['bold', 'italic', 'heading', '|', 'quote', 'unordered-list', '|', 'link'],
        minHeight: '100px'
    });

    // 연락처 입력 검증
    const phoneInput = document.getElementById('owner_phone');
    const emailInput = document.getElementById('owner_email');
    const contactHelp = document.getElementById('contactHelp');

    function validateContact() {
        const hasPhone = phoneInput.value.trim().length > 0;
        const hasEmail = emailInput.value.trim().length > 0;

        if (!hasPhone && !hasEmail) {
            contactHelp.className = 'mt-1 text-xs text-red-600 dark:text-red-400';
            contactHelp.textContent = '휴대전화 또는 이메일 중 하나는 반드시 입력해야 합니다.';
            return false;
        } else {
            contactHelp.className = 'mt-1 text-xs text-green-600 dark:text-green-400';
            contactHelp.textContent = '연락처가 올바르게 입력되었습니다.';
            return true;
        }
    }

    phoneInput.addEventListener('input', validateContact);
    emailInput.addEventListener('input', validateContact);
    validateContact();

    // API 키 보기/숨기기
    const toggleApi = document.getElementById('toggleApi');
    const apiInput = document.getElementById('blink_api_info');

    toggleApi.addEventListener('click', function () {
        if (apiInput.type === 'password') {
            apiInput.type = 'text';
            toggleApi.innerHTML = '<i class="fas fa-eye-slash text-gray-600 dark:text-gray-300"></i>';
        } else {
            apiInput.type = 'password';
            toggleApi.innerHTML = '<i class="fas fa-eye text-gray-600 dark:text-gray-300"></i>';
        }
    });

    // 월렛 ID 보기/숨기기
    const toggleWallet = document.getElementById('toggleWallet');
    const walletInput = document.getElementById('blink_wallet_id');

    toggleWallet.addEventListener('click', function () {
        if (walletInput.type === 'password') {
            walletInput.type = 'text';
            toggleWallet.innerHTML = '<i class="fas fa-eye-slash text-gray-600 dark:text-gray-300"></i>';
        } else {
            walletInput.type = 'password';
            toggleWallet.innerHTML = '<i class="fas fa-eye text-gray-600 dark:text-gray-300"></i>';
        }
    });

    // 폼 제출 검증
    document.getElementById('editStoreForm').addEventListener('submit', function (e) {
        if (!validateContact()) {
            e.preventDefault();
            alert('연락처를 확인해주세요.');
            return false;
        }

        const storeName = document.getElementById('store_name').value.trim();
        const ownerName = document.getElementById('owner_name').value.trim();
        const chatChannel = document.getElementById('chat_channel').value.trim();

        if (!storeName || !ownerName || !chatChannel) {
            e.preventDefault();
            alert('필수 필드를 모두 입력해주세요.');
            return false;
        }

        if (!confirm('스토어 정보를 변경하시겠습니까?')) {
            e.preventDefault();
            return false;
        }

        const saveBtn = document.getElementById('saveBtn');
        saveBtn.classList.add('opacity-50', 'cursor-not-allowed');
        saveBtn.disabled = true;

        return true;
    });

    // 컬러픽커 연동 및 미리보기
    const color1Input = document.getElementById('hero_color1');
    const color1Text = document.getElementById('hero_color1_text');
    const color1Btn = document.getElementById('color1_picker_btn');
    const color2Input = document.getElementById('hero_color2');
    const color2Text = document.getElementById('hero_color2_text');
    const color2Btn = document.getElementById('color2_picker_btn');
    const textColorInput = document.getElementById('hero_text_color');
    const textColorText = document.getElementById('hero_text_color_text');
    const textColorBtn = document.getElementById('text_color_picker_btn');
    const preview = document.getElementById('gradient_preview');

    function updateGradientPreview() {
        const color1 = color1Input.value;
        const color2 = color2Input.value;
        const textColor = textColorInput.value;
        const gradient = `linear-gradient(135deg, ${color1} 0%, ${color2} 100%)`;

        // 미리보기 업데이트
        preview.style.background = gradient;
        preview.style.color = textColor;

        // 팔레트 버튼 색상도 업데이트
        color1Btn.style.backgroundColor = color1;
        color2Btn.style.backgroundColor = color2;
        textColorBtn.style.backgroundColor = textColor;

        // 텍스트 색상 조정 (밝기에 따라)
        color1Btn.style.color = isLightColor(color1) ? '#333' : 'white';
        color2Btn.style.color = isLightColor(color2) ? '#333' : 'white';
        textColorBtn.style.color = isLightColor(textColor) ? '#333' : 'white';
    }

    function isLightColor(hex) {
        // 색상의 밝기를 계산하여 텍스트 색상 결정
        const r = parseInt(hex.substr(1, 2), 16);
        const g = parseInt(hex.substr(3, 2), 16);
        const b = parseInt(hex.substr(5, 2), 16);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        return brightness > 155;
    }

    function syncColorInputs() {
        // 컬러픽커와 텍스트 입력 동기화
        color1Text.value = color1Input.value;
        color2Text.value = color2Input.value;
        textColorText.value = textColorInput.value;
        updateGradientPreview();
    }

    function syncTextInputs() {
        // 텍스트 입력에서 컬러픽커로 동기화
        if (color1Text.value.match(/^#[0-9A-F]{6}$/i)) {
            color1Input.value = color1Text.value;
        }
        if (color2Text.value.match(/^#[0-9A-F]{6}$/i)) {
            color2Input.value = color2Text.value;
        }
        if (textColorText.value.match(/^#[0-9A-F]{6}$/i)) {
            textColorInput.value = textColorText.value;
        }
        updateGradientPreview();
    }

    // 커스텀 컬러팔레트 기능
    const commonColors = [
        '#FF0000', '#FF8000', '#FFFF00', '#80FF00', '#00FF00', '#00FF80', '#00FFFF', '#0080FF',
        '#0000FF', '#8000FF', '#FF00FF', '#FF0080', '#800000', '#808000', '#008000', '#008080',
        '#000080', '#800080', '#C0C0C0', '#808080', '#FFFFFF', '#000000', '#FFA500', '#FFD700',
        '#ADFF2F', '#00CED1', '#FF69B4', '#DDA0DD', '#F0E68C', '#E6E6FA', '#FFE4E1', '#F5F5DC'
    ];

    function createColorPalette(gridId, inputId, textInputId, customInputId) {
        const grid = document.getElementById(gridId);
        if (!grid) return;
        
        const input = document.getElementById(inputId);
        const textInput = document.getElementById(textInputId);
        const customInput = document.getElementById(customInputId);

        // 기본 색상 팔레트 생성
        commonColors.forEach(color => {
            const swatch = document.createElement('div');
            swatch.className = 'color-swatch';
            swatch.style.backgroundColor = color;
            swatch.title = color;
            swatch.addEventListener('click', function () {
                input.value = color;
                textInput.value = color;
                updateGradientPreview();
                hideAllPalettes();
            });
            grid.appendChild(swatch);
        });

        // 커스텀 입력 처리
        if (customInput) {
            customInput.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    const color = this.value;
                    if (color.match(/^#[0-9A-F]{6}$/i)) {
                        input.value = color;
                        textInput.value = color;
                        updateGradientPreview();
                        hideAllPalettes();
                    }
                }
            });

            customInput.addEventListener('blur', function () {
                const color = this.value;
                if (color.match(/^#[0-9A-F]{6}$/i)) {
                    input.value = color;
                    textInput.value = color;
                    updateGradientPreview();
                }
            });
        }
    }

    function hideAllPalettes() {
        document.querySelectorAll('.custom-color-palette').forEach(palette => {
            palette.classList.remove('is-active');
        });
    }

    function showPalette(paletteId) {
        hideAllPalettes();
        const palette = document.getElementById(paletteId);
        if (palette) {
            palette.classList.add('is-active');
        }
    }

    // 팔레트 초기화
    createColorPalette('color1_grid', 'hero_color1', 'hero_color1_text', 'color1_custom_input');
    createColorPalette('color2_grid', 'hero_color2', 'hero_color2_text', 'color2_custom_input');
    createColorPalette('text_color_grid', 'hero_text_color', 'hero_text_color_text', 'text_color_custom_input');

    // iro.js 컬러휠 초기화 (라이브러리가 로드된 경우에만)
    if (typeof iro !== 'undefined') {
        function createColorWheel(containerId, inputId, textInputId) {
            const container = document.getElementById(containerId);
            if (!container) return null;
            
            const colorPicker = new iro.ColorPicker(containerId, {
                width: 200,
                color: document.getElementById(inputId).value,
                borderWidth: 1,
                borderColor: "#fff"
            });

            colorPicker.on('color:change', function (color) {
                const hexColor = color.hexString;
                document.getElementById(inputId).value = hexColor;
                document.getElementById(textInputId).value = hexColor;
                updateGradientPreview();
            });

            return colorPicker;
        }

        // 컬러휠 생성
        const color1Wheel = createColorWheel('#color1_wheel', 'hero_color1', 'hero_color1_text');
        const color2Wheel = createColorWheel('#color2_wheel', 'hero_color2', 'hero_color2_text');
        const textColorWheel = createColorWheel('#text_color_wheel', 'hero_text_color', 'hero_text_color_text');
    }

    // 팔레트 버튼 클릭 시 커스텀 팔레트 표시
    if (color1Btn) {
        color1Btn.addEventListener('click', function (e) {
            e.stopPropagation();
            showPalette('color1_palette');
        });
    }

    if (color2Btn) {
        color2Btn.addEventListener('click', function (e) {
            e.stopPropagation();
            showPalette('color2_palette');
        });
    }

    if (textColorBtn) {
        textColorBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            showPalette('text_color_palette');
        });
    }

    // 외부 클릭시 팔레트 닫기
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.custom-color-palette') && !e.target.closest('.color-picker-btn')) {
            hideAllPalettes();
        }
    });

    // 이벤트 리스너 추가
    if (color1Input) color1Input.addEventListener('input', syncColorInputs);
    if (color2Input) color2Input.addEventListener('input', syncColorInputs);
    if (textColorInput) textColorInput.addEventListener('input', syncColorInputs);
    if (color1Text) color1Text.addEventListener('input', syncTextInputs);
    if (color2Text) color2Text.addEventListener('input', syncTextInputs);
    if (textColorText) textColorText.addEventListener('input', syncTextInputs);

    // 추천 색상 버튼 기능
    const presetButtons = document.querySelectorAll('.preset-color');
    presetButtons.forEach(button => {
        button.addEventListener('click', function () {
            const color1 = this.dataset.color1;
            const color2 = this.dataset.color2;

            // 모든 입력 필드 업데이트
            if (color1Input) color1Input.value = color1;
            if (color1Text) color1Text.value = color1;
            if (color2Input) color2Input.value = color2;
            if (color2Text) color2Text.value = color2;

            // 미리보기 업데이트
            updateGradientPreview();

            // 선택된 버튼 강조 효과
            presetButtons.forEach(btn => btn.classList.remove('is-active'));
            this.classList.add('is-active');

            setTimeout(() => {
                this.classList.remove('is-active');
            }, 1000);
        });
    });

    // 텍스트 색상 프리셋 버튼 기능
    const textPresetButtons = document.querySelectorAll('.text-preset-color');
    textPresetButtons.forEach(button => {
        button.addEventListener('click', function () {
            const textColor = this.dataset.color;

            // 텍스트 색상 필드 업데이트
            if (textColorInput) textColorInput.value = textColor;
            if (textColorText) textColorText.value = textColor;

            // 미리보기 업데이트
            updateGradientPreview();

            // 선택된 버튼 강조 효과
            textPresetButtons.forEach(btn => btn.classList.remove('is-active'));
            this.classList.add('is-active');

            setTimeout(() => {
                this.classList.remove('is-active');
            }, 1000);
        });
    });

    // 스토어 활성화 체크박스 경고
    const isActiveCheckbox = document.querySelector('input[name="is_active"]');
    if (isActiveCheckbox) {
        isActiveCheckbox.addEventListener('change', function () {
            if (!this.checked) {
                // 체크가 해제될 때 경고
                const confirmed = confirm(
                    '⚠️ 스토어를 비활성화하시겠습니까?\n\n' +
                    '비활성화하면:\n' +
                    '• 고객들이 스토어에 접근할 수 없습니다\n' +
                    '• 스토어 URL이 작동하지 않습니다\n' +
                    '• 검색에서 제외됩니다\n\n' +
                    '정말로 비활성화하시겠습니까?'
                );

                if (!confirmed) {
                    // 취소하면 다시 체크
                    this.checked = true;
                }
            }
        });
    }

    // 초기 미리보기 설정
    updateGradientPreview();
}); 