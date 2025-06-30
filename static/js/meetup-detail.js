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
        const countdownElement = document.getElementById('early-bird-countdown');
        const countdownOverlayElement = document.getElementById('early-bird-countdown-overlay');
        
        if (!countdownElement && !countdownOverlayElement) return;
        
        function updateCountdown() {
            const now = new Date().getTime();
            const endTime = endDateTime.getTime();
            const distance = endTime - now;
            
            if (distance < 0) {
                // 카운트다운 종료
                if (countdownElement) {
                    countdownElement.textContent = '마감됨';
                    countdownElement.className = 'text-gray-500';
                }
                if (countdownOverlayElement) {
                    countdownOverlayElement.textContent = '마감됨';
                }
                return;
            }
            
            // 시간 계산
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            // 텍스트 형태로 표시
            let timeText = '';
            if (days > 0) {
                timeText = `${days}일 ${hours.toString().padStart(2, '0')}시간 ${minutes.toString().padStart(2, '0')}분 ${seconds.toString().padStart(2, '0')}초 남음`;
            } else if (hours > 0) {
                timeText = `${hours.toString().padStart(2, '0')}시간 ${minutes.toString().padStart(2, '0')}분 ${seconds.toString().padStart(2, '0')}초 남음`;
            } else if (minutes > 0) {
                timeText = `${minutes.toString().padStart(2, '0')}분 ${seconds.toString().padStart(2, '0')}초 남음`;
            } else {
                timeText = `${seconds.toString().padStart(2, '0')}초 남음`;
            }
            
            // 기존 카운트다운 요소 업데이트
            if (countdownElement) {
                countdownElement.textContent = timeText;
                
                // 긴급도에 따른 색상 변경
                if (distance < 60000) { // 1분 미만
                    countdownElement.className = 'text-red-600 font-bold animate-pulse';
                } else if (distance < 3600000) { // 1시간 미만
                    countdownElement.className = 'text-orange-600 font-medium';
                } else {
                    countdownElement.className = 'text-red-600';
                }
            }
            
            // 오버레이 카운트다운 요소 업데이트
            if (countdownOverlayElement) {
                countdownOverlayElement.textContent = timeText;
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
    
    // 옵션 선택 (토글 방식)
    function selectOption(choiceElement) {
        const optionId = choiceElement.dataset.optionId;
        const choiceId = choiceElement.dataset.choiceId;
        const choicePrice = parseFloat(choiceElement.dataset.choicePrice) || 0;
        const isCurrentlySelected = choiceElement.classList.contains('selected');
        
        // 같은 옵션 그룹의 모든 선택지들 비활성화
        document.querySelectorAll(`[data-option-id="${optionId}"]`).forEach(choice => {
            choice.classList.remove('selected');
            choice.classList.remove('border-purple-500', 'bg-purple-500', 'text-white');
            choice.classList.add('border-black', 'dark:border-white');
            
            // 제목과 가격 색상 원래대로
            const title = choice.querySelector('.option-title');
            const price = choice.querySelector('.option-price');
            if (title) {
                title.classList.remove('text-white');
                title.classList.add('text-gray-900', 'dark:text-white');
            }
            if (price) {
                price.classList.remove('text-white');
                price.classList.add('text-gray-600', 'dark:text-gray-400');
            }
        });
        
        // 이미 선택된 옵션이 아니라면 활성화 (토글 효과)
        if (!isCurrentlySelected) {
            choiceElement.classList.add('selected');
            choiceElement.classList.remove('border-black', 'dark:border-white');
            choiceElement.classList.add('border-purple-500', 'bg-purple-500', 'text-white');
            
            // 제목과 가격 색상 흰색으로
            const title = choiceElement.querySelector('.option-title');
            const price = choiceElement.querySelector('.option-price');
            if (title) {
                title.classList.add('text-white');
                title.classList.remove('text-gray-900', 'dark:text-white');
            }
            if (price) {
                price.classList.add('text-white');
                price.classList.remove('text-gray-600', 'dark:text-gray-400');
            }
            
            // 선택된 옵션 저장
            selectedOptions[optionId] = {
                choiceId: choiceId,
                price: choicePrice
            };
        } else {
            // 토글로 선택 해제
            delete selectedOptions[optionId];
        }
        
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
        // 참가자 정보 입력 페이지로 이동 (GET 요청)
        const checkoutUrl = `/meetup/${meetupData.storeId}/${meetupData.meetupId}/checkout/`;
        
        // 선택된 옵션이 있다면 URL 파라미터로 전달
        if (Object.keys(selectedOptions).length > 0) {
            const params = new URLSearchParams();
            params.append('selected_options', JSON.stringify(selectedOptions));
            window.location.href = `${checkoutUrl}?${params.toString()}`;
        } else {
            window.location.href = checkoutUrl;
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