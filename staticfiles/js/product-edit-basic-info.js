// product-edit-basic-info.js - 상품 기본 정보 편집 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 모든 EasyMDE 관련 로컬 스토리지 데이터 정리
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.startsWith('smde_') || key.includes('easymde') || key.includes('product_description'))) {
            keysToRemove.push(key);
        }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    
    // textarea의 원본 값 저장
    const descriptionTextarea = document.getElementById('description');
    const originalValue = descriptionTextarea.value;
    
    // EasyMDE 마크다운 에디터 초기화
    const easyMDE = new EasyMDE({
        element: document.getElementById('description'),
        spellChecker: false,
        placeholder: '상품에 대한 자세한 설명을 마크다운 형식으로 작성하세요...',
        toolbar: [
          'bold', 'italic', 'heading', '|',
          'quote', 'unordered-list', 'ordered-list', '|',
          'link', 'image'
        ],
        status: ['lines', 'words', 'cursor'],
        autosave: {
            enabled: false
        },
        renderingConfig: {
            singleLineBreaks: false,
            codeSyntaxHighlighting: true
        },
        insertTexts: {
            horizontalRule: ["", "\n\n-----\n\n"],
            image: ["![](http://", ")"],
            link: ["[", "](http://)"],
            table: ["", "\n\n| Column 1 | Column 2 | Column 3 |\n| -------- | -------- | -------- |\n| Text     | Text      | Text     |\n\n"]
        },
        previewRender: function(plainText) {
            // 우리가 만든 마크다운 렌더러 사용
            if (typeof MarkdownRenderer !== 'undefined') {
                return MarkdownRenderer.parseText(plainText);
            } else {
                // 폴백: marked 라이브러리 사용
                return marked.parse(plainText);
            }
        }
    });

    // EasyMDE 초기화 후 원본 값으로 강제 설정
    setTimeout(() => {
        easyMDE.value(originalValue);
    }, 100);

    // 폼 제출 시 EasyMDE 내용 동기화
    const form = document.getElementById('basicInfoForm');
    if (form) {
        form.addEventListener('submit', function() {
            easyMDE.codemirror.save();
        });
    }

    // 할인 체크박스 기능
    const isDiscounted = document.getElementById('is_discounted');
    const discountSection = document.getElementById('discountSection');

    if (isDiscounted && discountSection) {
        isDiscounted.addEventListener('change', function () {
            discountSection.classList.toggle('hidden', !this.checked);
        });
    }

    // 가격 표시 방식 변경에 따른 단위 업데이트
    const priceDisplayRadios = document.querySelectorAll('input[name="price_display"]');
    const priceUnits = document.querySelectorAll('.price-unit');

    function updatePriceUnits(selectedValue) {
        const unit = selectedValue === 'sats' ? 'sats' : '원';
        priceUnits.forEach(unitElement => {
            unitElement.textContent = unit;
        });
    }

    // 초기 단위 설정
    const checkedRadio = document.querySelector('input[name="price_display"]:checked');
    if (checkedRadio) {
        updatePriceUnits(checkedRadio.value);
    }

    // 라디오 버튼 변경 이벤트 리스너
    priceDisplayRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                updatePriceUnits(this.value);
            }
        });
    });
}); 