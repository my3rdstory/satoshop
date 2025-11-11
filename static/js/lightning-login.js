/**
 * Lightning Login JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    const startLoginBtn = document.getElementById('startLoginBtn');
    const copyLnurlBtn = document.getElementById('copyLnurlBtn');
    const retryBtn = document.getElementById('retryBtn');
    const openWalletBtn = document.getElementById('openWalletBtn');
    const expiredRefreshBtn = document.getElementById('expiredRefreshBtn');
    
    // CSRF 토큰 가져오기
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
                     getCookie('csrftoken');
    
    // 로그인 시작
    if (startLoginBtn) {
        startLoginBtn.addEventListener('click', function() {
            showLoadingState();
            startLightningLogin();
        });
    }
    
    // 다시 시도
    if (retryBtn) {
        retryBtn.addEventListener('click', function() {
            showLoadingState();
            startLightningLogin();
        });
    }
    
    // LNURL 복사
    if (copyLnurlBtn) {
        copyLnurlBtn.addEventListener('click', function() {
            const lnurlText = document.getElementById('lnurlText');
            if (lnurlText) {
                lnurlText.select();
                document.execCommand('copy');
                
                const originalIcon = copyLnurlBtn.innerHTML;
                copyLnurlBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    copyLnurlBtn.innerHTML = originalIcon;
                }, 1000);
            }
        });
    }

    if (openWalletBtn) {
        openWalletBtn.addEventListener('click', () => {
            const lnurlText = document.getElementById('lnurlText');
            if (!lnurlText || !lnurlText.value) return;
            window.location.href = lnurlText.value.trim();
        });
    }

    if (expiredRefreshBtn) {
        expiredRefreshBtn.addEventListener('click', () => {
            expiredRefreshBtn.classList.add('hidden');
            showLoadingState();
            startLightningLogin();
        });
    }
    
    /**
     * CSRF 토큰 가져오기
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * 상태 표시 함수들
     */
    function showInitialState() {
        toggleElements('initialState', ['loadingState', 'qrState', 'successState', 'errorState']);
    }
    
    function showLoadingState() {
        toggleElements('loadingState', ['initialState', 'qrState', 'successState', 'errorState']);
    }
    
    function showQRState() {
        toggleElements('qrState', ['initialState', 'loadingState', 'successState', 'errorState']);
    }
    
    function showSuccessState() {
        toggleElements('successState', ['initialState', 'loadingState', 'qrState', 'errorState']);
    }
    
    function showErrorState(message) {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        toggleElements('errorState', ['initialState', 'loadingState', 'qrState', 'successState']);
    }
    
    /**
     * 요소 표시/숨기기
     */
    function toggleElements(showId, hideIds) {
        // 표시할 요소
        const showElement = document.getElementById(showId);
        if (showElement) {
            showElement.classList.remove('hidden');
        }
        
        // 숨길 요소들
        hideIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.classList.add('hidden');
            }
        });
    }
    
    /**
     * QR 코드 생성
     */
    async function generateQRCode(lnurl) {
        try {
            const qrCodeImage = document.getElementById('qrCodeImage');
            if (!qrCodeImage) {
                console.error('QR 코드 이미지 요소를 찾을 수 없습니다.');
                return;
            }

            // 캔버스 생성
            const canvas = document.createElement('canvas');

            // QRious 인스턴스 생성
            const qr = new QRious({
                element: canvas,
                value: lnurl,
                size: 256,
                foreground: '#000000',
                background: '#FFFFFF',
                level: 'M'
            });

            // 캔버스를 이미지로 변환
            const dataURL = canvas.toDataURL();
            qrCodeImage.src = dataURL;

        } catch (error) {
            console.error('QR Code generation error:', error);
            showErrorState('QR 코드 생성에 실패했습니다. LNURL을 수동으로 복사해주세요.');
        }
    }

    /**
     * 라이트닝 로그인 시작
     */
    async function startLightningLogin() {
        try {
            const nextParam = new URLSearchParams(window.location.search).get('next');
            const url = nextParam ? 
                `/accounts/ln-auth-get-url/?action=login&next=${encodeURIComponent(nextParam)}` :
                '/accounts/ln-auth-get-url/?action=login';
                
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (!data.success) {
                showErrorState(data.error || '로그인 세션 생성에 실패했습니다.');
                return;
            }
            
            // QR 코드 생성
            await generateQRCode(data.lnurl);
            
            // LNURL 텍스트 설정
            const lnurlText = document.getElementById('lnurlText');
            if (lnurlText) {
                lnurlText.value = data.lnurl;
            }
            if (expiredRefreshBtn) expiredRefreshBtn.classList.add('hidden');
            
            showQRState();
            updateStatusMessage('지갑에서 인증을 완료하면 자동으로 로그인됩니다.', 'pending');
            
            // 로그인 상태 확인을 위한 폴링 시작
            startLoginCheckPolling(data.k1);
            
        } catch (error) {
            console.error('Lightning login error:', error);
            showErrorState('네트워크 오류가 발생했습니다.');
        }
    }
    
    /**
     * 로그인 상태 확인 폴링
     */
    function startLoginCheckPolling(k1) {
        let pollCount = 0;
        const maxPolls = 60; // 2분간 확인
        let errorCheckCount = 0;
        
        const checkInterval = setInterval(async () => {
            pollCount++;
            
            if (pollCount >= maxPolls) {
                clearInterval(checkInterval);
                updateStatusMessage('로그인 대기 시간이 만료되었습니다. 새로고침 후 다시 시도해주세요.', 'expired');
                return;
            }
            
            // 라이트닝 인증 상태 확인 API 호출 (k1 포함)
            try {
                const response = await fetch(`/accounts/check-lightning-auth/?k1=${k1}`, {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.authenticated) {
                        clearInterval(checkInterval);
                        
                        const welcomeMsg = data.is_new ? 
                            `${data.username}님 회원가입이 완료되었습니다! 페이지를 이동합니다...` :
                            `${data.username}님으로 로그인이 완료되었습니다! 페이지를 이동합니다...`;
                            
                        updateStatusMessage(welcomeMsg, 'success');
                        showSuccessState();
                        
                        // 2초 후 적절한 페이지로 이동
                        setTimeout(() => {
                            if (data.next_url) {
                                window.location.href = data.next_url;
                            } else {
                                const urlParams = new URLSearchParams(window.location.search);
                                const nextUrl = urlParams.get('next');
                                if (nextUrl) {
                                    window.location.href = decodeURIComponent(nextUrl);
                                } else {
                                    window.location.href = '/accounts/mypage/';
                                }
                            }
                        }, 2000);
                        return;
                    }
                    
                    // 에러가 있는지 확인
                    if (data.error) {
                        clearInterval(checkInterval);
                        let errorMessage = data.error;
                        
                        // 에러 유형에 따른 사용자 친화적 메시지
                        if (errorMessage.includes('이미 등록된')) {
                            errorMessage = '이미 다른 계정에 등록된 라이트닝 지갑입니다.\n다른 지갑을 사용하거나 기존 계정으로 로그인해주세요.';
                        } else if (errorMessage.includes('연동 세션이 만료')) {
                            errorMessage = '연동 세션이 만료되었습니다.\n페이지를 새로고침하고 다시 시도해주세요.';
                        }
                        
                        updateStatusMessage(`오류: ${errorMessage}`, 'error');
                        showErrorState(errorMessage);
                        return;
                    }
                } else if (response.status >= 400) {
                    // 4xx, 5xx 에러 처리
                    errorCheckCount++;
                    if (errorCheckCount >= 3) { // 3번 연속 에러 시 중단
                        clearInterval(checkInterval);
                        let errorMessage = '로그인 처리 중 오류가 발생했습니다.';
                        
                        if (response.status === 400) {
                            errorMessage = '잘못된 요청입니다. 이미 등록된 지갑이거나 세션이 만료되었을 수 있습니다.';
                        }
                        
                        updateStatusMessage(`오류: ${errorMessage}`, 'error');
                        showErrorState(errorMessage);
                        return;
                    }
                }
            } catch (error) {
                console.log('Lightning auth check error:', error);
                errorCheckCount++;
                if (errorCheckCount >= 5) { // 5번 연속 네트워크 에러 시 중단
                    clearInterval(checkInterval);
                    updateStatusMessage('네트워크 오류가 지속되고 있습니다. 페이지를 새로고침해주세요.', 'error');
                    showErrorState('네트워크 연결을 확인하고 다시 시도해주세요.');
                    return;
                }
            }
        }, 2000); // 2초마다 확인
    }
    
    /**
     * 상태 메시지 업데이트
     */
    function updateStatusMessage(message, status) {
        const statusMessage = document.getElementById('statusMessage');
        if (statusMessage) {
            let iconClass;
            switch(status) {
                case 'success':
                    iconClass = 'check';
                    break;
                case 'error':
                case 'expired':
                    iconClass = 'exclamation-triangle';
                    break;
                default:
                    iconClass = 'clock';
            }
            statusMessage.innerHTML = `<i class="fas fa-${iconClass} mr-2"></i>${message}`;
            statusMessage.className = `p-3 rounded-lg border text-sm font-medium status-${status}`;
        }

        if (status === 'expired' && expiredRefreshBtn) {
            expiredRefreshBtn.classList.remove('hidden');
        }
    }

    // 전역 함수로 노출 (필요한 경우)
    window.lightningLogin = {
        showInitialState,
        showLoadingState,
        showQRState,
        showSuccessState,
        showErrorState,
        updateStatusMessage
    };
}); 
