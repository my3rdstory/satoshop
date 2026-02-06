// 배송 정보 입력 폼 검증 스크립트

document.addEventListener('DOMContentLoaded', function() {
    const checkoutBtn = document.getElementById('checkout-btn');
    const checkoutBtnText = document.getElementById('checkout-btn-text');
    const addressSearchBtn = document.getElementById('address-search-btn');
    const addressModal = document.getElementById('address-modal');
    const closeModalBtn = document.getElementById('close-address-modal');
    const postalCodeField = document.getElementById('shipping_postal_code');
    const addressField = document.getElementById('shipping_address');
    
    // 필수 요소들이 존재하는지 확인
    if (!checkoutBtn) {
        console.error('checkout-btn 요소를 찾을 수 없습니다.');
        return;
    }
    if (!checkoutBtnText) {
        console.error('checkout-btn-text 요소를 찾을 수 없습니다.');
    }
    if (!addressModal) {
        console.error('address-modal 요소를 찾을 수 없습니다.');
    }
    
    // 필수 필드들
    const ALWAYS_REQUIRED_FIELDS = [
        'buyer_name',
        'buyer_phone', 
        'buyer_email'
    ];
    const SHIPPING_REQUIRED_FIELDS = ['shipping_postal_code', 'shipping_address'];
    const trackedFields = Array.from(new Set([
        ...ALWAYS_REQUIRED_FIELDS,
        ...SHIPPING_REQUIRED_FIELDS,
        'order_memo',
    ]));
    const pickupCheckbox = document.getElementById('pickup_requested');
    const shippingSection = document.getElementById('shipping-section');
    const pickupNotice = document.getElementById('pickup-shipping-notice');
    const memoHint = document.getElementById('pickup-memo-hint');
    const orderMemoField = document.getElementById('order_memo');

    function isPickupMode() {
        return pickupCheckbox ? pickupCheckbox.checked : false;
    }

    function toggleShippingFieldRequirements(pickupMode) {
        SHIPPING_REQUIRED_FIELDS.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.required = !pickupMode;
            }
        });
    }

    function updatePickupState() {
        const pickupMode = isPickupMode();
        if (shippingSection) {
            shippingSection.classList.toggle('hidden', pickupMode);
        }
        if (pickupNotice) {
            pickupNotice.classList.toggle('hidden', !pickupMode);
        }
        if (memoHint) {
            memoHint.classList.toggle('hidden', !pickupMode);
        }
        toggleShippingFieldRequirements(pickupMode);
    }

    function getActiveRequiredFields() {
        const pickupMode = isPickupMode();
        return pickupMode
            ? [...ALWAYS_REQUIRED_FIELDS]
            : [...ALWAYS_REQUIRED_FIELDS, ...SHIPPING_REQUIRED_FIELDS];
    }
    
    function validateForm() {
        const requiredFields = getActiveRequiredFields();
        let allFilled = true;
        
        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (!field || !field.value.trim()) {
                allFilled = false;
            }
        });
        
        // checkoutBtn이 존재하는지 확인
        if (!checkoutBtn) {
            console.error('checkout-btn 요소를 찾을 수 없습니다.');
            return;
        }
        
        if (allFilled) {
            checkoutBtn.disabled = false;
            checkoutBtn.classList.remove('disabled:bg-gray-400', 'disabled:cursor-not-allowed', 'disabled:shadow-none');
            checkoutBtn.classList.add('bg-bitcoin', 'hover:bg-bitcoin/90');
            
            // 총 금액 확인하여 버튼 텍스트 설정
            const totalAmount = window.shippingPageData ? window.shippingPageData.totalAmount : 0;
            const checkoutBtnIcon = document.getElementById('checkout-btn-icon');
            
            if (totalAmount === 0) {
                if (checkoutBtnText) {
                    checkoutBtnText.textContent = '무료 주문 완료하기';
                }
                if (checkoutBtnIcon) {
                    checkoutBtnIcon.className = 'fas fa-check mr-2';
                }
            } else {
                if (checkoutBtnText) {
                    checkoutBtnText.textContent = '결제하기';
                }
                if (checkoutBtnIcon) {
                    checkoutBtnIcon.className = 'fas fa-credit-card mr-2';
                }
            }
        } else {
            checkoutBtn.disabled = true;
            checkoutBtn.classList.add('disabled:bg-gray-400', 'disabled:cursor-not-allowed', 'disabled:shadow-none');
            checkoutBtn.classList.remove('bg-bitcoin', 'hover:bg-bitcoin/90');
            if (checkoutBtnText) {
                checkoutBtnText.textContent = '필수 정보를 입력해주세요';
            }
        }
    }
    
    // 현재 우편번호 검색 인스턴스 저장
    let currentPostcodeInstance = null;
    
    // 모달 열기/닫기 함수
    function openAddressModal() {
        if (addressModal) {
            addressModal.classList.remove('hidden');
            addressModal.classList.add('flex');
            document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
        }
    }
    
    function closeAddressModal() {
        if (addressModal) {
            addressModal.classList.add('hidden');
            addressModal.classList.remove('flex');
            document.body.style.overflow = ''; // 배경 스크롤 복원
        }
        
        // API가 자체적으로 정리할 시간을 준 후 컨테이너 초기화
        setTimeout(() => {
            const container = document.getElementById('address-search-container');
            if (container) {
                container.innerHTML = '';
            }
            currentPostcodeInstance = null;
        }, 300);
    }

    // 주소 검색 기능
    function execDaumPostcode() {
        // addressModal이 존재하지 않으면 함수 종료
        if (!addressModal) {
            console.error('address-modal 요소를 찾을 수 없습니다.');
            return;
        }
        
        // 이미 모달이 열려있으면 중복 실행 방지
        if (!addressModal.classList.contains('hidden')) {
            return;
        }
        
        // 모달 열기
        openAddressModal();
        
        // 컨테이너 가져오기
        const container = document.getElementById('address-search-container');
        if (!container) {
            console.error('address-search-container 요소를 찾을 수 없습니다.');
            return;
        }
        
        // 기존 내용이 있다면 안전하게 정리하고 새 인스턴스 생성
        if (currentPostcodeInstance || container.children.length > 0) {
            container.innerHTML = '';
            currentPostcodeInstance = null;
            // DOM 정리 후 잠시 대기 후 새 인스턴스 생성
            setTimeout(() => {
                createPostcodeInstance(container);
            }, 100);
        } else {
            // 바로 새 인스턴스 생성
            createPostcodeInstance(container);
        }
    }
    
    // Postcode 인스턴스 생성 함수
    function createPostcodeInstance(container) {
        if (!window.kakao || !window.kakao.Postcode) {
            console.error('Kakao Postcode script is not loaded.');
            closeAddressModal();
            return;
        }

        // 다크모드 감지
        const isDarkMode = document.documentElement.classList.contains('dark') || 
                          window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        currentPostcodeInstance = new window.kakao.Postcode({
            oncomplete: function(data) {
                // 검색결과 항목을 클릭했을때 실행할 코드
                
                // 각 주소의 노출 규칙에 따라 주소를 조합한다.
                var addr = ''; // 주소 변수
                var extraAddr = ''; // 참고항목 변수

                //사용자가 선택한 주소 타입에 따라 해당 주소 값을 가져온다.
                if (data.userSelectedType === 'R') { // 사용자가 도로명 주소를 선택했을 경우
                    addr = data.roadAddress;
                } else { // 사용자가 지번 주소를 선택했을 경우(J)
                    addr = data.jibunAddress;
                }

                // 사용자가 선택한 주소가 도로명 타입일때 참고항목을 조합한다.
                if(data.userSelectedType === 'R'){
                    // 법정동명이 있을 경우 추가한다. (법정리는 제외)
                    // 법정동의 경우 마지막 문자가 "동/로/가"로 끝난다.
                    if(data.bname !== '' && /[동|로|가]$/g.test(data.bname)){
                        extraAddr += data.bname;
                    }
                    // 건물명이 있고, 공동주택일 경우 추가한다.
                    if(data.buildingName !== '' && data.apartment === 'Y'){
                        extraAddr += (extraAddr !== '' ? ', ' + data.buildingName : data.buildingName);
                    }
                    // 표시할 참고항목이 있을 경우, 괄호까지 추가한 최종 문자열을 만든다.
                    if(extraAddr !== ''){
                        extraAddr = ' (' + extraAddr + ')';
                    }
                    // 조합된 참고항목을 해당 필드에 넣는다.
                    addr += extraAddr;
                }

                // 우편번호와 주소 정보를 해당 필드에 넣는다.
                document.getElementById('shipping_postal_code').value = data.zonecode;
                document.getElementById('shipping_address').value = addr;

                // 모달 닫기
                closeAddressModal();

                // 커서를 상세주소 필드로 이동한다.
                setTimeout(() => {
                    const detailField = document.getElementById('shipping_detail_address');
                    if (detailField) {
                        detailField.focus();
                    }
                }, 200);
                
                // 폼 검증 다시 실행
                validateForm();
            },
            theme: isDarkMode ? {
                bgColor: "#1F2937", //바탕 배경색 (dark)
                searchBgColor: "#374151", //검색창 배경색 (dark)
                contentBgColor: "#1F2937", //본문 배경색 (dark)
                pageBgColor: "#111827", //페이지 배경색 (dark)
                textColor: "#F9FAFB", //기본 글자색 (dark)
                queryTextColor: "#F9FAFB", //검색창 글자색 (dark)
                postcodeTextColor: "#F59E0B", //우편번호 글자색 (bitcoin color)
                emphTextColor: "#60A5FA", //강조 글자색 (blue)
                outlineColor: "#4B5563" //테두리 (dark)
            } : {
                bgColor: "#FFFFFF", //바탕 배경색 (light)
                searchBgColor: "#0052CC", //검색창 배경색 (light)
                contentBgColor: "#FFFFFF", //본문 배경색 (light)
                pageBgColor: "#FAFAFA", //페이지 배경색 (light)
                textColor: "#333333", //기본 글자색 (light)
                queryTextColor: "#FFFFFF", //검색창 글자색 (light)
                postcodeTextColor: "#0052CC", //우편번호 글자색 (light)
                emphTextColor: "#0052CC", //강조 글자색 (light)
                outlineColor: "#E0E0E0" //테두리 (light)
            },
            width: '100%',
            height: '100%',
            animation: false, // 모달 내부에서는 애니메이션 비활성화
            hideMapBtn: false,
            hideEngBtn: false,
            autoMapping: true,
            shorthand: true
        });
        
        // embed 방식으로 컨테이너에 삽입
        currentPostcodeInstance.embed(container);
    }
    
    // 주소 검색 버튼 클릭 이벤트
    if (addressSearchBtn) {
        addressSearchBtn.addEventListener('click', execDaumPostcode);
    }
    
    // 우편번호 필드 클릭 이벤트
    if (postalCodeField) {
        postalCodeField.addEventListener('click', execDaumPostcode);
    }
    
    // 기본주소 필드 클릭 이벤트
    if (addressField) {
        addressField.addEventListener('click', execDaumPostcode);
    }
    
    // 모달 닫기 버튼 클릭 이벤트
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeAddressModal);
    }
    
    // 모달 배경 클릭시 닫기
    if (addressModal) {
        addressModal.addEventListener('click', function(e) {
            if (e.target === addressModal) {
                closeAddressModal();
            }
        });
    }
    
    // ESC 키로 모달 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !addressModal.classList.contains('hidden')) {
            closeAddressModal();
        }
    });
    
    // 페이지 언로드시 인스턴스 정리
    window.addEventListener('beforeunload', function() {
        if (currentPostcodeInstance) {
            // 단순히 참조만 제거 (DOM 조작은 브라우저가 처리)
            currentPostcodeInstance = null;
        }
    });
    
    // 각 필수 필드에 이벤트 리스너 추가
    trackedFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', validateForm);
            field.addEventListener('blur', validateForm);
        }
    });

    if (pickupCheckbox) {
        pickupCheckbox.addEventListener('change', () => {
            updatePickupState();
            validateForm();
        });
    }
    
    // 초기 검증
    updatePickupState();
    validateForm();
}); 
