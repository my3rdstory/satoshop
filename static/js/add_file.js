// add_file.js - 파일 추가 기능을 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const priceDisplay = document.getElementById('id_price_display');
    const satsPriceSection = document.getElementById('sats-price-section');
    const krwPriceSection = document.getElementById('krw-price-section');
    const satsDiscountSection = document.getElementById('sats-discount-section');
    const krwDiscountSection = document.getElementById('krw-discount-section');
    const isDiscounted = document.getElementById('id_is_discounted');
    const discountSection = document.getElementById('discount-section');
    const fileInput = document.getElementById('id_file');
    const previewImageInput = document.getElementById('id_preview_image');
    
    // Flatpickr 초기화
    if (typeof flatpickr !== 'undefined') {
        flatpickr("#id_discount_end_date", {
            locale: "ko",
            dateFormat: "Y-m-d",
            minDate: "today"
        });
        
        flatpickr("#id_discount_end_time", {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            time_24hr: true,
            defaultHour: 23,
            defaultMinute: 59
        });
    }

    // 가격 표시 방식에 따른 입력 필드 표시/숨김
    function updatePriceSections() {
        const value = priceDisplay.value;
        
        if (value === 'free') {
            satsPriceSection.style.display = 'none';
            krwPriceSection.style.display = 'none';
            satsDiscountSection.style.display = 'none';
            krwDiscountSection.style.display = 'none';
            isDiscounted.checked = false;
            discountSection.style.display = 'none';
        } else if (value === 'sats') {
            satsPriceSection.style.display = 'block';
            krwPriceSection.style.display = 'none';
            satsDiscountSection.style.display = 'block';
            krwDiscountSection.style.display = 'none';
        } else if (value === 'krw') {
            satsPriceSection.style.display = 'none';
            krwPriceSection.style.display = 'block';
            satsDiscountSection.style.display = 'none';
            krwDiscountSection.style.display = 'block';
        }
    }

    // 할인 섹션 표시/숨김
    function updateDiscountSection() {
        if (isDiscounted.checked && priceDisplay.value !== 'free') {
            discountSection.style.display = 'block';
        } else {
            discountSection.style.display = 'none';
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

    if (isDiscounted) {
        isDiscounted.addEventListener('change', updateDiscountSection);
        updateDiscountSection();
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

            // 할인 가격 검증
            if (isDiscounted.checked && priceDisplay.value !== 'free') {
                if (priceDisplay.value === 'sats') {
                    const discountedPrice = document.getElementById('id_discounted_price');
                    const originalPrice = document.getElementById('id_price');
                    if (discountedPrice && originalPrice) {
                        if (!discountedPrice.value || discountedPrice.value <= 0) {
                            alert('할인가를 입력해주세요.');
                            e.preventDefault();
                            return;
                        }
                        if (parseFloat(discountedPrice.value) >= parseFloat(originalPrice.value)) {
                            alert('할인가는 원가보다 낮아야 합니다.');
                            e.preventDefault();
                            return;
                        }
                    }
                } else if (priceDisplay.value === 'krw') {
                    const discountedPriceKrw = document.getElementById('id_discounted_price_krw');
                    const originalPriceKrw = document.getElementById('id_price_krw');
                    if (discountedPriceKrw && originalPriceKrw) {
                        if (!discountedPriceKrw.value || discountedPriceKrw.value <= 0) {
                            alert('할인가를 입력해주세요.');
                            e.preventDefault();
                            return;
                        }
                        if (parseFloat(discountedPriceKrw.value) >= parseFloat(originalPriceKrw.value)) {
                            alert('할인가는 원가보다 낮아야 합니다.');
                            e.preventDefault();
                            return;
                        }
                    }
                }
            }
        });
    }

    // 마크다운 에디터 초기화 (EasyMDE가 로드된 경우)
    if (typeof EasyMDE !== 'undefined') {
        const descriptionTextarea = document.getElementById('id_description');
        const purchaseMessageTextarea = document.getElementById('id_purchase_message');
        
        if (descriptionTextarea) {
            new EasyMDE({
                element: descriptionTextarea,
                spellChecker: false,
                autosave: {
                    enabled: true,
                    uniqueId: "file_description",
                    delay: 1000,
                },
                toolbar: ["bold", "italic", "heading", "|", "quote", "unordered-list", "ordered-list", "|", "link", "image", "|", "preview", "side-by-side", "fullscreen", "|", "guide"]
            });
        }
        
        if (purchaseMessageTextarea) {
            new EasyMDE({
                element: purchaseMessageTextarea,
                spellChecker: false,
                autosave: {
                    enabled: true,
                    uniqueId: "file_purchase_message",
                    delay: 1000,
                },
                toolbar: ["bold", "italic", "heading", "|", "quote", "unordered-list", "ordered-list", "|", "link", "|", "preview", "side-by-side", "fullscreen"]
            });
        }
    }
});