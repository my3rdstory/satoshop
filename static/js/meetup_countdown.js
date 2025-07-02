// 밋업 카운트다운 공통 기능
class MeetupCountdown {
    constructor(options = {}) {
        this.countdownInterval = null;
        this.currentExpiresAt = null;
        this.originalReservationExpiresAt = null;
        
        // 설정
        this.storeId = options.storeId;
        this.meetupId = options.meetupId;
        this.reservationExpiresAt = options.reservationExpiresAt;
        
        // DOM 요소
        this.countdownDisplay = document.getElementById('countdown-display');
        this.floatingCountdown = document.getElementById('floating-countdown');
        this.countdownLabel = document.querySelector('.countdown-label');
        
        // 초기화
        this.init();
    }
    
    init() {
        if (!this.reservationExpiresAt) {
            console.log('예약 만료 시간이 없어서 카운트다운을 표시하지 않음');
            return;
        }
        
        if (!this.countdownDisplay || !this.floatingCountdown) {
            console.log('카운트다운 DOM 요소를 찾을 수 없음');
            return;
        }
        
        // 원본 예약 시간 저장
        this.originalReservationExpiresAt = this.reservationExpiresAt;
        this.currentExpiresAt = this.originalReservationExpiresAt;
        
        console.log('카운트다운 초기화:', {
            reservationExpiresAt: this.reservationExpiresAt,
            originalReservationExpiresAt: this.originalReservationExpiresAt,
            currentExpiresAt: this.currentExpiresAt
        });
        
        // 기본적으로 예약 모드로 설정
        if (this.floatingCountdown) {
            this.floatingCountdown.classList.add('reservation-mode');
        }
        
        // 카운트다운 표시
        setTimeout(() => {
            this.floatingCountdown.classList.add('show');
        }, 1000);
        
        // 카운트다운 시작
        this.startCountdown();
        
        // 페이지 벗어날 때 예약 해제
        this.setupPageLeaveHandlers();
    }
    
    startCountdown() {
        console.log('카운트다운 시작:', this.currentExpiresAt);
        
        if (!this.countdownDisplay || !this.floatingCountdown || !this.currentExpiresAt) {
            console.log('카운트다운 시작 실패 - 필수 요소 누락');
            return;
        }
        
        // 기존 카운트다운 정리
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
        
        this.countdownInterval = setInterval(() => {
            const now = new Date();
            const expiresAt = new Date(this.currentExpiresAt);
            const timeLeft = expiresAt - now;
            
            if (timeLeft <= 0) {
                // 시간 만료
                clearInterval(this.countdownInterval);
                this.countdownDisplay.textContent = '00:00';
                this.floatingCountdown.classList.add('urgent');
                
                // 페이지 리다이렉트
                setTimeout(() => {
                    alert('예약 시간이 만료되었습니다. 다시 시도해주세요.');
                    window.location.href = `/meetup/${this.storeId}/${this.meetupId}/`;
                }, 2000);
                return;
            }
            
            // 시간 계산
            const minutes = Math.floor(timeLeft / 60000);
            const seconds = Math.floor((timeLeft % 60000) / 1000);
            
            // 시간 표시 형식
            const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            this.countdownDisplay.textContent = timeString;
            
            // 1분 미만일 때 긴급 스타일 적용
            if (timeLeft < 60000) {
                this.floatingCountdown.classList.add('urgent');
            } else {
                this.floatingCountdown.classList.remove('urgent');
            }
            
            // 30초 미만일 때 추가 경고
            if (timeLeft < 30000 && timeLeft > 25000) {
                this.showWarningNotification('예약 시간이 30초 남았습니다!');
            }
            
        }, 1000);
    }
    
    // 카운트다운 만료 시간 업데이트 (인보이스 생성/취소 시 사용)
    updateExpiration(newExpiresAt) {
        console.log('카운트다운 만료 시간 업데이트:', newExpiresAt);
        this.currentExpiresAt = newExpiresAt;
        
        // 카운트다운 재시작
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
        this.startCountdown();
        
        // 카운트다운 레이블 업데이트
        if (this.countdownLabel) {
            if (newExpiresAt === this.originalReservationExpiresAt) {
                this.countdownLabel.textContent = '예약 시간 남음';
            } else {
                this.countdownLabel.textContent = '결제 시간 남음';
            }
        }
    }
    
    // 원본 예약 시간으로 복원 (인보이스 취소 시 사용)
    resetToOriginalExpiration() {
        console.log('원본 예약 시간으로 복원');
        this.updateExpiration(this.originalReservationExpiresAt);
    }
    
    // 인보이스 생성 시 카운트다운을 결제 시간으로 변경
    switchToPaymentMode(paymentExpiresAt) {
        console.log('🔄 결제 모드로 전환:', paymentExpiresAt);
        
        // 부드러운 전환을 위해 잠깐 숨기기
        this.hide();
        
        setTimeout(() => {
            // 결제 시간으로 업데이트
            this.updateExpiration(paymentExpiresAt);
            
            // 스타일 변경 (결제 모드 표시)
            if (this.floatingCountdown) {
                this.floatingCountdown.classList.add('payment-mode');
                this.floatingCountdown.classList.remove('reservation-mode');
            }
            
            // 라벨 변경
            if (this.countdownLabel) {
                this.countdownLabel.textContent = '결제 시간 남음';
            }
            
            // 다시 표시
            this.show();
        }, 300); // 300ms 후 결제 모드로 전환하여 표시
    }
    
    // 인보이스 취소 시 카운트다운을 예약 시간으로 복원
    switchToReservationMode() {
        console.log('🔄 예약 모드로 복원');
        
        // 부드러운 전환을 위해 잠깐 숨기기
        this.hide();
        
        setTimeout(() => {
            // 원래 예약 시간으로 복원
            this.updateExpiration(this.originalReservationExpiresAt);
            
            // 스타일 변경 (예약 모드 표시)
            if (this.floatingCountdown) {
                this.floatingCountdown.classList.add('reservation-mode');
                this.floatingCountdown.classList.remove('payment-mode');
            }
            
            // 라벨 변경
            if (this.countdownLabel) {
                this.countdownLabel.textContent = '예약 시간 남음';
            }
            
            // 다시 표시
            this.show();
        }, 300); // 300ms 후 예약 모드로 전환하여 표시
    }
    
    // 카운트다운 표시
    show() {
        console.log('👁️ 카운트다운 표시');
        if (this.floatingCountdown) {
            this.floatingCountdown.classList.remove('hidden');
            this.floatingCountdown.classList.add('show');
            console.log('✅ 카운트다운 표시 완료');
        }
    }
    
    // 카운트다운 숨기기 (완전히 숨김)
    hide() {
        console.log('👻 카운트다운 숨기기');
        if (this.floatingCountdown) {
            this.floatingCountdown.classList.remove('show');
            this.floatingCountdown.classList.add('hidden');
            console.log('✅ 카운트다운 숨기기 완료');
        }
    }
    
    // 경고 알림 표시
    showWarningNotification(message) {
        // 기존 알림이 있으면 제거
        const existingNotification = document.getElementById('warning-notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        // 새로운 알림 생성
        const notification = document.createElement('div');
        notification.id = 'warning-notification';
        notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 animate-bounce';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // 3초 후 자동 제거
        setTimeout(() => {
            if (notification && notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
    
    // 페이지 벗어날 때 예약 해제 설정
    setupPageLeaveHandlers() {
        if (!this.storeId || !this.meetupId) {
            return;
        }
        
        // 페이지 벗어날 때 예약 해제
        window.addEventListener('beforeunload', () => {
            this.releaseReservation();
        });
        
        // 페이지 숨김/표시 변경 시 (모바일 브라우저 대응)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.releaseReservation();
            }
        });
    }
    
    // 예약 해제 요청
    releaseReservation() {
        if (!this.storeId || !this.meetupId) {
            return;
        }
        
        const url = `/meetup/${this.storeId}/${this.meetupId}/release_reservation/`;
        
        // sendBeacon API 사용 (페이지 언로드 시에도 요청 보장)
        if (navigator.sendBeacon) {
            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', this.getCsrfToken());
            navigator.sendBeacon(url, formData);
        } else {
            // sendBeacon을 지원하지 않는 브라우저용 fallback
            try {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', url, false); // 동기 요청
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.send(`csrfmiddlewaretoken=${this.getCsrfToken()}`);
            } catch (e) {
                console.log('예약 해제 요청 실패:', e);
            }
        }
    }
    
    // CSRF 토큰 가져오기
    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) {
            return token.value;
        }
        
        // 메타 태그에서 찾기
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        // 쿠키에서 찾기
        const name = 'csrftoken';
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
        return cookieValue || '';
    }
    
    // 카운트다운 정리
    destroy() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
    }
    
    // 카운트다운 중지 및 숨기기 (무료 밋업 결제 시 사용)
    stopAndHide() {
        console.log('🛑 카운트다운 중지 및 숨기기');
        
        // 카운트다운 인터벌 중지
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
            console.log('⏹️ 카운트다운 인터벌 중지됨');
        }
        
        // 플로팅 카운트다운 숨기기
        if (this.floatingCountdown) {
            this.floatingCountdown.classList.remove('show');
            this.floatingCountdown.classList.add('hidden');
            console.log('👻 플로팅 카운트다운 숨김');
        }
    }
}

// 전역에서 사용할 수 있도록 window 객체에 등록
window.MeetupCountdown = MeetupCountdown; 