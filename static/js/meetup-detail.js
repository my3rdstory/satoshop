// 밋업 디테일 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 밋업 데이터 가져오기
    const meetupDataElement = document.getElementById('meetup-data');
    const meetupData = meetupDataElement ? JSON.parse(meetupDataElement.textContent) : {};
    
    // 선택된 옵션들
    let selectedOptions = {};
    
    // 마크다운 렌더링
    if (typeof marked !== 'undefined' && typeof renderMarkdown === 'function') {
        renderMarkdown();
    }
    
    // 이벤트 리스너 설정
    initializeEventListeners();
    
    // 카운트다운 초기화
    initializeCountdown();
    
    function initializeEventListeners() {
        // 전역 함수로 노출
        window.changeMainImage = changeMainImage;
        window.selectOption = selectOption;
        window.joinMeetup = joinMeetup;
    }
    
    // 카운트다운 초기화 및 시작
    function initializeCountdown() {
        const countdownDataElement = document.getElementById('countdown-data');
        if (!countdownDataElement) return;
        
        try {
            const countdownData = JSON.parse(countdownDataElement.textContent);
            const endDateTime = new Date(countdownData.endDateTime);
            
            // 카운트다운 시작
            startCountdown(endDateTime);
        } catch (error) {
            console.error('카운트다운 데이터 파싱 오류:', error);
        }
    }
    
    // 카운트다운 실행
    function startCountdown(endDateTime) {
        const countdownElement = document.getElementById('countdown');
        const overlayElement = document.getElementById('countdownOverlay');
        
        if (!countdownElement || !overlayElement) return;
        
        function updateCountdown() {
            const now = new Date().getTime();
            const endTime = endDateTime.getTime();
            const distance = endTime - now;
            
            if (distance < 0) {
                // 카운트다운 종료
                countdownElement.innerHTML = '<span class="text-red-300">할인 마감</span>';
                overlayElement.classList.add('countdown-expired');
                overlayElement.querySelector('.text-sm.mt-2').textContent = '조기등록 할인이 종료되었습니다';
                return;
            }
            
            // 시간 계산
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            // 화면에 표시
            document.getElementById('days').textContent = String(days).padStart(2, '0');
            document.getElementById('hours').textContent = String(hours).padStart(2, '0');
            document.getElementById('minutes').textContent = String(minutes).padStart(2, '0');
            document.getElementById('seconds').textContent = String(seconds).padStart(2, '0');
            
            // 1분 미만일 때 강조 효과
            if (distance < 60000) { // 1분 미만
                countdownElement.classList.add('countdown-pulse');
                overlayElement.style.background = 'rgba(239, 68, 68, 0.7)';
            } else if (distance < 3600000) { // 1시간 미만
                overlayElement.style.background = 'rgba(245, 158, 11, 0.7)';
            }
        }
        
        // 즉시 실행
        updateCountdown();
        
        // 1초마다 업데이트
        const countdownInterval = setInterval(updateCountdown, 1000);
        
        // 페이지 언로드 시 인터벌 정리
        window.addEventListener('beforeunload', () => {
            clearInterval(countdownInterval);
        });
    }
    
    // 메인 이미지 변경
    function changeMainImage(imageUrl, thumbnailElement) {
        const mainImage = document.getElementById('mainImage');
        if (mainImage) {
            mainImage.src = imageUrl;
            
            // 모든 썸네일에서 active 클래스 제거
            document.querySelectorAll('.thumbnail').forEach(thumb => {
                thumb.classList.remove('active');
            });
            
            // 클릭된 썸네일에 active 클래스 추가
            thumbnailElement.classList.add('active');
        }
    }
    
    // 옵션 선택
    function selectOption(choiceElement) {
        const optionId = choiceElement.dataset.optionId;
        const choiceId = choiceElement.dataset.choiceId;
        const choicePrice = parseFloat(choiceElement.dataset.choicePrice) || 0;
        
        // 같은 옵션 그룹의 다른 선택지들에서 selected 클래스 제거
        const optionGroup = choiceElement.closest('.bg-gray-100, .dark\\:bg-gray-700');
        if (optionGroup) {
            optionGroup.querySelectorAll('.option-choice').forEach(choice => {
                choice.classList.remove('selected');
            });
        }
        
        // 현재 선택지에 selected 클래스 추가
        choiceElement.classList.add('selected');
        
        // 선택된 옵션 저장
        selectedOptions[optionId] = {
            choiceId: choiceId,
            price: choicePrice
        };
        
        // 총 가격 업데이트
        updateTotalPrice();
    }
    
    // 총 가격 업데이트
    function updateTotalPrice() {
        let totalPrice = meetupData.basePrice || 0;
        
        // 옵션 가격 추가
        Object.values(selectedOptions).forEach(option => {
            totalPrice += option.price;
        });
        
        // 가격 표시 업데이트 (필요시)
        const priceElements = document.querySelectorAll('.total-price');
        priceElements.forEach(element => {
            element.textContent = `${totalPrice.toLocaleString()} sats`;
        });
    }
    
    // 밋업 참가 신청
    function joinMeetup() {
        // 로그인 체크
        if (!meetupData.isAuthenticated) {
            if (confirm('로그인이 필요합니다. 로그인 페이지로 이동하시겠습니까?')) {
                window.location.href = meetupData.loginUrl;
            }
            return;
        }
        
        // 필수 옵션 선택 체크
        const requiredOptions = document.querySelectorAll('[data-required="true"]');
        for (let option of requiredOptions) {
            const optionId = option.dataset.optionId;
            if (!selectedOptions[optionId]) {
                alert('필수 옵션을 선택해주세요.');
                return;
            }
        }
        
        // 참가 신청 확인
        const totalPrice = calculateTotalPrice();
        const message = `밋업에 참가하시겠습니까?\n\n총 참가비: ${totalPrice.toLocaleString()} sats`;
        
        if (confirm(message)) {
            // TODO: 실제 참가 신청 로직 구현
            alert('참가 신청 기능을 구현 중입니다.');
            console.log('Selected options:', selectedOptions);
            console.log('Total price:', totalPrice);
        }
    }
    
    // 총 가격 계산
    function calculateTotalPrice() {
        let totalPrice = meetupData.basePrice || 0;
        
        Object.values(selectedOptions).forEach(option => {
            totalPrice += option.price;
        });
        
        return totalPrice;
    }
    
    // 참가 버튼 상태 업데이트
    function updateJoinButtonState() {
        const joinButton = document.querySelector('[onclick="joinMeetup()"]');
        if (!joinButton) return;
        
        // 필수 옵션 체크
        const requiredOptions = document.querySelectorAll('[data-required="true"]');
        let allRequiredSelected = true;
        
        for (let option of requiredOptions) {
            const optionId = option.dataset.optionId;
            if (!selectedOptions[optionId]) {
                allRequiredSelected = false;
                break;
            }
        }
        
        // 버튼 상태 업데이트
        if (allRequiredSelected) {
            joinButton.disabled = false;
            joinButton.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            joinButton.disabled = true;
            joinButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }
    
    // 반응형 이미지 갤러리
    function initializeImageGallery() {
        const thumbnails = document.querySelectorAll('.thumbnail');
        
        thumbnails.forEach((thumbnail, index) => {
            thumbnail.addEventListener('click', function() {
                const img = this.querySelector('img');
                if (img) {
                    changeMainImage(img.src, this);
                }
            });
            
            // 키보드 네비게이션
            thumbnail.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
            
            // 접근성을 위한 속성 추가
            thumbnail.setAttribute('tabindex', '0');
            thumbnail.setAttribute('role', 'button');
            thumbnail.setAttribute('aria-label', `이미지 ${index + 1} 보기`);
        });
    }
    
    // 초기화
    initializeImageGallery();
    updateTotalPrice();
    
    // 옵션 변경 시 버튼 상태 업데이트
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('option-choice')) {
            setTimeout(updateJoinButtonState, 100);
        }
    });
});

// 전역에서 접근 가능하도록 노출
window.MeetupDetail = {
    updateTotalPrice: function() {
        // 외부에서 호출할 수 있는 인터페이스
    }
}; 