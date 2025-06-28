// 카테고리 드래그&드롭 전용 JavaScript
console.log('category-drag-drop.js 로드됨');

// 전역 변수
let draggedElement = null;
let dropIndicator = null;

// 초기화 함수
function initializeCategoryDragDrop() {
    console.log('드래그&드롭 초기화 시작');
    
    // 기존 카테고리 카드들에 드래그 이벤트 설정
    const existingCards = document.querySelectorAll('.category-card');
    console.log('기존 카테고리 카드 개수:', existingCards.length);
    
    existingCards.forEach((card, index) => {
        console.log(`카드 ${index + 1} 설정 중:`, card.getAttribute('data-category-id'));
        setupDragEvents(card);
    });
}

// 드래그 이벤트 설정
function setupDragEvents(cardElement) {
    console.log('드래그 이벤트 설정:', cardElement.getAttribute('data-category-id'));
    
    // 드래그 가능하도록 설정
    cardElement.setAttribute('draggable', 'true');
    
    // 이벤트 리스너 추가
    cardElement.addEventListener('dragstart', handleDragStart);
    cardElement.addEventListener('dragend', handleDragEnd);
    cardElement.addEventListener('dragover', handleDragOver);
    cardElement.addEventListener('drop', handleDrop);
    cardElement.addEventListener('dragenter', handleDragEnter);
    cardElement.addEventListener('dragleave', handleDragLeave);
    
    console.log('이벤트 리스너 추가 완료');
}

// 드래그 시작
function handleDragStart(e) {
    console.log('드래그 시작:', this.getAttribute('data-category-id'));
    
    draggedElement = this;
    this.style.opacity = '0.5';
    this.classList.add('dragging');
    
    // 컨테이너에 드래그 상태 클래스 추가
    const categoryGrid = document.getElementById('categoryGrid');
    if (categoryGrid) {
        categoryGrid.classList.add('dragging');
    }
    
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.outerHTML);
}

// 드래그 종료
function handleDragEnd(e) {
    console.log('드래그 종료');
    
    this.style.opacity = '';
    this.classList.remove('dragging');
    draggedElement = null;
    
    // 컨테이너에서 드래그 상태 클래스 제거
    const categoryGrid = document.getElementById('categoryGrid');
    if (categoryGrid) {
        categoryGrid.classList.remove('dragging');
    }
    
    removeDropIndicator();
}

// 드래그 오버
function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

// 드래그 진입
function handleDragEnter(e) {
    if (this === draggedElement) return;
    
    console.log('드래그 진입:', this.getAttribute('data-category-id'));
    
    const rect = this.getBoundingClientRect();
    const midpoint = rect.top + rect.height / 2;
    const isAfter = e.clientY > midpoint;
    
    console.log('드롭 위치:', isAfter ? '아래' : '위');
    
    showDropIndicator(this, isAfter);
}

// 드래그 이탈
function handleDragLeave(e) {
    // 요소를 완전히 벗어났을 때만 인디케이터 제거
    if (!this.contains(e.relatedTarget)) {
        console.log('드래그 이탈');
        removeDropIndicator();
    }
}

// 드롭
function handleDrop(e) {
    console.log('드롭 발생');
    
    if (e.stopPropagation) {
        e.stopPropagation();
    }

    if (draggedElement !== this) {
        const rect = this.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        const isAfter = e.clientY > midpoint;
        
        console.log('요소 이동:', {
            from: draggedElement.getAttribute('data-category-id'),
            to: this.getAttribute('data-category-id'),
            position: isAfter ? '아래' : '위'
        });
        
        if (isAfter) {
            this.parentNode.insertBefore(draggedElement, this.nextSibling);
        } else {
            this.parentNode.insertBefore(draggedElement, this);
        }
        
        // 순서 저장
        saveCategoryOrder();
    }
    
    removeDropIndicator();
    return false;
}

// 드롭 인디케이터 표시
function showDropIndicator(element, isAfter) {
    removeDropIndicator();
    
    console.log('드롭 인디케이터 표시');
    
    dropIndicator = document.createElement('div');
    dropIndicator.className = 'drop-indicator';
    dropIndicator.style.cssText = `
        position: absolute;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        border-radius: 2px;
        z-index: 10;
        pointer-events: none;
        box-shadow: 0 0 8px rgba(59, 130, 246, 0.5);
    `;
    
    if (isAfter) {
        element.parentNode.insertBefore(dropIndicator, element.nextSibling);
    } else {
        element.parentNode.insertBefore(dropIndicator, element);
    }
}

// 드롭 인디케이터 제거
function removeDropIndicator() {
    if (dropIndicator) {
        console.log('드롭 인디케이터 제거');
        dropIndicator.remove();
        dropIndicator = null;
    }
}

// 카테고리 순서 저장
function saveCategoryOrder() {
    console.log('순서 저장 시작');
    
    const categoryCards = document.querySelectorAll('.category-card');
    const categoryOrders = [];
    
    categoryCards.forEach((card, index) => {
        const categoryId = card.getAttribute('data-category-id');
        if (categoryId) {
            categoryOrders.push({
                id: categoryId,
                order: index + 1
            });
        }
    });

    console.log('새로운 순서:', categoryOrders);

    if (categoryOrders.length === 0) {
        console.log('저장할 카테고리가 없음');
        return;
    }

    // 전역 변수 확인
    if (!window.storeId) {
        console.error('storeId가 설정되지 않음');
        return;
    }
    
    if (!window.csrfToken) {
        console.error('CSRF 토큰이 설정되지 않음');
        return;
    }

    fetch(`/menu/${window.storeId}/categories/reorder/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': window.csrfToken,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ category_orders: categoryOrders })
    })
    .then(response => {
        console.log('API 응답 상태:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('API 응답 데이터:', data);
        if (!data.success) {
            console.error('순서 저장 실패:', data.error);
            alert('순서 저장에 실패했습니다: ' + data.error);
            location.reload();
        } else {
            console.log('순서 저장 성공');
        }
    })
    .catch(error => {
        console.error('순서 저장 오류:', error);
        alert('네트워크 오류가 발생했습니다.');
        location.reload();
    });
}

// 새 카테고리 카드에 드래그 기능 추가하는 함수 (외부에서 호출용)
function addDragToNewCard(cardElement) {
    console.log('새 카드에 드래그 기능 추가');
    setupDragEvents(cardElement);
}

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM 로드 완료 - 드래그&드롭 초기화');
    
    // 약간의 지연을 두어 다른 스크립트들이 먼저 실행되도록 함
    setTimeout(initializeCategoryDragDrop, 100);
});

// 전역 함수로 노출
window.addDragToNewCard = addDragToNewCard;
window.initializeCategoryDragDrop = initializeCategoryDragDrop; 