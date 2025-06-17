/**
 * 환율 연동 기능
 */
class CurrencyExchange {
    constructor() {
        this.currentRate = null;
        this.isLoading = false;
        this.originalSatsValues = {}; // 원본 사토시 값들을 저장
        this.originalKrwValues = {}; // 원본 원화 값들을 저장
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadExchangeRate();
        this.storeOriginalValues(); // 원본 값들을 저장
    }

    bindEvents() {
        // 가격 표시 방식 변경 이벤트
        const priceDisplayRadios = document.querySelectorAll('input[name="price_display"]');
        priceDisplayRadios.forEach(radio => {
            radio.addEventListener('change', () => this.handlePriceDisplayChange());
        });

        // 가격 입력 필드 변경 이벤트
        const priceInputs = ['price', 'discounted_price', 'shipping_fee'];
        priceInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('input', () => this.handlePriceInput(inputId));
            }
        });

        // 옵션 가격 입력 필드 변경 이벤트 (동적으로 추가되는 요소들을 위해 이벤트 위임 사용)
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('option-price-input')) {
                this.handleOptionPriceInput(e.target);
            }
        });
    }

    async loadExchangeRate() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        try {
            const response = await fetch('/api/exchange-rate/');
            const data = await response.json();
            
            if (data.success) {
                this.currentRate = data.btc_krw_rate;
                this.initializePriceDisplay(); // 환율 로드 후 가격 표시 초기화
                this.updateAllConversions();
            } else {
                console.error('환율 데이터 로드 실패:', data.error);
            }
        } catch (error) {
            console.error('환율 API 호출 실패:', error);
        } finally {
            this.isLoading = false;
        }
    }

    // 원본 사토시 및 원화 값들을 저장
    storeOriginalValues() {
        const priceInput = document.getElementById('price');
        const discountedPriceInput = document.getElementById('discounted_price');
        const shippingFeeInput = document.getElementById('shipping_fee');

        // 사토시 값 저장 (항상 존재)
        if (priceInput && priceInput.value) {
            this.originalSatsValues.price = parseFloat(priceInput.value);
        }
        if (discountedPriceInput && discountedPriceInput.value) {
            this.originalSatsValues.discounted_price = parseFloat(discountedPriceInput.value);
        }
        if (shippingFeeInput && shippingFeeInput.value) {
            this.originalSatsValues.shipping_fee = parseFloat(shippingFeeInput.value);
        }

        // 원화 값 저장 (data 속성에서 가져오기)
        const priceKrw = priceInput?.dataset.priceKrw;
        const discountedPriceKrw = discountedPriceInput?.dataset.discountedPriceKrw;
        const shippingFeeKrw = shippingFeeInput?.dataset.shippingFeeKrw;

        if (priceKrw) {
            this.originalKrwValues.price = parseFloat(priceKrw);
        }
        if (discountedPriceKrw) {
            this.originalKrwValues.discounted_price = parseFloat(discountedPriceKrw);
        }
        if (shippingFeeKrw) {
            this.originalKrwValues.shipping_fee = parseFloat(shippingFeeKrw);
        }
    }

    // 페이지 로드 시 가격 표시 방식에 따라 초기화
    initializePriceDisplay() {
        // 가격 표시 방식 라디오 버튼이 있는 경우 (상품 추가/편집 페이지)
        const selectedDisplay = document.querySelector('input[name="price_display"]:checked');
        if (selectedDisplay) {
            if (selectedDisplay.value === 'krw') {
                this.convertSatsToKrwDisplay();
                this.switchToKrwMode();
            } else {
                this.switchToSatsMode();
            }
        } 
        // 옵션 편집 페이지 등에서는 전역 변수로 가격 표시 방식 확인
        else if (window.productPriceDisplay) {
            if (window.productPriceDisplay === 'krw') {
                this.switchToKrwMode();
            } else {
                this.switchToSatsMode();
            }
        }
    }

    // 저장된 원화 값을 입력 필드에 표시 (DB에서 가져온 값 우선 사용)
    convertSatsToKrwDisplay() {
        const priceInput = document.getElementById('price');
        const discountedPriceInput = document.getElementById('discounted_price');
        const shippingFeeInput = document.getElementById('shipping_fee');

        // DB에 저장된 원화 값이 있으면 그것을 사용, 없으면 사토시에서 변환
        if (priceInput) {
            if (this.originalKrwValues.price) {
                priceInput.value = this.originalKrwValues.price;
            } else if (this.originalSatsValues.price && this.currentRate) {
                const krwPrice = this.convertSatsToKrw(this.originalSatsValues.price);
                priceInput.value = krwPrice;
            }
        }

        if (discountedPriceInput) {
            if (this.originalKrwValues.discounted_price) {
                discountedPriceInput.value = this.originalKrwValues.discounted_price;
            } else if (this.originalSatsValues.discounted_price && this.currentRate) {
                const krwDiscountPrice = this.convertSatsToKrw(this.originalSatsValues.discounted_price);
                discountedPriceInput.value = krwDiscountPrice;
            }
        }

        if (shippingFeeInput) {
            if (this.originalKrwValues.shipping_fee) {
                shippingFeeInput.value = this.originalKrwValues.shipping_fee;
            } else if (this.originalSatsValues.shipping_fee && this.currentRate) {
                const krwShippingFee = this.convertSatsToKrw(this.originalSatsValues.shipping_fee);
                shippingFeeInput.value = krwShippingFee;
            }
        }
    }

    // 원화 표시에서 사토시 표시로 되돌리기
    convertKrwToSatsDisplay() {
        const priceInput = document.getElementById('price');
        const discountedPriceInput = document.getElementById('discounted_price');
        const shippingFeeInput = document.getElementById('shipping_fee');

        if (priceInput && this.originalSatsValues.price) {
            priceInput.value = this.originalSatsValues.price;
        }

        if (discountedPriceInput && this.originalSatsValues.discounted_price) {
            discountedPriceInput.value = this.originalSatsValues.discounted_price;
        }

        if (shippingFeeInput && this.originalSatsValues.shipping_fee) {
            shippingFeeInput.value = this.originalSatsValues.shipping_fee;
        }
    }

    handlePriceDisplayChange() {
        const selectedDisplay = document.querySelector('input[name="price_display"]:checked').value;
        
        if (selectedDisplay === 'krw') {
            this.convertSatsToKrwDisplay();
            this.switchToKrwMode();
        } else {
            this.convertKrwToSatsDisplay();
            this.switchToSatsMode();
        }
    }

    switchToKrwMode() {
        // 단위 표시 변경
        document.querySelectorAll('.price-unit').forEach(unit => {
            unit.textContent = '원';
        });

        // 옵션 가격 단위도 변경
        document.querySelectorAll('.option-price-unit').forEach(unit => {
            unit.textContent = '원';
        });

        // 도움말 텍스트 변경
        const priceHelpText = document.querySelector('.price-help-text');
        if (priceHelpText) {
            priceHelpText.textContent = '가격은 원화 단위로 입력하세요';
        }

        const discountHelpText = document.querySelector('.discount-help-text');
        if (discountHelpText) {
            discountHelpText.textContent = '할인가는 정가보다 낮아야 합니다 (원화 기준)';
        }

        const shippingHelpText = document.querySelector('.shipping-help-text');
        if (shippingHelpText) {
            shippingHelpText.textContent = '배송비는 원화 단위로 입력하세요 (0원인 경우 배송비 무료로 표시됩니다)';
        }

        // 환율 정보 표시
        this.showExchangeInfo();
        this.showOptionExchangeInfo();
        this.updateAllConversions();
        this.updateAllOptionConversions();
    }

    switchToSatsMode() {
        // 단위 표시 변경
        document.querySelectorAll('.price-unit').forEach(unit => {
            unit.textContent = 'sats';
        });

        // 옵션 가격 단위도 변경
        document.querySelectorAll('.option-price-unit').forEach(unit => {
            unit.textContent = 'sats';
        });

        // 도움말 텍스트 변경
        const priceHelpText = document.querySelector('.price-help-text');
        if (priceHelpText) {
            priceHelpText.textContent = '가격은 사토시 단위로 입력하세요';
        }

        const discountHelpText = document.querySelector('.discount-help-text');
        if (discountHelpText) {
            discountHelpText.textContent = '할인가는 정가보다 낮아야 합니다';
        }

        const shippingHelpText = document.querySelector('.shipping-help-text');
        if (shippingHelpText) {
            shippingHelpText.textContent = '배송비는 사토시 단위로 입력하세요 (0sats인 경우 배송비 무료로 표시됩니다)';
        }

        // 환율 정보 숨김
        this.hideExchangeInfo();
        this.hideOptionExchangeInfo();
    }

    showExchangeInfo() {
        document.querySelectorAll('.exchange-info, .discount-exchange-info, .shipping-exchange-info').forEach(info => {
            info.classList.remove('hidden');
        });
    }

    hideExchangeInfo() {
        document.querySelectorAll('.exchange-info, .discount-exchange-info, .shipping-exchange-info').forEach(info => {
            info.classList.add('hidden');
        });
    }

    showOptionExchangeInfo() {
        document.querySelectorAll('.option-exchange-info').forEach(info => {
            info.classList.remove('hidden');
        });
    }

    hideOptionExchangeInfo() {
        document.querySelectorAll('.option-exchange-info').forEach(info => {
            info.classList.add('hidden');
        });
    }

    handlePriceInput(inputId) {
        const selectedDisplay = document.querySelector('input[name="price_display"]:checked').value;
        
        if (selectedDisplay === 'krw') {
            this.updateConversion(inputId);
        }
    }

    updateConversion(inputId) {
        if (!this.currentRate) return;

        const input = document.getElementById(inputId);
        if (!input) return;

        const krwAmount = parseFloat(input.value) || 0;
        const satsAmount = this.convertKrwToSats(krwAmount);

        let conversionElement;
        if (inputId === 'price') {
            conversionElement = document.querySelector('.converted-amount');
        } else if (inputId === 'discounted_price') {
            conversionElement = document.querySelector('.discount-converted-amount');
        } else if (inputId === 'shipping_fee') {
            conversionElement = document.querySelector('.shipping-converted-amount');
        }

        if (conversionElement) {
            if (krwAmount > 0) {
                conversionElement.textContent = `≈ ${satsAmount.toLocaleString()} sats`;
            } else {
                conversionElement.textContent = '';
            }
        }
    }

    updateAllConversions() {
        const selectedDisplay = document.querySelector('input[name="price_display"]:checked').value;
        
        if (selectedDisplay === 'krw') {
            this.updateConversion('price');
            this.updateConversion('discounted_price');
            this.updateConversion('shipping_fee');
        }
    }

    handleOptionPriceInput(input) {
        // 가격 표시 방식 확인 (라디오 버튼이 있으면 그것을, 없으면 전역 변수 사용)
        const selectedDisplayRadio = document.querySelector('input[name="price_display"]:checked');
        const selectedDisplay = selectedDisplayRadio ? selectedDisplayRadio.value : window.productPriceDisplay;
        
        if (selectedDisplay === 'krw') {
            this.updateOptionConversion(input);
        }
    }

    updateOptionConversion(input) {
        if (!this.currentRate) return;

        const krwAmount = parseFloat(input.value) || 0;
        const satsAmount = this.convertKrwToSats(krwAmount);

        // 해당 옵션의 변환 정보 표시 요소 찾기
        const optionRow = input.closest('.flex');
        const conversionElement = optionRow?.querySelector('.option-converted-amount');

        if (conversionElement) {
            if (krwAmount > 0) {
                conversionElement.textContent = `≈ ${satsAmount.toLocaleString()} sats`;
            } else {
                conversionElement.textContent = '';
            }
        }
    }

    updateAllOptionConversions() {
        // 가격 표시 방식 확인 (라디오 버튼이 있으면 그것을, 없으면 전역 변수 사용)
        const selectedDisplayRadio = document.querySelector('input[name="price_display"]:checked');
        const selectedDisplay = selectedDisplayRadio ? selectedDisplayRadio.value : window.productPriceDisplay;
        
        if (selectedDisplay === 'krw') {
            const optionInputs = document.querySelectorAll('.option-price-input');
            optionInputs.forEach(input => {
                this.updateOptionConversion(input);
            });
        }
    }

    convertKrwToSats(krwAmount) {
        if (!this.currentRate || krwAmount <= 0) return 0;
        
        // 1 BTC = 100,000,000 사토시
        const btcAmount = krwAmount / this.currentRate;
        const satsAmount = btcAmount * 100_000_000;
        return Math.round(satsAmount);
    }

    convertSatsToKrw(satsAmount) {
        if (!this.currentRate || satsAmount <= 0) return 0;
        
        // 1 BTC = 100,000,000 사토시
        const btcAmount = satsAmount / 100_000_000;
        const krwAmount = btcAmount * this.currentRate;
        return Math.round(krwAmount);
    }

    // 폼 제출 시 추가 데이터 준비 (변환하지 않고 그대로 전송)
    prepareFormData() {
        const selectedDisplayRadio = document.querySelector('input[name="price_display"]:checked');
        const selectedDisplay = selectedDisplayRadio ? selectedDisplayRadio.value : window.productPriceDisplay;
        
        // 숨겨진 필드들을 추가하여 원화/사토시 값을 모두 전송
        const form = document.querySelector('#productForm, #basicInfoForm, #optionsForm, #unifiedProductForm');
        if (!form) return;

        // 기존 숨겨진 필드들 제거
        const existingHiddenFields = form.querySelectorAll('input[type="hidden"][name$="_krw"], input[type="hidden"][name$="_sats"]');
        existingHiddenFields.forEach(field => field.remove());

        // 옵션 편집 폼인 경우 옵션 가격만 처리
        if (form.id === 'optionsForm') {
            this.addHiddenOptionFields(form, selectedDisplay);
            return;
        }

        if (selectedDisplay === 'krw') {
            // 원화 모드: 현재 입력값을 원화로, 사토시는 변환값으로 전송
            this.addHiddenKrwFields(form);
        } else {
            // 사토시 모드: 현재 입력값을 사토시로, 원화는 변환값으로 전송
            this.addHiddenSatsFields(form);
        }
    }

    addHiddenKrwFields(form) {
        const priceInput = document.getElementById('price');
        const discountedPriceInput = document.getElementById('discounted_price');
        const shippingFeeInput = document.getElementById('shipping_fee');

        if (priceInput && priceInput.value) {
            const krwPrice = parseFloat(priceInput.value);
            const satsPrice = this.convertKrwToSats(krwPrice);
            
            // 원화 모드: 입력값(원화)과 변환값(사토시) 전송
            this.createHiddenField(form, 'price_krw', krwPrice);
            this.createHiddenField(form, 'price_sats', satsPrice);
        }

        if (discountedPriceInput && discountedPriceInput.value) {
            const krwDiscountPrice = parseFloat(discountedPriceInput.value);
            const satsDiscountPrice = this.convertKrwToSats(krwDiscountPrice);
            
            this.createHiddenField(form, 'discounted_price_krw', krwDiscountPrice);
            this.createHiddenField(form, 'discounted_price_sats', satsDiscountPrice);
        }

        if (shippingFeeInput && shippingFeeInput.value) {
            const krwShippingFee = parseFloat(shippingFeeInput.value);
            const satsShippingFee = this.convertKrwToSats(krwShippingFee);
            
            this.createHiddenField(form, 'shipping_fee_krw', krwShippingFee);
            this.createHiddenField(form, 'shipping_fee_sats', satsShippingFee);
        }
    }

    addHiddenSatsFields(form) {
        const priceInput = document.getElementById('price');
        const discountedPriceInput = document.getElementById('discounted_price');
        const shippingFeeInput = document.getElementById('shipping_fee');

        if (priceInput && priceInput.value) {
            const satsPrice = parseFloat(priceInput.value);
            const krwPrice = this.convertSatsToKrw(satsPrice);
            
            // 사토시 모드: 입력값(사토시)과 변환값(원화) 전송
            this.createHiddenField(form, 'price_sats', satsPrice);
            this.createHiddenField(form, 'price_krw', krwPrice);
        }

        if (discountedPriceInput && discountedPriceInput.value) {
            const satsDiscountPrice = parseFloat(discountedPriceInput.value);
            const krwDiscountPrice = this.convertSatsToKrw(satsDiscountPrice);
            
            this.createHiddenField(form, 'discounted_price_sats', satsDiscountPrice);
            this.createHiddenField(form, 'discounted_price_krw', krwDiscountPrice);
        }

        if (shippingFeeInput && shippingFeeInput.value) {
            const satsShippingFee = parseFloat(shippingFeeInput.value);
            const krwShippingFee = this.convertSatsToKrw(satsShippingFee);
            
            this.createHiddenField(form, 'shipping_fee_sats', satsShippingFee);
            this.createHiddenField(form, 'shipping_fee_krw', krwShippingFee);
        }
    }

    addHiddenOptionFields(form, selectedDisplay) {
        const optionInputs = form.querySelectorAll('.option-price-input');
        
        optionInputs.forEach(input => {
            if (!input.value) return;
            
            const price = parseFloat(input.value);
            if (isNaN(price) || price <= 0) return;
            
            // 입력 필드의 name 속성에서 인덱스 추출
            const nameMatch = input.name.match(/options\[(\d+)\]\[choices\]\[(\d+)\]\[price\]/);
            if (!nameMatch) return;
            
            const optionIndex = nameMatch[1];
            const choiceIndex = nameMatch[2];
            
            if (selectedDisplay === 'krw') {
                // 원화 모드: 입력값은 원화, 사토시로 변환
                const satsPrice = this.convertKrwToSats(price);
                this.createHiddenField(form, `options[${optionIndex}][choices][${choiceIndex}][price_krw]`, price);
                this.createHiddenField(form, `options[${optionIndex}][choices][${choiceIndex}][price_sats]`, satsPrice);
            } else {
                // 사토시 모드: 입력값은 사토시, 원화로 변환
                const krwPrice = this.convertSatsToKrw(price);
                this.createHiddenField(form, `options[${optionIndex}][choices][${choiceIndex}][price_sats]`, price);
                this.createHiddenField(form, `options[${optionIndex}][choices][${choiceIndex}][price_krw]`, krwPrice);
            }
        });
    }

    createHiddenField(form, name, value) {
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = name;
        hiddenField.value = value;
        form.appendChild(hiddenField);
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    const currencyExchange = new CurrencyExchange();
    
    // 폼 제출 시 데이터 준비
    const forms = document.querySelectorAll('#productForm, #basicInfoForm, #optionsForm, #unifiedProductForm');
    forms.forEach(form => {
        if (form) {
            form.addEventListener('submit', function(e) {
                currencyExchange.prepareFormData();
            });
        }
    });
}); 