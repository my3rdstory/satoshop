// 밋업 디테일 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 밋업 데이터 가져오기
    const meetupDataElement = document.getElementById('meetup-data');
    const meetupData = meetupDataElement ? JSON.parse(meetupDataElement.textContent) : {};
    
    // 선택된 옵션들 저장
    let selectedOptions = {};
    
    // 마크다운 렌더링
    initializeMarkdownRendering();
    
    // 이벤트 리스너 초기화
    initializeEventListeners();
    
    // 카운트다운 초기화
    initializeCountdown();
    
    function initializeEventListeners() {
        // 이미지 썸네일 클릭 이벤트
        document.querySelectorAll('.thumbnail').forEach(thumbnail => {
            thumbnail.addEventListener('click', function() {
                const img = this.querySelector('img');
                if (img && img.src) {
                    changeMainImage(img.src, this);
                }
            });
        });
    }
    
    function initializeMarkdownRendering() {
        // 설명 마크다운 렌더링
        const descriptionElement = document.getElementById('meetup-description');
        if (descriptionElement) {
            const markdownText = descriptionElement.textContent;
            if (markdownText.trim()) {
                const htmlContent = marked.parse(markdownText);
                descriptionElement.innerHTML = htmlContent;
            }
        }
        
        // 특이사항 마크다운 렌더링
        const notesElement = document.getElementById('special-notes');
        if (notesElement) {
            const markdownText = notesElement.textContent;
            if (markdownText.trim()) {
                const htmlContent = marked.parse(markdownText);
                notesElement.innerHTML = htmlContent;
            }
        }
    }
    
    function initializeCountdown() {
        // 조기등록 할인 오버레이 카운트다운 시작
        const countdownDataElement = document.getElementById('countdown-data');
        if (countdownDataElement) {
            try {
                const countdownData = JSON.parse(countdownDataElement.textContent);
                if (countdownData.endDateTime) {
                    startEarlyBirdCountdown(countdownData.endDateTime);
                }
            } catch (e) {
                console.error('조기등록 카운트다운 데이터 파싱 오류:', e);
            }
        }
        
        // 기타 카운트다운 요소들
        const countdownElement = document.querySelector('.countdown-timer');
        if (countdownElement) {
            const endDateTime = countdownElement.dataset.endDateTime;
            if (endDateTime) {
                startCountdown(endDateTime);
            }
        }
    }
    
    function startEarlyBirdCountdown(endDateTime) {
        const countdownElement = document.getElementById('early-bird-countdown-overlay');
        if (!countdownElement) return;
        
        const countdownInterval = setInterval(() => {
            const now = new Date();
            const end = new Date(endDateTime);
            const timeLeft = end - now;
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                countdownElement.textContent = '할인 종료';
                // 페이지 새로고침으로 할인 상태 업데이트
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
                return;
            }
            
            // 시간 계산
            const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
            
            // 남은 시간 포맷팅 (항상 초까지 표시)
            let timeString = '';
            if (days > 0) {
                timeString = `${days}일 ${hours}시간 ${minutes}분 ${seconds}초`;
            } else if (hours > 0) {
                timeString = `${hours}시간 ${minutes}분 ${seconds}초`;
            } else if (minutes > 0) {
                timeString = `${minutes}분 ${seconds}초`;
            } else {
                timeString = `${seconds}초`;
            }
            
            countdownElement.textContent = `${timeString} 남음`;
            
            // 1시간 미만일 때 긴급 스타일 적용
            if (timeLeft < 3600000) { // 1시간 = 3600000ms
                countdownElement.classList.add('text-red-300', 'font-bold');
            }
            
        }, 1000);
    }
    
    function startCountdown(endDateTime) {
        const countdownInterval = setInterval(() => {
            updateCountdown();
        }, 1000);
        
        function updateCountdown() {
            const now = new Date().getTime();
            const end = new Date(endDateTime).getTime();
            const timeLeft = end - now;
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
            }
        }
    }
    
    // 메인 이미지 변경 - 전역 함수로 노출
    window.changeMainImage = function(imageUrl, thumbnailElement) {
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
    };
    
    // 옵션 선택 (토글 방식) - 전역 함수로 노출
    window.selectOption = function(choiceElement) {
        const optionId = choiceElement.dataset.optionId;
        const choiceId = choiceElement.dataset.choiceId;
        const choicePrice = parseFloat(choiceElement.dataset.choicePrice) || 0;
        const isCurrentlySelected = choiceElement.classList.contains('selected');
        
        // 옵션명과 선택지명 가져오기 (HTML 엔티티 및 공백 제거)
        const optionGroup = choiceElement.closest('.option-group');
        const optionName = optionGroup ? optionGroup.querySelector('h4').textContent.trim() : '';
        const choiceName = choiceElement.querySelector('.option-title').textContent.trim().replace(/\u00A0/g, '');
        
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
            
            // 선택된 옵션 저장 (옵션명과 선택지명 포함)
            selectedOptions[optionId] = {
                choiceId: choiceId,
                price: choicePrice,
                optionName: optionName,
                choiceName: choiceName
            };
        } else {
            // 토글로 선택 해제
            delete selectedOptions[optionId];
        }
        
        // 총 가격 업데이트
        updateTotalPrice();
        updateJoinButtonState();
    };
    
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
    
    // 밋업 참가 신청 (AJAX로 변경) - 전역 함수로 노출
    window.joinMeetup = function() {
        const joinButton = document.querySelector('[onclick="joinMeetup()"]');
        if (!joinButton) return;
        
        // 버튼 비활성화 및 로딩 상태
        joinButton.disabled = true;
        joinButton.innerHTML = `
            <i class="fas fa-spinner fa-spin"></i>
            <span>신청 처리 중...</span>
        `;
        
        // 무료 밋업인지 확인 - isFree 필드로 명확하게 구분
        const isFree = meetupData.isFree;
        
        // 무료/유료에 따라 다른 URL - 무료 밋업은 참가자 정보 입력 페이지로 먼저 이동
        const checkoutUrl = isFree 
            ? `/meetup/${meetupData.storeId}/${meetupData.meetupId}/free_participant_info/`
            : `/meetup/${meetupData.storeId}/${meetupData.meetupId}/checkout/`;
        
        // 선택된 옵션을 URL 파라미터로 전달
        const params = new URLSearchParams();
        if (Object.keys(selectedOptions).length > 0) {
            params.append('selected_options', JSON.stringify(selectedOptions));
        }
        
        const fullUrl = Object.keys(selectedOptions).length > 0 ? 
            `${checkoutUrl}?${params.toString()}` : checkoutUrl;
        
        // 페이지 이동
        window.location.href = fullUrl;
    };
    
    // 정원 상태 업데이트 (필요시에만 호출)
    function updateCapacityStatus() {
        return new Promise((resolve, reject) => {
            if (!meetupData.storeId || !meetupData.meetupId) {
                reject('meetup 정보 없음');
                return;
            }
            
            const url = `/meetup/${meetupData.storeId}/${meetupData.meetupId}/capacity-status/`;
            
            fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    reject(data.error);
                    return;
                }
                
                // UI 업데이트
                updateCapacityUI(data);
                resolve(data);
            })
            .catch(error => {
                reject(error);
            });
        });
    }
    
    // 정원 상태 UI 업데이트
    function updateCapacityUI(data) {
        // 남은 자리 수 업데이트
        const remainingSpotsElement = document.querySelector('.text-sm.font-medium');
        if (remainingSpotsElement) {
            let statusText = '';
            let statusClass = '';
            
            if (data.is_temporarily_closed) {
                statusText = '일시 중단';
                statusClass = 'text-purple-500';
            } else if (data.is_expired) {
                statusText = '종료';
                statusClass = 'text-gray-500';
            } else if (data.is_full) {
                statusText = '정원 마감';
                statusClass = 'text-red-500';
            } else if (data.remaining_spots !== null) {
                statusText = `남은자리: ${data.remaining_spots.toLocaleString()}명`;
                if (data.remaining_spots <= 5 && data.remaining_spots > 0) {
                    statusClass = 'text-orange-500';
                } else {
                    statusClass = 'text-green-500';
                }
            } else {
                statusText = '참가 가능';
                statusClass = 'text-green-500';
            }
            
            // 클래스 업데이트
            remainingSpotsElement.className = `text-sm font-medium ${statusClass}`;
            remainingSpotsElement.textContent = statusText;
        }
        
        // 현재 참가자 수 업데이트
        const participantCountElement = document.querySelector('.flex.justify-between.text-sm span:last-child');
        if (participantCountElement && data.max_participants) {
            participantCountElement.textContent = `${data.current_participants || 0}명 / ${data.max_participants}명`;
        }
        
        // 진행률 바 업데이트
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar && data.max_participants) {
            const percentage = Math.min(100, (data.current_participants || 0) / data.max_participants * 100);
            progressBar.style.width = `${percentage}%`;
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
    
    // 전역 함수로 노출
    window.joinMeetup = joinMeetup;
    window.selectOption = selectOption;
});

// 전역에서 접근 가능하도록 노출
window.MeetupDetail = {
    updateTotalPrice: function() {
        // 외부에서 호출할 수 있는 인터페이스
    }
}; 