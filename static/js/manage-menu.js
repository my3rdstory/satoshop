// 메뉴 관리 페이지 JavaScript

// CSRF 토큰 가져오기
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

const csrftoken = getCookie('csrftoken');

// 메뉴 활성화 토글
function toggleMenuActive(menuId, isActive) {
    const storeId = window.location.pathname.split('/')[2]; // URL에서 store_id 추출
    
    fetch(`/menu/${storeId}/${menuId}/toggle-active/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            is_active: isActive
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (isActive) {
                showNotification('메뉴가 활성화되었습니다.', 'success');
            } else {
                showNotification('메뉴가 비활성화되었습니다.', 'info');
            }
            
            // 페이지의 상태 표시 업데이트
            updateStatusDisplay(isActive);
        } else {
            showNotification('오류가 발생했습니다: ' + data.error, 'error');
            // 토글 상태 되돌리기
            const toggle = document.querySelector(`input[onchange*="toggleMenuActive"]`);
            if (toggle) {
                toggle.checked = !isActive;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('네트워크 오류가 발생했습니다.', 'error');
        // 토글 상태 되돌리기
        const toggle = document.querySelector(`input[onchange*="toggleMenuActive"]`);
        if (toggle) {
            toggle.checked = !isActive;
        }
    });
}

// 상태 표시 업데이트
function updateStatusDisplay(isActive) {
    const statusIndicator = document.querySelector('.status-indicator');
    if (statusIndicator) {
        if (isActive) {
            statusIndicator.className = 'status-indicator status-active';
            statusIndicator.innerHTML = '<i class="fas fa-check-circle"></i><span>활성화됨</span>';
        } else {
            statusIndicator.className = 'status-indicator status-inactive';
            statusIndicator.innerHTML = '<i class="fas fa-pause-circle"></i><span>비활성화됨</span>';
        }
    }
}

// 일시품절 토글 (기존 함수 재사용)
function toggleTemporaryOutOfStock(menuId, isOutOfStock) {
    const storeId = window.location.pathname.split('/')[2]; // URL에서 store_id 추출
    
    fetch(`/menu/${storeId}/${menuId}/toggle-temporary-out-of-stock/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            is_temporarily_out_of_stock: isOutOfStock
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (isOutOfStock) {
                showNotification('메뉴가 일시품절로 설정되었습니다.', 'warning');
            } else {
                showNotification('메뉴 일시품절이 해제되었습니다.', 'success');
            }
        } else {
            showNotification('오류가 발생했습니다: ' + data.error, 'error');
            // 토글 상태 되돌리기
            const toggle = document.querySelector(`input[onchange*="${menuId}"]`);
            if (toggle) {
                toggle.checked = !isOutOfStock;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('네트워크 오류가 발생했습니다.', 'error');
        // 토글 상태 되돌리기
        const toggle = document.querySelector(`input[onchange*="${menuId}"]`);
        if (toggle) {
            toggle.checked = !isOutOfStock;
        }
    });
}

// 알림 표시 함수
function showNotification(message, type = 'info') {
    // 기존 알림이 있으면 제거
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 알림 생성
    const notification = document.createElement('div');
    notification.className = `notification fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full`;
    
    // 타입에 따른 스타일 설정
    const typeClasses = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };
    
    notification.className += ` ${typeClasses[type] || typeClasses.info}`;
    notification.textContent = message;
    
    // 아이콘 추가
    const icon = document.createElement('i');
    const iconClasses = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    icon.className = `${iconClasses[type] || iconClasses.info} mr-2`;
    notification.prepend(icon);
    
    // 페이지에 추가
    document.body.appendChild(notification);
    
    // 애니메이션으로 표시
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('메뉴 관리 페이지 로드됨');
    
    // 토글 스위치에 애니메이션 효과 추가
    const toggleSwitches = document.querySelectorAll('.toggle-switch input');
    toggleSwitches.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const slider = this.nextElementSibling;
            slider.style.transform = 'scale(0.95)';
            setTimeout(() => {
                slider.style.transform = 'scale(1)';
            }, 150);
        });
    });
    
    // 관리 메뉴 항목에 호버 효과 개선
    const menuItems = document.querySelectorAll('.divide-y > div');
    menuItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(4px)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
}); 