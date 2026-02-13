/**
 * 라이트닝 인증 연동 페이지 JavaScript (신규 LNURL 방식)
 */

document.addEventListener('DOMContentLoaded', function() {
    const startLinkingBtn = document.getElementById('startLinkingBtn');
    const copyLnurlBtn = document.getElementById('copyLnurlBtn');
    const retryBtn = document.getElementById('retryBtn');
    
    // CSRF 토큰 가져오기
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
                     getCookie('csrftoken');
    
    // 연동 시작
    if (startLinkingBtn) {
        startLinkingBtn.addEventListener('click', function() {
            showLoadingState();
            startLightningLinking();
        });
    }
    
    // 다시 시도
    if (retryBtn) {
        retryBtn.addEventListener('click', function() {
            showLoadingState();
            startLightningLinking();
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
            // QRious 라이브러리 사용
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
     * 라이트닝 연동 시작
     */
    async function startLightningLinking() {
        try {
            const response = await fetch('/accounts/ln-auth-get-link/?action=link', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (!data.success) {
                showErrorState(data.error || '연동 세션 생성에 실패했습니다.');
                return;
            }
            
            // k1 값을 전역 변수로 저장 (폴링에서 사용)
            window.currentK1 = data.k1;
            
            // QR 코드 생성
            await generateQRCode(data.lnurl);
            
            // LNURL 텍스트 설정
            const lnurlText = document.getElementById('lnurlText');
            if (lnurlText) {
                lnurlText.value = data.lnurl;
            }
            
            showQRState();
            
            // 새로운 방식에서는 콜백에서 바로 처리됨
            updateStatusMessage('지갑에서 인증을 완료하면 자동으로 연동됩니다.', 'pending');
            
            // 성공 확인을 위한 간단한 폴링 (선택적)
            startLinkCheckPolling();
            
        } catch (error) {
            console.error('Lightning linking error:', error);
            showErrorState('네트워크 오류가 발생했습니다.');
        }
    }
    
    /**
     * 연동 상태 확인 (옵션)
     */
    function startLinkCheckPolling() {
        let pollCount = 0;
        const maxPolls = 60; // 2분간 확인
        let errorCheckCount = 0;
        
        console.log('🔄 연동 상태 폴링 시작, k1:', window.currentK1 ? window.currentK1.substring(0, 16) + '...' : 'undefined');
        
        const checkInterval = setInterval(async () => {
            pollCount++;
            
            if (pollCount >= maxPolls) {
                clearInterval(checkInterval);
                updateStatusMessage('연동 대기 시간이 만료되었습니다. 새로고침 후 다시 시도해주세요.', 'expired');
                return;
            }
            
            // API를 통한 연동 상태 확인
            try {
                const url = window.currentK1 ? 
                    `/accounts/ln-auth-check-link/?k1=${encodeURIComponent(window.currentK1)}` : 
                    '/accounts/ln-auth-check-link/';
                
                console.log(`📡 폴링 #${pollCount}: ${url}`);
                    
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log(`✅ 폴링 응답 #${pollCount}:`, data);
                    
                    if (data.success && data.linked) {
                        clearInterval(checkInterval);
                        updateStatusMessage('연동이 완료되었습니다! 마이페이지로 이동합니다...', 'success');
                        showSuccessState();
                        
                        // 2초 후 마이페이지로 이동
                        setTimeout(() => {
                            window.location.href = '/accounts/mypage/';
                        }, 2000);
                        return;
                    }
                    
                    // 에러가 있는지 확인
                    if (data.error || (!data.success && data.error)) {
                        console.log('🚨 에러 감지:', data.error);
                        clearInterval(checkInterval);
                        let errorMessage = data.error || '연동 처리 중 오류가 발생했습니다.';
                        
                        // 에러 유형에 따른 사용자 친화적 메시지
                        if (errorMessage.includes('이미 다른 계정에 등록된')) {
                            errorMessage = '이미 다른 계정에 등록된 라이트닝 지갑입니다.\n다른 지갑을 사용해주세요.';
                        } else if (errorMessage.includes('이미 다른 라이트닝 지갑이 연동')) {
                            errorMessage = '이미 다른 라이트닝 지갑이 연동되어 있습니다.\n기존 연동을 해제한 후 다시 시도해주세요.';
                        } else if (errorMessage.includes('연동 세션이 만료')) {
                            errorMessage = '연동 세션이 만료되었습니다.\n페이지를 새로고침하고 다시 시도해주세요.';
                        }
                        
                        console.log('🚨 사용자에게 표시할 에러:', errorMessage);
                        updateStatusMessage(`오류: ${errorMessage}`, 'error');
                        showErrorState(errorMessage);
                        return;
                    }
                } else if (response.status >= 400) {
                    // 4xx, 5xx 에러 처리
                    errorCheckCount++;
                    if (errorCheckCount >= 3) { // 3번 연속 에러 시 중단
                        clearInterval(checkInterval);
                        let errorMessage = '연동 처리 중 오류가 발생했습니다.';
                        
                        if (response.status === 400) {
                            errorMessage = '잘못된 요청입니다. 이미 등록된 지갑이거나 세션이 만료되었을 수 있습니다.';
                        }
                        
                        updateStatusMessage(`오류: ${errorMessage}`, 'error');
                        showErrorState(errorMessage);
                        return;
                    }
                }
            } catch (error) {
                console.log('Link check error:', error);
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
            const iconClass = status === 'pending' ? 'clock' : 
                            status === 'expired' ? 'exclamation-triangle' : 
                            status === 'success' ? 'check-circle' : 'check';
            statusMessage.innerHTML = `<i class="fas fa-${iconClass} mr-2"></i>${message}`;
            statusMessage.className = `p-3 rounded-lg border text-sm font-medium status-${status}`;
        }
    }
}); 