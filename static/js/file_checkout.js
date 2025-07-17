// file_checkout.js - 파일 결제 기능을 위한 JavaScript

let orderId = null;
let checkInterval = null;
let countdownInterval = null;
let expiresAt = null;

// 페이지 로드 시 인보이스 생성
document.addEventListener('DOMContentLoaded', function() {
    createInvoice();
});

// 인보이스 생성
function createInvoice() {
    const loadingState = document.getElementById('loading-state');
    const fileId = window.fileId || document.querySelector('[data-file-id]')?.dataset.fileId;
    
    if (!fileId) {
        showError('파일 정보를 찾을 수 없습니다.');
        return;
    }

    fetch(window.createInvoiceUrl || '/file/api/create-invoice/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            file_id: fileId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('네트워크 응답이 올바르지 않습니다.');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            orderId = data.order_id;
            expiresAt = new Date(data.expires_at);
            showInvoice(data.payment_request);
            startPaymentCheck();
            startCountdown();
        } else {
            showError(data.error || '인보이스 생성에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('인보이스 생성 오류:', error);
        showError('네트워크 오류가 발생했습니다.');
    });
}

// 인보이스 표시
function showInvoice(paymentRequest) {
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('invoice-section').classList.remove('hidden');
    document.getElementById('payment-request').value = paymentRequest;
    
    // QR 코드 생성
    const qrContainer = document.getElementById('qr-code');
    qrContainer.innerHTML = '';
    
    if (typeof QRCode !== 'undefined') {
        QRCode.toCanvas(paymentRequest, {
            width: 256,
            margin: 2,
            color: {
                dark: '#000000',
                light: '#FFFFFF'
            }
        }, function (error, canvas) {
            if (error) {
                console.error('QR 코드 생성 오류:', error);
                qrContainer.innerHTML = '<p class="text-red-500">QR 코드 생성 실패</p>';
            } else {
                qrContainer.appendChild(canvas);
                canvas.style.maxWidth = '100%';
                canvas.style.height = 'auto';
            }
        });
    } else {
        console.error('QRCode 라이브러리가 로드되지 않았습니다.');
        qrContainer.innerHTML = '<p class="text-yellow-500">QR 코드를 표시할 수 없습니다.</p>';
    }
}

// 인보이스 복사
function copyInvoice() {
    const input = document.getElementById('payment-request');
    const button = event.target;
    
    // 입력 필드 선택 및 복사
    input.select();
    input.setSelectionRange(0, 99999); // 모바일 지원
    
    try {
        document.execCommand('copy');
        
        // 피드백
        const originalText = button.textContent;
        const originalClasses = button.className;
        button.textContent = '복사됨!';
        button.classList.add('bg-green-500', 'hover:bg-green-600');
        button.classList.remove('bg-purple-500', 'hover:bg-purple-600');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.className = originalClasses;
        }, 2000);
    } catch (err) {
        console.error('복사 실패:', err);
        alert('복사에 실패했습니다. 수동으로 복사해주세요.');
    }
}

// 결제 상태 확인
function startPaymentCheck() {
    checkInterval = setInterval(() => {
        if (!orderId) return;
        
        fetch(window.checkPaymentUrl || '/file/api/check-payment/', {
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
                
                // 성공 메시지 표시
                showSuccess('결제가 완료되었습니다! 잠시 후 이동합니다...');
                
                // 리다이렉트
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 1500);
            } else if (!data.success) {
                clearInterval(checkInterval);
                clearInterval(countdownInterval);
                showError(data.error || '결제 확인 중 오류가 발생했습니다.');
            }
        })
        .catch(error => {
            console.error('결제 확인 오류:', error);
        });
    }, 1000); // 1초마다 확인
}

// 카운트다운
function startCountdown() {
    countdownInterval = setInterval(() => {
        const now = new Date();
        const remaining = Math.max(0, expiresAt - now);
        
        if (remaining === 0) {
            clearInterval(countdownInterval);
            clearInterval(checkInterval);
            showError('결제 시간이 만료되었습니다.');
            return;
        }
        
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        const countdownElement = document.getElementById('countdown');
        
        if (countdownElement) {
            countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            // 남은 시간이 1분 미만일 때 빨간색으로 표시
            if (remaining < 60000) {
                countdownElement.classList.add('text-red-500', 'font-bold');
            }
        }
    }, 1000);
}

// 결제 취소
function cancelPayment() {
    if (!orderId) {
        window.history.back();
        return;
    }
    
    if (confirm('결제를 취소하시겠습니까?')) {
        clearInterval(checkInterval);
        clearInterval(countdownInterval);
        
        // 취소 요청
        fetch(window.cancelPaymentUrl || '/file/api/cancel-payment/', {
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
                window.history.back();
            } else {
                // 실패해도 뒤로 가기
                window.history.back();
            }
        })
        .catch(() => {
            // 에러 발생 시에도 뒤로 가기
            window.history.back();
        });
    }
}

// 성공 메시지 표시
function showSuccess(message) {
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('invoice-section').classList.add('hidden');
    document.getElementById('error-message').classList.add('hidden');
    
    const successDiv = document.createElement('div');
    successDiv.className = 'bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-800 rounded-lg p-4';
    successDiv.innerHTML = `
        <div class="flex">
            <div class="flex-shrink-0">
                <i class="fas fa-check-circle text-green-400 text-xl"></i>
            </div>
            <div class="ml-3">
                <h3 class="text-sm font-medium text-green-800 dark:text-green-200">결제 성공</h3>
                <div class="mt-2 text-sm text-green-700 dark:text-green-300">
                    <p>${message}</p>
                </div>
            </div>
        </div>
    `;
    
    const paymentSection = document.getElementById('payment-section');
    paymentSection.innerHTML = '';
    paymentSection.appendChild(successDiv);
}

// 에러 표시
function showError(message) {
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('invoice-section').classList.add('hidden');
    document.getElementById('error-message').classList.remove('hidden');
    document.getElementById('error-text').textContent = message;
    
    // 다시 시도 버튼 추가
    const errorMessage = document.getElementById('error-message');
    if (!errorMessage.querySelector('.retry-button')) {
        const retryButton = document.createElement('button');
        retryButton.className = 'retry-button mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors';
        retryButton.textContent = '다시 시도';
        retryButton.onclick = () => location.reload();
        errorMessage.appendChild(retryButton);
    }
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
    if (checkInterval) clearInterval(checkInterval);
    if (countdownInterval) clearInterval(countdownInterval);
});

// 페이지 가시성 변경 감지 (백그라운드 탭 처리)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // 페이지가 백그라운드로 갔을 때
        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
        }
    } else {
        // 페이지가 다시 활성화되었을 때
        if (!checkInterval && orderId && !document.getElementById('error-message').classList.contains('hidden')) {
            startPaymentCheck();
        }
    }
});

// 모바일 장치에서 화면 회전 시 QR 코드 크기 조정
window.addEventListener('orientationchange', () => {
    setTimeout(() => {
        const canvas = document.querySelector('#qr-code canvas');
        if (canvas) {
            canvas.style.maxWidth = '100%';
            canvas.style.height = 'auto';
        }
    }, 300);
});