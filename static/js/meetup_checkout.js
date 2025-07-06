// meetup_checkout.js

let currentPaymentHash = '';
let currentInvoice = '';
let paymentCheckInterval = null;
let meetupCountdown = null; // 카운트다운 인스턴스
let paymentExpiresAt = null;
let isInvoiceGenerated = false;


document.addEventListener('DOMContentLoaded', function() {
    
    // 체크아웃 데이터 로드
    const checkoutDataElement = document.getElementById('checkout-data');
    if (!checkoutDataElement) {
        return;
    }
    
    const checkoutData = JSON.parse(checkoutDataElement.textContent);
    
    // 전역 변수
    window.checkoutData = checkoutData;
    window.selectedOptions = {};
    
    // 디버깅 로그
    
    // 페이지 초기화
    if (checkoutData.isPaymentPage) {
        initPaymentPage();
    } else {
        initCheckoutPage();
    }
});

// 체크아웃 페이지 초기화
function initCheckoutPage() {
    // 옵션 선택 이벤트 리스너 설정
    const optionInputs = document.querySelectorAll('.option-choice-input');
    optionInputs.forEach(input => {
        input.addEventListener('change', updateSelectedOption);
    });
    
    // 폼 제출 이벤트
    const checkoutForm = document.getElementById('checkoutForm');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', handleCheckoutSubmit);
    }
    
    // 초기 가격 계산
    updateTotalPrice();
}

// 결제 페이지 초기화
function initPaymentPage() {
    
    // 인보이스 생성 버튼 스타일 설정
    const generateBtn = document.getElementById('generateInvoiceBtn');
    if (generateBtn) {
        generateBtn.classList.add('invoice-btn');
    }
    
    // 카운트다운 초기화
    if (window.checkoutData.reservationExpiresAt) {
        meetupCountdown = new MeetupCountdown({
            storeId: window.checkoutData.storeId,
            meetupId: window.checkoutData.meetupId,
            reservationExpiresAt: window.checkoutData.reservationExpiresAt
        });
        
        // 전역에서 접근 가능하도록 저장
        window.meetupCountdownInstance = meetupCountdown;
    }
    
    // 무료 참가 신청 폼 이벤트 리스너 추가
    const freeParticipationForm = document.getElementById('free-participation-form');
    
    if (freeParticipationForm) {
        
        freeParticipationForm.addEventListener('submit', function(event) {
            
            // 카운트다운 중지
            if (window.meetupCountdownInstance) {
                try {
                    window.meetupCountdownInstance.stopAndHide();
                } catch (error) {
                }
            } else {
            }
            
            // 버튼 상태 변경
            const submitBtn = document.getElementById('freeParticipationBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `
                    <div class="flex items-center">
                        <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                        <span>처리 중...</span>
                    </div>
                `;
            } else {
            }
            
            // 폼 제출은 계속 진행 (event.preventDefault() 호출하지 않음)
        });
    } else {
    }
}

// 인보이스 생성
function generateInvoice() {
    const generateBtn = document.getElementById('generateInvoiceBtn');
    const invoiceContainer = document.getElementById('invoiceContainer');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const qrCodeImage = document.getElementById('qrCodeImage');
    
    // 버튼 비활성화 및 로딩 표시
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-3"></i> 생성 중...';
    
    // 취소 버튼 초기화 및 숨기기
    document.getElementById('cancelContainer').classList.add('hidden');
    const cancelBtn = document.getElementById('cancelInvoiceBtn');
    cancelBtn.disabled = false;
    cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
    
    // 기존 결제 상태 확인 중지
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        paymentCheckInterval = null;
    }
    
    // 인보이스 컨테이너 표시 및 로딩 스피너 표시
    invoiceContainer.classList.remove('hidden');
    loadingSpinner.classList.remove('hidden');
    qrCodeImage.classList.add('hidden');
    
    // 인보이스 생성 요청
    fetch(`/meetup/${window.checkoutData.storeId}/${window.checkoutData.meetupId}/checkout/${window.checkoutData.orderId}/create_invoice/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.checkoutData.csrfToken
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 인보이스 생성 성공
            currentPaymentHash = data.payment_hash;
            currentInvoice = data.invoice;
            
            // 인보이스 만료 시간으로 카운트다운 업데이트 (보통 15분)
            if (data.expires_at && window.meetupCountdownInstance) {
                try {
                    window.meetupCountdownInstance.switchToPaymentMode(data.expires_at);
                } catch (error) {
                }
            }
            
            // QR 코드 생성
            generateQRCode(data.invoice);
            
            // 인보이스 텍스트 표시
            document.getElementById('invoiceTextArea').value = data.invoice;
            
            // 로딩 숨기고 QR 코드 표시
            loadingSpinner.classList.add('hidden');
            qrCodeImage.classList.remove('hidden');
            
            // 라이트닝 지갑 열기 버튼 표시
            const lightningWalletButton = document.getElementById('lightningWalletButton');
            if (lightningWalletButton) {
                lightningWalletButton.classList.remove('hidden');
            }
            
            // 결제 상태 확인 시작
            startPaymentStatusCheck();
            
            // 상태 메시지 표시
            showPaymentStatus('결제를 기다리고 있습니다. QR 코드를 스캔하거나 인보이스를 복사하여 결제해주세요.', 'pending');
            
            // 버튼 텍스트 변경
            generateBtn.innerHTML = '<i class="fas fa-check mr-3"></i> 인보이스 생성됨';
            
            // 취소 버튼 표시
            document.getElementById('cancelContainer').classList.remove('hidden');
            
        } else {
            // 인보이스 생성 실패
            showPaymentStatus('인보이스 생성에 실패했습니다: ' + data.error, 'error');
            
            // 버튼 복원
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
            
            // 로딩 숨기기
            loadingSpinner.classList.add('hidden');
            
            // 라이트닝 지갑 버튼 숨기기
            const lightningWalletButton = document.getElementById('lightningWalletButton');
            if (lightningWalletButton) {
                lightningWalletButton.classList.add('hidden');
            }
            
            // 취소 버튼 숨기기 및 초기화
            document.getElementById('cancelContainer').classList.add('hidden');
            const cancelBtn = document.getElementById('cancelInvoiceBtn');
            cancelBtn.disabled = false;
            cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
        }
    })
    .catch(error => {
        showPaymentStatus('인보이스 생성 중 오류가 발생했습니다.', 'error');
        
        // 버튼 복원
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
        
        // 로딩 숨기기
        loadingSpinner.classList.add('hidden');
        
        // 취소 버튼 숨기기 및 초기화
        document.getElementById('cancelContainer').classList.add('hidden');
        const cancelBtn = document.getElementById('cancelInvoiceBtn');
        cancelBtn.disabled = false;
        cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
    });
}

function generateQRCode(invoice) {
    try {
        const qr = new QRious({
            element: document.getElementById('qrCodeImage'),
            value: invoice,
            size: 250,
            level: 'M'
        });
    } catch (error) {
        // QR 코드 생성 실패 시 대체 텍스트 표시
        document.getElementById('qrCodeImage').alt = 'QR 코드 생성 실패';
    }
}

function copyInvoiceToClipboard() {
    if (currentInvoice) {
        const tempInput = document.createElement('input');
        tempInput.value = currentInvoice;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        
        // 복사 완료 메시지
        showPaymentStatus('인보이스가 클립보드에 복사되었습니다.', 'success');
        setTimeout(() => {
            showPaymentStatus('결제를 기다리고 있습니다. QR 코드를 스캔하거나 인보이스를 복사하여 결제해주세요.', 'pending');
        }, 2000);
    }
}

function startPaymentStatusCheck() {
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
    }
    
    // 즉시 한 번 확인하고 1초마다 확인 (기존 3초에서 단축)
    checkPaymentStatus();
    paymentCheckInterval = setInterval(checkPaymentStatus, 1000);
    
    // Page Visibility API 이벤트 리스너 추가
    setupPageVisibilityListener();
}

function checkPaymentStatus() {
    if (!currentPaymentHash || currentPaymentHash === '') {
        // payment_hash가 없으면 상태 확인 중지
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
        return;
    }
    
    fetch(`/meetup/${window.checkoutData.storeId}/${window.checkoutData.meetupId}/checkout/${window.checkoutData.orderId}/check_payment/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.checkoutData.csrfToken
        },
        body: JSON.stringify({
            payment_hash: currentPaymentHash
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            if (data.paid) {
                // 결제 완료
                
                if (paymentCheckInterval) {
                    clearInterval(paymentCheckInterval);
                    paymentCheckInterval = null;
                }
                
                // 카운트다운 중지
                if (window.meetupCountdownInstance) {
                    try {
                        window.meetupCountdownInstance.stopAndHide();
                    } catch (error) {
                    }
                }
                
                showPaymentStatus('결제가 완료되었습니다! 참가 확정 페이지로 이동합니다...', 'success');
                
                // 2초 후 결제 완료 페이지로 이동
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            }
            // 결제 대기 중이면 계속 확인
        } else {
            // 에러가 발생하면 상태 확인 중지
            if (paymentCheckInterval) {
                clearInterval(paymentCheckInterval);
                paymentCheckInterval = null;
            }
        }
    })
    .catch(error => {
        // 네트워크 에러가 발생하면 상태 확인 중지
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
    });
}

function showPaymentStatus(message, type) {
    const statusDiv = document.getElementById('paymentStatus');
    const messageDiv = document.getElementById('paymentMessage');
    
    statusDiv.className = 'status-' + type + ' p-4 rounded-lg border';
    statusDiv.classList.remove('hidden');
    messageDiv.innerHTML = message;
}

function cancelInvoice() {
    if (!currentPaymentHash) {
        showPaymentStatus('취소할 인보이스가 없습니다.', 'error');
        return;
    }
    
    if (!confirm('정말로 결제를 취소하시겠습니까?')) {
        return;
    }
    
    const cancelBtn = document.getElementById('cancelInvoiceBtn');
    cancelBtn.disabled = true;
    cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> 취소 중...';
    
    fetch(`/meetup/${window.checkoutData.storeId}/${window.checkoutData.meetupId}/checkout/${window.checkoutData.orderId}/cancel_invoice/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.checkoutData.csrfToken
        },
        body: JSON.stringify({
            payment_hash: currentPaymentHash
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 결제 상태 확인 중지
            if (paymentCheckInterval) {
                clearInterval(paymentCheckInterval);
                paymentCheckInterval = null;
            }
            
            // 현재 인보이스 정보 초기화 (결제 상태 확인 중지 후)
            currentPaymentHash = null;
            currentInvoice = null;
            
            // 카운트다운을 원본 예약 시간으로 복원
            if (window.meetupCountdownInstance) {
                try {
                    window.meetupCountdownInstance.switchToReservationMode();
                } catch (error) {
                }
            }
            
            // 성공 메시지 표시
            showPaymentStatus('결제가 취소되었습니다.', 'error');
            
            // 취소 버튼 숨기기
            document.getElementById('cancelContainer').classList.add('hidden');
            
            // 인보이스 생성 버튼 복원
            const generateBtn = document.getElementById('generateInvoiceBtn');
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
            
            // 인보이스 컨테이너 숨기기
            document.getElementById('invoiceContainer').classList.add('hidden');
            
            // 라이트닝 지갑 버튼 숨기기
            const lightningWalletButton = document.getElementById('lightningWalletButton');
            if (lightningWalletButton) {
                lightningWalletButton.classList.add('hidden');
            }
            
            // 🔄 페이지 새로고침으로 완전 초기화
            setTimeout(() => {
                showPaymentStatus('페이지를 새로고침하여 초기화합니다...', 'info');
                window.location.reload();
            }, 1500);
            
        } else {
            // 결제가 이미 완료된 경우 처리
            if (data.redirect_url) {
                // 결제 상태 확인 중지
                if (paymentCheckInterval) {
                    clearInterval(paymentCheckInterval);
                    paymentCheckInterval = null;
                }
                
                // 카운트다운 중지
                if (window.meetupCountdownInstance) {
                    try {
                        window.meetupCountdownInstance.stopAndHide();
                    } catch (error) {
                    }
                }
                
                // 성공 메시지 표시
                showPaymentStatus('결제가 완료되었습니다! 참가 확정 페이지로 이동합니다...', 'success');
                
                // 2초 후 결제 완료 페이지로 이동
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            } else {
                // 일반적인 실패 메시지 표시
                showPaymentStatus('취소 중 오류가 발생했습니다: ' + data.error, 'error');
                
                // 취소 버튼 복원
                cancelBtn.disabled = false;
                cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
            }
        }
    })
    .catch(error => {
        showPaymentStatus('취소 처리 중 오류가 발생했습니다.', 'error');
        
        // 취소 버튼 복원
        cancelBtn.disabled = false;
        cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
    });
}

// 옵션 선택 업데이트 (체크아웃 페이지용)
function updateSelectedOption(event) {
    const input = event.target;
    const optionId = input.dataset.optionId;
    const choiceId = input.dataset.choiceId;
    const choicePrice = parseInt(input.dataset.choicePrice) || 0;
    
    // 선택된 옵션 저장
    window.selectedOptions[optionId] = {
        choiceId: choiceId,
        price: choicePrice
    };
    
    // UI 업데이트
    updateOptionUI(input);
    updateTotalPrice();
}

// 옵션 UI 업데이트 (체크아웃 페이지용)
function updateOptionUI(selectedInput) {
    const optionId = selectedInput.dataset.optionId;
    
    // 같은 옵션의 다른 선택지들 비활성화
    const allInputsInOption = document.querySelectorAll(`input[data-option-id="${optionId}"]`);
    allInputsInOption.forEach(input => {
        const label = input.closest('.option-choice-label');
        const indicator = label.querySelector('.option-choice-indicator');
        const dot = indicator.querySelector('.option-choice-dot');
        
        if (input === selectedInput) {
            // 선택된 옵션
            label.classList.add('border-purple-500', 'bg-purple-50');
            label.classList.remove('border-gray-300');
            indicator.classList.add('border-purple-500');
            indicator.classList.remove('border-gray-300');
            dot.classList.remove('hidden');
        } else {
            // 선택되지 않은 옵션
            label.classList.remove('border-purple-500', 'bg-purple-50');
            label.classList.add('border-gray-300');
            indicator.classList.remove('border-purple-500');
            indicator.classList.add('border-gray-300');
            dot.classList.add('hidden');
        }
    });
}

// 총 가격 업데이트 (체크아웃 페이지용)
function updateTotalPrice() {
    const basePrice = window.checkoutData.basePrice;
    let optionsPrice = 0;
    
    // 선택된 옵션들의 가격 합계
    Object.values(window.selectedOptions).forEach(option => {
        optionsPrice += option.price;
    });
    
    // UI 업데이트
    const basePriceDisplay = document.getElementById('basePriceDisplay');
    const optionsPriceDisplay = document.getElementById('optionsPriceDisplay');
    const optionsPriceRow = document.getElementById('optionsPriceRow');
    const totalPriceDisplay = document.getElementById('totalPriceDisplay');
    
    if (basePriceDisplay) {
        basePriceDisplay.textContent = `${basePrice.toLocaleString()} sats`;
    }
    
    if (optionsPriceDisplay && optionsPriceRow) {
        if (optionsPrice > 0) {
            optionsPriceDisplay.textContent = `${optionsPrice.toLocaleString()} sats`;
            optionsPriceRow.style.display = 'flex';
        } else {
            optionsPriceRow.style.display = 'none';
        }
    }
    
    if (totalPriceDisplay) {
        const totalPrice = basePrice + optionsPrice;
        totalPriceDisplay.textContent = `${totalPrice.toLocaleString()} sats`;
    }
}

// 체크아웃 폼 제출 처리 (체크아웃 페이지용)
async function handleCheckoutSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // 참가자 정보 수집
    const participantData = {
        participant_name: formData.get('participant_name').trim(),
        participant_email: formData.get('participant_email').trim(),
        participant_phone: formData.get('participant_phone').trim(),
        selected_options: window.selectedOptions
    };
    
    // 유효성 검사
    if (!participantData.participant_name || !participantData.participant_email) {
        alert('참가자 이름과 이메일은 필수입니다.');
        return;
    }
    
    // 필수 옵션 확인
    const requiredOptions = document.querySelectorAll('input[data-option-required="true"]');
    const requiredOptionIds = new Set();
    requiredOptions.forEach(input => {
        requiredOptionIds.add(input.dataset.optionId);
    });
    
    for (const optionId of requiredOptionIds) {
        if (!window.selectedOptions[optionId]) {
            alert('필수 옵션을 모두 선택해주세요.');
            return;
        }
    }
    
    // 버튼 비활성화
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>처리 중...';
    
    try {
        const response = await fetch(`/meetup/${window.checkoutData.storeId}/${window.checkoutData.meetupId}/checkout/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.checkoutData.csrfToken
            },
            body: JSON.stringify(participantData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 결제 페이지로 리다이렉트
            window.location.href = result.redirect_url;
        } else {
            alert(result.error || '주문 생성에 실패했습니다.');
        }
    } catch (error) {
        alert('주문 처리 중 오류가 발생했습니다.');
    } finally {
        // 버튼 복원
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// 라이트닝 지갑 열기 함수
function openLightningWallet() {
    if (!currentInvoice) {
        showPaymentStatus('먼저 인보이스를 생성해주세요.', 'error');
        return;
    }
    
    // Lightning URL 스킴 생성
    const lightningUrl = `lightning:${currentInvoice}`;
    
    try {
        // 모바일 디바이스 감지
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (isMobile) {
            // 모바일에서는 즉시 라이트닝 URL로 이동
            window.location.href = lightningUrl;
            
            // 사용자에게 안내 메시지 표시
            showPaymentStatus('라이트닝 지갑이 열렸습니다. 결제 완료 후 이 페이지로 돌아와주세요.', 'info');
        } else {
            // 데스크톱에서는 새 탭으로 열기 시도
            const newWindow = window.open(lightningUrl, '_blank');
            
            // 새 창이 차단된 경우 대체 방법 제공
            if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
                // 클립보드에 복사하고 안내
                copyInvoiceToClipboard();
                showPaymentStatus('팝업이 차단되었습니다. 인보이스가 클립보드에 복사되었으니 라이트닝 지갑에 직접 붙여넣어주세요.', 'warning');
            } else {
                showPaymentStatus('라이트닝 지갑이 열렸습니다. 결제 완료 후 이 페이지로 돌아와주세요.', 'info');
            }
        }
        
        // 버튼 임시 비활성화 (사용자 경험 개선)
        const walletButton = document.querySelector('#lightningWalletButton button');
        if (walletButton) {
            const originalText = walletButton.innerHTML;
            walletButton.disabled = true;
            walletButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>지갑 열기 중...';
            
            // 3초 후 버튼 복원
            setTimeout(() => {
                walletButton.disabled = false;
                walletButton.innerHTML = originalText;
            }, 3000);
        }
        
    } catch (error) {
        console.error('라이트닝 지갑 열기 실패:', error);
        
        // 오류 발생 시 클립보드 복사로 대체
        copyInvoiceToClipboard();
        showPaymentStatus('지갑 열기에 실패했습니다. 인보이스가 클립보드에 복사되었으니 직접 붙여넣어주세요.', 'warning');
    }
    
    // 지갑 앱 열림 후 즉시 결제 상태 확인 트리거
    schedulePaymentCheck();
}

// 지갑 앱 열림 후 결제 상태 확인 스케줄링
function schedulePaymentCheck() {
    if (!currentPaymentHash) return;
    
    // 3초 후 첫 번째 확인 (지갑 앱 전환 시간 고려)
    setTimeout(() => {
        if (currentPaymentHash) {
            console.log('지갑 앱 후 첫 번째 결제 상태 확인');
            checkPaymentStatus();
        }
    }, 3000);
    
    // 8초 후 두 번째 확인 (결제 처리 시간 고려)
    setTimeout(() => {
        if (currentPaymentHash) {
            console.log('지갑 앱 후 두 번째 결제 상태 확인');
            checkPaymentStatus();
        }
    }, 8000);
    
    // 15초 후 세 번째 확인 (최종 확인)
    setTimeout(() => {
        if (currentPaymentHash) {
            console.log('지갑 앱 후 최종 결제 상태 확인');
            checkPaymentStatus();
        }
    }, 15000);
}

// Page Visibility API 설정
function setupPageVisibilityListener() {
    if (typeof document.hidden !== 'undefined') {
        document.addEventListener('visibilitychange', handleVisibilityChange);
    } else if (typeof document.webkitHidden !== 'undefined') {
        document.addEventListener('webkitvisibilitychange', handleVisibilityChange);
    } else if (typeof document.mozHidden !== 'undefined') {
        document.addEventListener('mozvisibilitychange', handleVisibilityChange);
    }
}

// 페이지 가시성 변경 처리
function handleVisibilityChange() {
    if (document.hidden || document.webkitHidden || document.mozHidden) {
        // 페이지가 백그라운드로 이동
        console.log('📱 페이지가 백그라운드로 이동 (지갑 앱 열림?)');
    } else {
        // 페이지가 다시 활성화됨
        console.log('📱 페이지가 다시 활성화됨 (지갑 앱에서 돌아옴?)');
        
        // 결제 상태 확인 중이면 즉시 확인
        if (currentPaymentHash && paymentCheckInterval) {
            console.log('🔍 결제 상태 즉시 확인 실행');
            checkPaymentStatusEnhanced();
            
            // 추가로 2초 후 한 번 더 확인 (결제 완료 처리 시간 고려)
            setTimeout(() => {
                if (currentPaymentHash) {
                    console.log('🔍 결제 상태 추가 확인 실행');
                    checkPaymentStatusEnhanced();
                }
            }, 2000);
        }
    }
}

// 강화된 결제 상태 확인 (로깅 포함)
function checkPaymentStatusEnhanced() {
    if (!currentPaymentHash || currentPaymentHash === '') {
        // payment_hash가 없으면 상태 확인 중지
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
        return Promise.resolve();
    }
    
    console.log('🔍 결제 상태 확인 중...', currentPaymentHash);
    
    return fetch(`/meetup/${window.checkoutData.storeId}/${window.checkoutData.meetupId}/checkout/${window.checkoutData.orderId}/check_payment/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.checkoutData.csrfToken
        },
        body: JSON.stringify({
            payment_hash: currentPaymentHash
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('🔍 결제 상태 확인 결과:', data);
        
        if (data.success) {
            if (data.paid) {
                // 결제 완료
                console.log('💳 결제 완료 감지!');
                
                if (paymentCheckInterval) {
                    clearInterval(paymentCheckInterval);
                    paymentCheckInterval = null;
                }
                
                // 카운트다운 중지
                if (window.meetupCountdownInstance) {
                    try {
                        window.meetupCountdownInstance.stopAndHide();
                    } catch (error) {
                        console.log('카운트다운 중지 중 오류:', error);
                    }
                }
                
                showPaymentStatus('✅ 결제가 완료되었습니다! 참가 확정 페이지로 이동합니다...', 'success');
                
                // 2초 후 결제 완료 페이지로 이동
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            }
            // 결제 대기 중이면 계속 확인
        } else {
            console.log('❌ 결제 상태 확인 실패:', data.error);
            // 에러가 발생하면 상태 확인 중지
            if (paymentCheckInterval) {
                clearInterval(paymentCheckInterval);
                paymentCheckInterval = null;
            }
        }
    })
    .catch(error => {
        console.error('🚨 결제 상태 확인 중 네트워크 오류:', error);
        // 네트워크 에러는 조용히 처리하고 계속 폴링
    });
}

// DOM 로드 완료 시 페이지 가시성 리스너 초기화
document.addEventListener('DOMContentLoaded', function() {
    setupPageVisibilityListener();
    
    // 모바일 디바이스에서 추가 최적화
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if (isMobile) {
        console.log('📱 모바일 디바이스 감지됨 - 결제 상태 확인 최적화 활성화');
        
        // 모바일에서 페이지 포커스 이벤트 추가
        window.addEventListener('focus', function() {
            console.log('📱 window focus 이벤트 - 결제 상태 확인');
            if (currentPaymentHash && paymentCheckInterval) {
                checkPaymentStatusEnhanced();
            }
        });
        
        // 모바일에서 페이지 보이기 이벤트 추가
        window.addEventListener('pageshow', function(event) {
            console.log('📱 pageshow 이벤트 - 결제 상태 확인');
            if (currentPaymentHash && paymentCheckInterval) {
                checkPaymentStatusEnhanced();
            }
        });
    }
});

// 기존 checkPaymentStatus 함수를 강화된 버전으로 교체
const originalCheckPaymentStatus = checkPaymentStatus;
checkPaymentStatus = function() {
    return checkPaymentStatusEnhanced();
}; 