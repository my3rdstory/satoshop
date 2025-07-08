let currentPaymentHash = '';
let currentInvoice = '';
let paymentCheckInterval = null;
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
    
    // 페이지 초기화
    if (checkoutData.isPaymentPage) {
        initPaymentPage();
    }
});

// 결제 페이지 초기화
function initPaymentPage() {
    // 인보이스 생성 버튼 스타일 설정
    const generateBtn = document.getElementById('generateInvoiceBtn');
    if (generateBtn) {
        generateBtn.classList.add('invoice-btn');
    }
    
    // 무료 참가 신청 폼 이벤트 리스너 추가
    const freeParticipationForm = document.getElementById('free-participation-form');
    
    if (freeParticipationForm) {
        freeParticipationForm.addEventListener('submit', function(event) {
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
            }
            
            // 폼 제출은 계속 진행 (event.preventDefault() 호출하지 않음)
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
    
    // 인보이스 생성 요청 (임시 - 나중에 실제 API로 교체)
    setTimeout(() => {
        // 임시로 에러 메시지 표시
        showPaymentStatus('결제 서비스가 아직 구현되지 않았습니다.', 'error');
        
        // 버튼 복원
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
        
        // 로딩 숨기기
        loadingSpinner.classList.add('hidden');
    }, 2000);
    
    // 실제 구현 시 아래 주석을 해제하고 위의 setTimeout을 제거
    /*
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
    });
    */
}

// QR 코드 생성
function generateQRCode(invoice) {
    const qrCodeImage = document.getElementById('qrCodeImage');
    
    const qr = new QRious({
        element: qrCodeImage,
        value: invoice,
        size: 250,
        background: 'white',
        foreground: 'black',
        level: 'M'
    });
}

// 인보이스 클립보드에 복사
function copyInvoiceToClipboard() {
    const invoiceTextArea = document.getElementById('invoiceTextArea');
    if (invoiceTextArea && invoiceTextArea.value) {
        invoiceTextArea.select();
        navigator.clipboard.writeText(invoiceTextArea.value).then(function() {
            // 성공 메시지
            const btn = event.target.closest('button');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check mr-1"></i> 복사됨!';
            btn.classList.add('text-green-600');
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('text-green-600');
            }, 2000);
        }).catch(function(err) {
            console.error('클립보드 복사 실패:', err);
            // 폴백: 구식 방법
            try {
                document.execCommand('copy');
                alert('인보이스가 클립보드에 복사되었습니다.');
            } catch (e) {
                alert('클립보드 복사에 실패했습니다. 수동으로 복사해주세요.');
            }
        });
    }
}

// 결제 상태 확인 시작
function startPaymentStatusCheck() {
    if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
    }
    
    // 즉시 한 번 확인
    checkPaymentStatus();
    
    // 5초마다 확인
    paymentCheckInterval = setInterval(checkPaymentStatus, 5000);
}

// 결제 상태 확인
function checkPaymentStatus() {
    if (!currentPaymentHash) {
        return;
    }
    
    // 실제 구현 시 아래 주석을 해제
    /*
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
    .then(response => response.json())
    .then(data => {
        if (data.paid) {
            // 결제 완료
            showPaymentStatus('결제가 완료되었습니다! 잠시 후 참가 확정 페이지로 이동합니다.', 'success');
            
            // 결제 상태 확인 중지
            if (paymentCheckInterval) {
                clearInterval(paymentCheckInterval);
                paymentCheckInterval = null;
            }
            
            // 3초 후 참가 확정 페이지로 이동
            setTimeout(() => {
                window.location.href = `/lecture/${window.checkoutData.storeId}/live/${window.checkoutData.liveLectureId}/complete/${data.order_id}/`;
            }, 3000);
            
        } else if (data.expired) {
            // 결제 만료
            showPaymentStatus('결제 시간이 만료되었습니다. 다시 시도해주세요.', 'error');
            
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
            generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
        }
    })
    .catch(error => {
        console.error('결제 상태 확인 오류:', error);
    });
    */
}

// 결제 상태 메시지 표시
function showPaymentStatus(message, type) {
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
        showPaymentStatus('라이트닝 지갑이 열렸습니다. 결제를 완료해주세요.', 'pending');
    } else {
        alert('인보이스가 생성되지 않았습니다.');
    }
}

// 인보이스 취소
function cancelInvoice() {
    if (confirm('결제를 취소하시겠습니까?')) {
        // 결제 상태 확인 중지
        if (paymentCheckInterval) {
            clearInterval(paymentCheckInterval);
            paymentCheckInterval = null;
        }
        
        // 인보이스 영역 숨기기
        document.getElementById('invoiceContainer').classList.add('hidden');
        
        // 변수 초기화
        currentPaymentHash = '';
        currentInvoice = '';
        isInvoiceGenerated = false;
        
        // 버튼 복원
        const generateBtn = document.getElementById('generateInvoiceBtn');
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-qrcode mr-3"></i> 결제 인보이스 생성';
        
        // 상태 메시지 숨기기
        document.getElementById('paymentStatus').classList.add('hidden');
        
        showPaymentStatus('결제가 취소되었습니다.', 'error');
        
        // 3초 후 메시지 숨기기
        setTimeout(() => {
            document.getElementById('paymentStatus').classList.add('hidden');
        }, 3000);
    }
} 