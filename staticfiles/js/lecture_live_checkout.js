let currentPaymentHash = '';
let currentInvoice = '';
let paymentCheckInterval = null;
let paymentExpiresAt = null;
let isInvoiceGenerated = false;

// 전역 변수
let checkoutData = {};

document.addEventListener('DOMContentLoaded', function() {
    initializePage();
});

// 페이지 초기화
function initializePage() {
    // 모바일 디바이스 감지 및 주의사항 표시
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (isMobile) {
        // 모바일 환경에서만 주의사항 박스 표시
        const mobileWarning = document.getElementById('mobilePaymentWarning');
        if (mobileWarning) {
            mobileWarning.classList.remove('hidden');
        }
    }
    
    // 체크아웃 데이터 파싱
    parseCheckoutData();
    
    // 무료 참가 신청 폼 이벤트 리스너
    setupFreeParticipationForm();
}

// 체크아웃 데이터 파싱
function parseCheckoutData() {
    const checkoutDataElement = document.getElementById('checkout-data');
    if (checkoutDataElement) {
        try {
            checkoutData = JSON.parse(checkoutDataElement.textContent);
            window.checkoutData = checkoutData;
        } catch (error) {
            console.error('체크아웃 데이터 파싱 실패:', error);
        }
    }
}

// 무료 참가 신청 폼 설정
function setupFreeParticipationForm() {
    const freeForm = document.getElementById('free-participation-form');
    
    if (freeForm) {
        freeForm.addEventListener('submit', function(event) {
            // 버튼 상태 변경
            const btn = document.getElementById('freeParticipationBtn');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<div class="flex items-center"><div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div><span>처리 중...</span></div>';
            }
            
            // event.preventDefault() 호출하지 않음 - 폼이 정상적으로 제출되도록 함
        });
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
    fetch(`/lecture/${window.checkoutData.storeId}/live/${window.checkoutData.liveLectureId}/checkout/create_invoice/`, {
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
            showPaymentStatus('pending', '결제를 기다리고 있습니다. QR 코드를 스캔하거나 인보이스를 복사하여 결제해주세요.');
            
            // 버튼 텍스트 변경
            generateBtn.innerHTML = '<i class="fas fa-check mr-3"></i> 인보이스 생성됨';
            
            // 취소 버튼 표시
            document.getElementById('cancelContainer').classList.remove('hidden');
            
        } else {
            // 인보이스 생성 실패
            showPaymentStatus('error', '인보이스 생성에 실패했습니다: ' + data.error);
            
            // 버튼 복원
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i>결제 인보이스 생성';
            
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
        console.error('인보이스 생성 오류:', error);
        showPaymentStatus('error', '인보이스 생성 중 오류가 발생했습니다.');
        
        // 버튼 복원
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i>결제 인보이스 생성';
        
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
    });
}

// QR 코드 생성
function generateQRCode(invoice) {
    try {
        const qr = new QRious({
            element: document.getElementById('qrCodeImage'),
            value: invoice,
            size: 250,
            level: 'M'
        });
    } catch (error) {
        console.error('QR 코드 생성 오류:', error);
        // QR 코드 생성 실패 시 대체 텍스트 표시
        document.getElementById('qrCodeImage').alt = 'QR 코드 생성 실패';
    }
}

// 인보이스 클립보드에 복사
function copyInvoiceToClipboard() {
    if (currentInvoice) {
        const tempInput = document.createElement('input');
        tempInput.value = currentInvoice;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        
        // 복사 완료 메시지
        showPaymentStatus('success', '인보이스가 클립보드에 복사되었습니다.');
        setTimeout(() => {
            showPaymentStatus('pending', '결제를 기다리고 있습니다. QR 코드를 스캔하거나 인보이스를 복사하여 결제해주세요.');
        }, 2000);
    }
}

// 결제 상태 확인 시작
function startPaymentStatusCheck() {
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
    }
    
    // 즉시 한 번 확인
    checkPaymentStatus();
    
    // 1초마다 확인 (밋업과 동일)
    paymentCheckInterval = setInterval(checkPaymentStatus, 1000);
}

// 결제 상태 확인
function checkPaymentStatus() {
    if (!currentPaymentHash || currentPaymentHash === '') {
        // payment_hash가 없으면 상태 확인 중지
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
        return;
    }
    
    fetch(`/lecture/${window.checkoutData.storeId}/live/${window.checkoutData.liveLectureId}/checkout/check_payment/`, {
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
            if (data.status === 'paid') {
                // 결제 완료
                showPaymentStatus('success', '결제가 완료되었습니다! 잠시 후 참가 확정 페이지로 이동합니다.');
                
                // 결제 상태 확인 중지
                if (paymentCheckInterval) {
                    clearInterval(paymentCheckInterval);
                    paymentCheckInterval = null;
                }
                
                // 3초 후 참가 확정 페이지로 이동
                setTimeout(() => {
                    window.location.href = `/lecture/${window.checkoutData.storeId}/live/${window.checkoutData.liveLectureId}/complete/${data.order_id}/`;
                }, 3000);
                
            } else if (data.status === 'expired') {
                // 결제 만료
                showPaymentStatus('error', '결제 시간이 만료되었습니다. 다시 시도해주세요.');
                
                // 결제 상태 확인 중지
                if (paymentCheckInterval) {
                    clearInterval(paymentCheckInterval);
                    paymentCheckInterval = null;
                }
                
                // 인보이스 영역 숨기기
                document.getElementById('invoiceContainer').classList.add('hidden');
                
                // 버튼 복원
                const generateBtn = document.getElementById('generateInvoiceBtn');
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i>결제 인보이스 생성';
            }
            // data.status === 'pending'인 경우는 아무것도 하지 않고 계속 확인
        } else {
            // 서버에서 오류 응답
            console.error('결제 상태 확인 오류:', data.error);
        }
    })
    .catch(error => {
        console.error('결제 상태 확인 오류:', error);
    });
}

// 결제 상태 메시지 표시
function showPaymentStatus(type, message) {
    const statusDiv = document.getElementById('paymentStatus');
    const messageDiv = document.getElementById('paymentMessage');
    
    if (!statusDiv || !messageDiv) return;
    
    // 스타일 초기화
    statusDiv.className = 'p-4 rounded-lg border';
    
    // 타입에 따른 스타일 적용
    if (type === 'error') {
        statusDiv.classList.add('status-error');
        messageDiv.innerHTML = `<i class="fas fa-exclamation-circle mr-2"></i>${message}`;
    } else if (type === 'success') {
        statusDiv.classList.add('status-success');
        messageDiv.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${message}`;
    } else {
        statusDiv.classList.add('status-pending');
        messageDiv.innerHTML = `<i class="fas fa-clock mr-2"></i>${message}`;
    }
    
    statusDiv.classList.remove('hidden');
}

// 라이트닝 지갑 열기
function openLightningWallet() {
    if (currentInvoice) {
        const lightningUrl = `lightning:${currentInvoice}`;
        
        // 모바일에서는 직접 링크 열기 시도
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (isMobile) {
            // 모바일에서는 새 창으로 열기
            window.open(lightningUrl, '_blank');
        } else {
            // 데스크톱에서는 숨겨진 링크 생성하여 클릭
            const link = document.createElement('a');
            link.href = lightningUrl;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        // 사용자에게 안내 메시지 표시
        showPaymentStatus('pending', '라이트닝 지갑이 열렸습니다. 결제를 완료해주세요.');
    } else {
        alert('인보이스가 생성되지 않았습니다.');
    }
}

// 인보이스 취소
function cancelInvoice() {
    if (confirm('결제를 취소하시겠습니까?')) {
        const cancelBtn = document.getElementById('cancelInvoiceBtn');
        
        // 취소 버튼 로딩 상태로 변경
        cancelBtn.disabled = true;
        cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> 취소 중...';
        
        // 서버에 취소 요청
        fetch(`/lecture/${window.checkoutData.storeId}/live/${window.checkoutData.liveLectureId}/checkout/cancel_payment/`, {
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
                // 서버 취소 성공
                handleCancelSuccess();
            } else {
                // 서버 취소 실패
                if (data.redirect_url) {
                    // 이미 결제가 완료된 경우 완료 페이지로 리다이렉트
                    window.location.href = data.redirect_url;
                } else {
                    alert('취소 중 오류가 발생했습니다: ' + (data.error || '알 수 없는 오류'));
                    
                    // 취소 버튼 복원
                    cancelBtn.disabled = false;
                    cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
                }
            }
        })
        .catch(error => {
            console.error('취소 요청 중 오류:', error);
            alert('취소 요청 중 오류가 발생했습니다.');
            
            // 취소 버튼 복원
            cancelBtn.disabled = false;
            cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
        });
    }
}

// 취소 성공 처리
function handleCancelSuccess() {
    // 결제 상태 확인 중지
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        paymentCheckInterval = null;
    }
    
    // 🔄 밋업과 동일: 취소 성공 시 페이지 새로고침
    showPaymentStatus('success', '결제가 취소되었습니다. 페이지를 새로고침합니다...');
    
    setTimeout(() => {
        window.location.reload();
    }, 1500);
    
    return; // 아래 로직은 실행하지 않음 (페이지 새로고침으로 대체)
    
    // 인보이스 영역 숨기기
    document.getElementById('invoiceContainer').classList.add('hidden');
    
    // 변수 초기화
    currentPaymentHash = '';
    currentInvoice = '';
    isInvoiceGenerated = false;
    
    // 버튼 복원
    const generateBtn = document.getElementById('generateInvoiceBtn');
    generateBtn.disabled = false;
    generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i>결제 인보이스 생성';
    
    // 상태 메시지 숨기기
    document.getElementById('paymentStatus').classList.add('hidden');
    
    showPaymentStatus('error', '결제가 취소되었습니다.');
    
    // 3초 후 메시지 숨기기
    setTimeout(() => {
        document.getElementById('paymentStatus').classList.add('hidden');
    }, 3000);
} 