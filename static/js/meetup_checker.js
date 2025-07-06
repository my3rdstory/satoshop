// 밋업체커 JavaScript
let video = null;
let stream = null;
let scanning = false;
let lastScannedCode = null;
let lastScannedTime = 0;
let storeId = null;
let meetupId = null;

// CSRF 토큰 가져오기
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    video = document.getElementById('qr-video');
    
    // URL에서 store_id와 meetup_id 추출
    const pathParts = window.location.pathname.split('/');
    storeId = pathParts[2]; // /meetup/store_id/meetup_id/checker/
    meetupId = pathParts[3];
    
    // 카메라 오류 안내 표시
    showCameraGuidance();
    
    // 버튼 이벤트 리스너
    document.getElementById('start-scanner').addEventListener('click', startScanner);
    document.getElementById('stop-scanner').addEventListener('click', stopScanner);
    document.getElementById('manual-form').addEventListener('submit', handleManualSubmit);
    
    // 수동 입력 필드 엔터키 처리
    document.getElementById('order-number-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleManualSubmit(e);
        }
    });
    
    // 카메라 목록 가져오기
    getCameras();
    
    // 브라우저 지원 확인
    checkBrowserSupport();
});

// 브라우저 지원 확인
function checkBrowserSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('이 브라우저는 카메라 기능을 지원하지 않습니다. 수동 입력을 사용해주세요.', 'warning');
        document.getElementById('start-scanner').disabled = true;
        document.getElementById('start-scanner').classList.add('btn-disabled');
    }
}

// 카메라 사용 안내 표시
function showCameraGuidance() {
    const scannerContainer = document.querySelector('.scanner-container');
    const currentProtocol = window.location.protocol;
    const currentHost = window.location.host;
    
    let isSecureContext = window.isSecureContext;
    
    // localhost나 127.0.0.1이 아니고 HTTP인 경우 경고 표시
    if (!isSecureContext && !currentHost.includes('localhost') && !currentHost.includes('127.0.0.1')) {
        const notice = document.createElement('div');
        notice.className = 'camera-error-notice dark:camera-error-notice.dark';
        notice.innerHTML = `
            <div class="flex items-start">
                <i class="fas fa-exclamation-triangle text-yellow-600 dark:text-yellow-400 mr-3 mt-1"></i>
                <div class="camera-troubleshooting">
                    <h4 class="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">카메라 접근 안내</h4>
                    <p class="text-yellow-700 dark:text-yellow-300 mb-2">카메라 기능은 보안상 HTTPS 또는 localhost에서만 작동합니다.</p>
                    <ul class="text-yellow-700 dark:text-yellow-300 text-sm">
                        <li>• <strong>localhost:8000</strong> 또는 <strong>127.0.0.1:8000</strong>으로 접속하세요</li>
                        <li>• 브라우저에서 카메라 권한을 허용해주세요</li>
                        <li>• 카메라 사용이 어려운 경우 하단의 수동 입력을 이용하세요</li>
                    </ul>
                </div>
            </div>
        `;
        scannerContainer.insertBefore(notice, scannerContainer.firstChild);
    }
}

// 카메라 목록 가져오기
async function getCameras() {
    try {
        // 권한 요청 없이 기본 디바이스 목록만 조회
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        
        const select = document.getElementById('camera-select');
        select.innerHTML = '<option value="">카메라 선택</option>';
        
        videoDevices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.textContent = device.label || `카메라 ${index + 1}`;
            select.appendChild(option);
        });
        
        if (videoDevices.length > 0) {
            select.classList.remove('hidden');
            select.addEventListener('change', switchCamera);
        }
    } catch (error) {
        console.error('카메라 목록 가져오기 실패:', error);
        showCameraPermissionHelp();
    }
}

// 카메라 권한 도움말 표시
function showCameraPermissionHelp() {
    showToast('카메라 권한을 확인해주세요. 브라우저 설정에서 카메라 접근을 허용해주세요.', 'warning');
}

// 카메라 전환
async function switchCamera() {
    const select = document.getElementById('camera-select');
    const deviceId = select.value;
    
    if (scanning && deviceId) {
        await stopScanner();
        await startScanner(deviceId);
    }
}

// 스캐너 시작
async function startScanner(deviceId = null) {
    try {
        const constraints = {
            video: {
                facingMode: deviceId ? undefined : 'environment',
                deviceId: deviceId ? { exact: deviceId } : undefined,
                width: { ideal: 400 },
                height: { ideal: 300 }
            }
        };
        
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = stream;
        await video.play();
        
        scanning = true;
        document.getElementById('start-scanner').classList.add('hidden');
        document.getElementById('stop-scanner').classList.remove('hidden');
        
        // QR 코드 스캔 시작
        scanQRCode();
        
        showToast('카메라가 시작되었습니다. QR 코드를 스캔 영역에 맞춰주세요.', 'success');
        
        // 카메라 시작 성공 시 에러 안내 제거
        const errorNotice = document.querySelector('.camera-error-notice');
        if (errorNotice) {
            errorNotice.style.display = 'none';
        }
        
    } catch (error) {
        console.error('카메라 시작 실패:', error);
        handleCameraError(error);
    }
}

// 카메라 에러 처리
function handleCameraError(error) {
    let errorMessage = '카메라 접근에 실패했습니다. ';
    
    switch (error.name) {
        case 'NotAllowedError':
            errorMessage += '브라우저에서 카메라 권한을 허용해주세요.';
            break;
        case 'NotFoundError':
            errorMessage += '카메라를 찾을 수 없습니다. 다른 카메라를 선택해보세요.';
            break;
        case 'NotReadableError':
            errorMessage += '카메라가 다른 애플리케이션에서 사용 중입니다.';
            break;
        case 'OverconstrainedError':
            errorMessage += '요청한 카메라 설정을 지원하지 않습니다.';
            break;
        case 'SecurityError':
            errorMessage += 'HTTPS 또는 localhost에서만 카메라를 사용할 수 있습니다.';
            break;
        default:
            errorMessage += '수동 입력을 이용해주세요.';
    }
    
    showToast(errorMessage, 'error');
    showDetailedCameraHelp(error);
}

// 자세한 카메라 도움말 표시
function showDetailedCameraHelp(error) {
    const helpModal = document.getElementById('result-modal');
    const title = document.getElementById('modal-title');
    const content = document.getElementById('modal-content');
    
    title.innerHTML = '<i class="fas fa-camera text-blue-600 mr-2"></i>카메라 설정 도움말';
    title.className = 'text-lg font-medium text-blue-600 dark:text-blue-400';
    
    const currentUrl = window.location.href;
    const isHttps = currentUrl.startsWith('https://');
    const isLocalhost = currentUrl.includes('localhost') || currentUrl.includes('127.0.0.1');
    
    content.innerHTML = `
        <div class="space-y-4">
            <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <h4 class="font-semibold text-blue-800 dark:text-blue-200 mb-2">카메라 사용 조건</h4>
                <ul class="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                    <li class="flex items-center">
                        <i class="fas ${isHttps || isLocalhost ? 'fa-check text-green-500' : 'fa-times text-red-500'} mr-2"></i>
                        HTTPS 또는 localhost 필요
                    </li>
                    <li class="flex items-center">
                        <i class="fas fa-info-circle text-blue-500 mr-2"></i>
                        브라우저 카메라 권한 허용 필요
                    </li>
                    <li class="flex items-center">
                        <i class="fas fa-info-circle text-blue-500 mr-2"></i>
                        다른 앱에서 카메라 사용 중이면 접근 불가
                    </li>
                </ul>
            </div>
            
            <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                <h4 class="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">해결 방법</h4>
                <ol class="text-sm text-yellow-700 dark:text-yellow-300 space-y-2">
                    <li>1. 브라우저 주소창 왼쪽의 🔒 아이콘을 클릭</li>
                    <li>2. 카메라 권한을 "허용"으로 변경</li>
                    <li>3. 페이지를 새로고침</li>
                    <li>4. "카메라 시작" 버튼을 다시 클릭</li>
                </ol>
            </div>
            
            <div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <h4 class="font-semibold text-green-800 dark:text-green-200 mb-2">대체 방법</h4>
                <p class="text-sm text-green-700 dark:text-green-300">
                    카메라 사용이 어려운 경우, 오른쪽의 <strong>"주문번호 직접 입력"</strong>을 이용하여 
                    참가자의 티켓에 적힌 주문번호를 수동으로 입력할 수 있습니다.
                </p>
            </div>
        </div>
    `;
    
    helpModal.classList.remove('hidden');
}

// 스캐너 중지
async function stopScanner() {
    scanning = false;
    
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    
    if (video) {
        video.srcObject = null;
    }
    
    document.getElementById('start-scanner').classList.remove('hidden');
    document.getElementById('stop-scanner').classList.add('hidden');
    
    showToast('카메라가 중지되었습니다.', 'info');
}

// QR 코드 스캔
function scanQRCode() {
    if (!scanning || !video) return;
    
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        
        if (code) {
            const now = Date.now();
            // 같은 코드를 3초 내에 재스캔하는 것을 방지
            if (code.data !== lastScannedCode || now - lastScannedTime > 3000) {
                lastScannedCode = code.data;
                lastScannedTime = now;
                handleScannedCode(code.data);
                
                // 스캔 성공 효과
                video.parentElement.classList.add('scan-success-flash');
                setTimeout(() => {
                    video.parentElement.classList.remove('scan-success-flash');
                }, 500);
            }
        }
    }
    
    if (scanning) {
        requestAnimationFrame(scanQRCode);
    }
}

// 스캔된 코드 처리
function handleScannedCode(orderNumber) {
    console.log('QR 코드 스캔됨:', orderNumber);
    
    // 햅틱 피드백 (모바일)
    if (navigator.vibrate) {
        navigator.vibrate(100);
    }
    
    checkAttendance(orderNumber, 'qr');
}

// 수동 입력 처리
function handleManualSubmit(e) {
    e.preventDefault();
    const orderNumber = document.getElementById('order-number-input').value.trim();
    
    if (!orderNumber) {
        showToast('주문번호를 입력해주세요.', 'warning');
        document.getElementById('order-number-input').focus();
        return;
    }
    
    checkAttendance(orderNumber, 'manual');
}

// 참석 확인 처리
async function checkAttendance(orderNumber, source) {
    const submitButton = document.querySelector('#manual-form button[type="submit"]');
    const originalText = submitButton.innerHTML;
    
    try {
        // 로딩 상태 표시
        if (source === 'manual') {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>확인 중...';
        }
        
        const response = await fetch(`/meetup/${storeId}/${meetupId}/check-attendance/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                order_number: orderNumber,
                source: source
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessResult(data.participant, orderNumber);
            updateStats(data.stats);
            addRecentCheck(data.participant, orderNumber, true);
            
            // 수동 입력 필드 초기화
            if (source === 'manual') {
                document.getElementById('order-number-input').value = '';
            }
            
            // 성공 효과음 (선택적)
            playSuccessSound();
            
        } else {
            showErrorResult(data.error, orderNumber);
            addRecentCheck(null, orderNumber, false, data.error);
            
            // 실패 효과음 (선택적)
            playErrorSound();
        }
    } catch (error) {
        console.error('참석 확인 실패:', error);
        showToast('서버 오류가 발생했습니다. 네트워크 연결을 확인해주세요.', 'error');
    } finally {
        // 로딩 상태 해제
        if (source === 'manual') {
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }
    }
}

// 성공 효과음
function playSuccessSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
        // 오디오 컨텍스트 생성 실패 시 무시
    }
}

// 실패 효과음
function playErrorSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(300, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(200, audioContext.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
    } catch (error) {
        // 오디오 컨텍스트 생성 실패 시 무시
    }
}

// 성공 결과 표시
function showSuccessResult(participant, orderNumber) {
    const modal = document.getElementById('result-modal');
    const title = document.getElementById('modal-title');
    const content = document.getElementById('modal-content');
    
    title.innerHTML = '<i class="fas fa-check-circle text-green-600 mr-2"></i>참석 확인 완료';
    title.className = 'text-lg font-medium text-green-600 dark:text-green-400';
    
    content.innerHTML = `
        <div class="text-center result-animation">
            <div class="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <i class="fas fa-check text-3xl text-green-600 dark:text-green-400"></i>
            </div>
            <h4 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">${participant.name}</h4>
            <p class="text-gray-600 dark:text-gray-400 mb-4">${participant.email}</p>
            ${participant.phone ? `<p class="text-sm text-gray-500 dark:text-gray-500 mb-4">${participant.phone}</p>` : ''}
            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p class="text-sm text-gray-600 dark:text-gray-400">주문번호</p>
                <p class="font-mono text-gray-900 dark:text-white">${orderNumber}</p>
            </div>
        </div>
    `;
    
    modal.classList.remove('hidden');
    
    // 음성 피드백 (옵션)
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(`${participant.name}님 참석 확인 완료`);
        utterance.lang = 'ko-KR';
        utterance.rate = 1.2;
        utterance.volume = 0.7;
        speechSynthesis.speak(utterance);
    }
    
    // 자동 모달 닫기 (3초 후)
    setTimeout(() => {
        if (!modal.classList.contains('hidden')) {
            closeModal();
        }
    }, 3000);
}

// 오류 결과 표시
function showErrorResult(error, orderNumber) {
    const modal = document.getElementById('result-modal');
    const title = document.getElementById('modal-title');
    const content = document.getElementById('modal-content');
    
    title.innerHTML = '<i class="fas fa-exclamation-triangle text-red-600 mr-2"></i>확인 실패';
    title.className = 'text-lg font-medium text-red-600 dark:text-red-400';
    
    content.innerHTML = `
        <div class="text-center">
            <div class="w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <i class="fas fa-times text-3xl text-red-600 dark:text-red-400"></i>
            </div>
            <h4 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">참석 확인 실패</h4>
            <p class="text-gray-600 dark:text-gray-400 mb-4">${error}</p>
            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p class="text-sm text-gray-600 dark:text-gray-400">스캔된 주문번호</p>
                <p class="font-mono text-gray-900 dark:text-white break-all">${orderNumber}</p>
            </div>
        </div>
    `;
    
    modal.classList.remove('hidden');
}

// 모달 닫기
function closeModal() {
    document.getElementById('result-modal').classList.add('hidden');
}

// 통계 업데이트
function updateStats(stats) {
    const totalElement = document.getElementById('total-participants');
    const attendedElement = document.getElementById('attended-count');
    const rateElement = document.getElementById('attendance-rate');
    const pendingElement = document.getElementById('pending-count');
    
    // 애니메이션 효과와 함께 업데이트
    animateNumber(totalElement, parseInt(totalElement.textContent), stats.total_participants);
    animateNumber(attendedElement, parseInt(attendedElement.textContent), stats.attended_count);
    animateNumber(pendingElement, parseInt(pendingElement.textContent), stats.total_participants - stats.attended_count);
    
    // 참석률은 소수점 있으므로 별도 처리
    const currentRate = parseFloat(rateElement.textContent.replace('%', ''));
    animatePercentage(rateElement, currentRate, stats.attendance_rate);
}

// 숫자 애니메이션
function animateNumber(element, from, to) {
    const duration = 500;
    const steps = 20;
    const stepValue = (to - from) / steps;
    let current = from;
    let step = 0;
    
    const interval = setInterval(() => {
        step++;
        current += stepValue;
        
        if (step >= steps) {
            current = to;
            clearInterval(interval);
        }
        
        element.textContent = Math.round(current);
        element.parentElement.classList.add('stats-card');
    }, duration / steps);
}

// 퍼센트 애니메이션
function animatePercentage(element, from, to) {
    const duration = 500;
    const steps = 20;
    const stepValue = (to - from) / steps;
    let current = from;
    let step = 0;
    
    const interval = setInterval(() => {
        step++;
        current += stepValue;
        
        if (step >= steps) {
            current = to;
            clearInterval(interval);
        }
        
        element.textContent = current.toFixed(1) + '%';
        element.parentElement.classList.add('stats-card');
    }, duration / steps);
}

// 최근 확인 내역 추가
function addRecentCheck(participant, orderNumber, success, error = null) {
    const container = document.getElementById('recent-checks');
    const now = new Date();
    const timeString = now.toLocaleTimeString('ko-KR');
    
    const item = document.createElement('div');
    item.className = `p-3 rounded-lg border-l-4 transition-all duration-300 ${success ? 'bg-green-50 dark:bg-green-900/20 border-green-500' : 'bg-red-50 dark:bg-red-900/20 border-red-500'}`;
    
    if (success) {
        item.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-medium text-gray-900 dark:text-white">${participant.name}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">${orderNumber}</div>
                    ${participant.phone ? `<div class="text-xs text-gray-500 dark:text-gray-500">${participant.phone}</div>` : ''}
                </div>
                <div class="text-right">
                    <div class="text-sm font-medium text-green-600 dark:text-green-400">참석 확인</div>
                    <div class="text-xs text-gray-500 dark:text-gray-500">${timeString}</div>
                </div>
            </div>
        `;
    } else {
        item.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-medium text-gray-900 dark:text-white">확인 실패</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400 break-all">${orderNumber}</div>
                    <div class="text-xs text-red-600 dark:text-red-400">${error}</div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-medium text-red-600 dark:text-red-400">실패</div>
                    <div class="text-xs text-gray-500 dark:text-gray-500">${timeString}</div>
                </div>
            </div>
        `;
    }
    
    // 애니메이션과 함께 추가
    item.style.opacity = '0';
    item.style.transform = 'translateY(-10px)';
    container.insertBefore(item, container.firstChild);
    
    // 애니메이션 실행
    setTimeout(() => {
        item.style.opacity = '1';
        item.style.transform = 'translateY(0)';
    }, 10);
    
    // 최대 10개 항목만 유지
    while (container.children.length > 10) {
        const lastItem = container.lastChild;
        lastItem.style.opacity = '0';
        lastItem.style.transform = 'translateY(10px)';
        setTimeout(() => {
            if (lastItem.parentNode) {
                container.removeChild(lastItem);
            }
        }, 300);
    }
}

// 토스트 메시지 표시
function showToast(message, type = 'info') {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white transform transition-all duration-300 translate-x-full`;
    
    let icon = '';
    switch (type) {
        case 'success':
            toast.classList.add('bg-green-600');
            icon = '<i class="fas fa-check mr-2"></i>';
            break;
        case 'error':
            toast.classList.add('bg-red-600');
            icon = '<i class="fas fa-exclamation-triangle mr-2"></i>';
            break;
        case 'warning':
            toast.classList.add('bg-yellow-600');
            icon = '<i class="fas fa-exclamation-circle mr-2"></i>';
            break;
        default:
            toast.classList.add('bg-blue-600');
            icon = '<i class="fas fa-info-circle mr-2"></i>';
    }
    
    toast.innerHTML = icon + message;
    document.body.appendChild(toast);
    
    // 애니메이션
    setTimeout(() => {
        toast.classList.remove('translate-x-full');
    }, 100);
    
    // 자동 제거
    setTimeout(() => {
        toast.classList.add('translate-x-full');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }, 4000);
}

// 페이지 종료 시 카메라 정리
window.addEventListener('beforeunload', function() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
});

// ESC 키로 모달 닫기
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// 키보드 단축키
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S: 스캐너 시작/중지
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (scanning) {
            stopScanner();
        } else {
            startScanner();
        }
    }
    
    // Ctrl/Cmd + F: 수동 입력 필드 포커스
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        document.getElementById('order-number-input').focus();
    }
});

// 전역 함수로 내보내기 (템플릿에서 사용)
window.closeModal = closeModal; 