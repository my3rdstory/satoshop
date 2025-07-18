// file_checkout.js - 파일 결제 기능을 위한 JavaScript

let orderId = null;
let checkInterval = null;
let countdownInterval = null;
let expiresAt = null;
let currentPaymentHash = null;
let currentInvoice = null;

// 페이지 로드 시
 document.addEventListener('DOMContentLoaded', function() {
    // 모바일 디바이스 감지 및 주의사항 표시
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (isMobile) {
        // 모바일 환경에서만 주의사항 박스 표시
        const mobileWarning = document.getElementById('mobilePaymentWarning');
        if (mobileWarning) {
            mobileWarning.classList.remove('hidden');
        }
    }
    
    // 페이지 포커스 이벤트 리스너 추가 (모바일 결제 후 돌아왔을 때)
    window.addEventListener('focus', function() {
        if (currentPaymentHash) {
            console.log('페이지 포커스 - 결제 상태 즉시 확인');
            checkPaymentStatus();
        }
    });
    
    // 페이지 가시성 변경 이벤트 리스너 추가 (모바일 백그라운드에서 복귀 시)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && currentPaymentHash) {
            console.log('페이지 가시성 변경 - 결제 상태 즉시 확인');
            checkPaymentStatus();
            
            // 인터벌이 중단되었을 수 있으므로 재시작
            if (checkInterval) {
                clearInterval(checkInterval);
            }
            startPaymentCheck();
        }
    });
});

// 인보이스 생성
function generateInvoice() {
    const generateBtn = document.getElementById('generateInvoiceBtn');
    const invoiceContainer = document.getElementById('invoiceContainer');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const qrCodeCanvas = document.getElementById('qrCodeCanvas');
    const fileId = window.fileId || document.querySelector('[data-file-id]')?.dataset.fileId;
    
    if (!fileId) {
        showPaymentStatus('파일 정보를 찾을 수 없습니다.', 'error');
        return;
    }
    
    // 버튼 비활성화 및 로딩 표시
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-3"></i> 생성 중...';
    
    // 기존 결제 상태 확인 중지
    if (checkInterval) {
        clearInterval(checkInterval);
        checkInterval = null;
    }
    
    // 인보이스 컨테이너 표시 및 로딩 스피너 표시
    invoiceContainer.classList.remove('hidden');
    loadingSpinner.classList.remove('hidden');
    qrCodeCanvas.classList.add('hidden');

    fetch(window.createInvoiceUrl || '/file/ajax/create-invoice/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            file_id: fileId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 인보이스 생성 성공
            currentPaymentHash = data.payment_hash;
            currentInvoice = data.payment_request;
            orderId = data.order_id;
            expiresAt = new Date(data.expires_at);
            
            // QR 코드 생성
            generateQRCode(data.payment_request);
            
            // 인보이스 텍스트 표시
            document.getElementById('invoiceTextArea').value = data.payment_request;
            
            // 라이트닝 지갑 열기 버튼 표시
            document.getElementById('lightningWalletButton').classList.remove('hidden');
            
            // 결제 상태 확인 시작
            startPaymentCheck();
            
            showPaymentStatus('결제를 기다리고 있습니다. QR 코드를 스캔하거나 인보이스를 복사하여 결제해주세요.', 'pending');
            
            // 버튼 텍스트 변경
            generateBtn.innerHTML = '<i class="fas fa-check mr-3"></i> 인보이스 생성됨';
        } else {
            // 인보이스 생성 실패
            showPaymentStatus(data.error || '인보이스 생성에 실패했습니다.', 'error');
            
            // 버튼 복원
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
            
            // 로딩 숨기기
            loadingSpinner.classList.add('hidden');
            
            // 라이트닝 지갑 버튼 숨기기
            document.getElementById('lightningWalletButton').classList.add('hidden');
        }
    })
    .catch(error => {
        console.error('인보이스 생성 오류:', error);
        showPaymentStatus('인보이스 생성 중 오류가 발생했습니다.', 'error');
        
        // 버튼 복원
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
        
        // 로딩 숨기기
        loadingSpinner.classList.add('hidden');
        
        // 라이트닝 지갑 버튼 숨기기
        document.getElementById('lightningWalletButton').classList.add('hidden');
    });
}

// QR 코드 생성
function generateQRCode(invoice) {
    try {
        const qr = new QRious({
            element: document.getElementById('qrCodeCanvas'),
            value: invoice,
            size: 250,
            level: 'M'
        });
        
        // QR 코드 표시
        document.getElementById('loadingSpinner').classList.add('hidden');
        document.getElementById('qrCodeCanvas').classList.remove('hidden');
    } catch (error) {
        console.error('QR 코드 생성 오류:', error);
        // QR 코드 생성 실패 시 대체 텍스트 표시
        document.getElementById('qrCodeContainer').innerHTML = '<p class="text-red-500">QR 코드 생성 실패</p>';
    }
}

// 인보이스 복사
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
            showPaymentStatus('결제를 기다리고 있습니다...', 'pending');
        }, 3000);
    }
}

// 라이트닝 지갑 열기
function openLightningWallet() {
    if (currentInvoice) {
        const lightningUri = `lightning:${currentInvoice}`;
        window.location.href = lightningUri;
        
        // 모바일 환경에서는 지갑 열기 후 자동 결제 확인 강화
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            // 기존 interval 중지
            if (checkInterval) {
                clearInterval(checkInterval);
            }
            // 1초마다 더 자주 확인
            checkInterval = setInterval(checkPaymentStatus, 1000);
            
            // 5초 후 한 번 더 확인 (지갑에서 돌아올 시간 고려)
            setTimeout(() => {
                if (currentPaymentHash) {
                    console.log('지갑 열기 후 5초 - 결제 상태 확인');
                    checkPaymentStatus();
                }
            }, 5000);
        }
    }
}

// 결제 상태 확인
function checkPaymentStatus() {
    if (!currentPaymentHash || !orderId) {
        // 필수 정보가 없으면 타이머 정리
        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
        }
        return;
    }
    
    fetch(window.checkPaymentUrl || '/file/ajax/check-payment/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            order_id: orderId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.paid) {
            clearInterval(checkInterval);
            clearInterval(countdownInterval);
            
            showPaymentStatus('결제가 완료되었습니다! 잠시 후 이동합니다...', 'success');
            
            // 리다이렉트
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 1500);
        } else if (!data.success && data.error) {
            clearInterval(checkInterval);
            clearInterval(countdownInterval);
            showPaymentStatus(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('결제 확인 오류:', error);
    });
}

// 결제 상태 확인 시작
function startPaymentCheck() {
    if (checkInterval) {
        clearInterval(checkInterval);
    }
    
    checkInterval = setInterval(checkPaymentStatus, 1000); // 1초마다 확인
}

// 결제 상태 메시지 표시
function showPaymentStatus(message, type) {
    const statusElement = document.getElementById('paymentStatus');
    const messageElement = document.getElementById('paymentMessage');
    
    if (!statusElement || !messageElement) return;
    
    statusElement.classList.remove('hidden', 'status-pending', 'status-success', 'status-error');
    
    // 타입에 따른 스타일 설정
    switch(type) {
        case 'pending':
            statusElement.classList.add('status-pending');
            messageElement.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>${message}`;
            break;
        case 'success':
            statusElement.classList.add('status-success');
            messageElement.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${message}`;
            break;
        case 'error':
            statusElement.classList.add('status-error');
            messageElement.innerHTML = `<i class="fas fa-exclamation-circle mr-2"></i>${message}`;
            break;
        default:
            messageElement.textContent = message;
    }
}

// 결제 취소
function cancelPayment() {
    if (!currentPaymentHash) {
        showPaymentStatus('취소할 인보이스가 없습니다.', 'error');
        return;
    }
    
    if (!confirm('정말로 결제를 취소하시겠습니까?')) {
        return;
    }
    
    // 즉시 타이머 정리
    if (checkInterval) {
        clearInterval(checkInterval);
        checkInterval = null;
    }
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
    
    const cancelBtn = document.getElementById('cancelInvoiceBtn');
    cancelBtn.disabled = true;
    cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> 취소 중...';
    
    fetch(window.cancelPaymentUrl || '/file/ajax/cancel-payment/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            order_id: orderId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 결제 상태 확인 중지
            if (checkInterval) {
                clearInterval(checkInterval);
                checkInterval = null;
            }
            
            // 현재 인보이스 정보 초기화
            currentPaymentHash = null;
            currentInvoice = null;
            orderId = null;
            
            // 성공 메시지 표시
            showPaymentStatus('결제가 취소되었습니다.', 'error');
            
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
            
            // 페이지 새로고침 전에 모든 타이머 확실히 정리
            if (checkInterval) {
                clearInterval(checkInterval);
                checkInterval = null;
            }
            if (countdownInterval) {
                clearInterval(countdownInterval);
                countdownInterval = null;
            }
            
            // 페이지 새로고침으로 UI 초기화
            setTimeout(() => {
                showPaymentStatus('결제 화면을 초기화합니다...', 'info');
                window.location.reload();
            }, 1000);
            
        } else {
            // 결제가 이미 완료된 경우 처리
            if (data.redirect_url) {
                // 결제 상태 확인 중지
                if (checkInterval) {
                    clearInterval(checkInterval);
                    checkInterval = null;
                }
                
                showPaymentStatus('결제가 이미 완료되었습니다. 잠시 후 이동합니다...', 'success');
                
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 1500);
            } else {
                showPaymentStatus(data.error || '취소 중 오류가 발생했습니다.', 'error');
                cancelBtn.disabled = false;
                cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
            }
        }
    })
    .catch(error => {
        showPaymentStatus('취소 중 오류가 발생했습니다.', 'error');
        cancelBtn.disabled = false;
        cancelBtn.innerHTML = '<i class="fas fa-times mr-2"></i> 결제 취소';
    });
}

// 성공 메시지 표시
function showSuccess(message) {
    showPaymentStatus(message, 'success');
}

// 에러 표시
function showError(message) {
    showPaymentStatus(message, 'error');
}

// CSRF 토큰 가져오기
function getCsrfToken() {
    // 전역 변수에서 먼저 확인
    if (window.csrfToken) {
        return window.csrfToken;
    }
    
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenElement) {
        return tokenElement.value;
    }
    
    // 쿠키에서 가져오기
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

// 페이지 떠날 때 정리
window.addEventListener('beforeunload', () => {
    if (checkInterval) {
        clearInterval(checkInterval);
        checkInterval = null;
    }
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
});