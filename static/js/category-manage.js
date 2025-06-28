// 카테고리 관리 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소들
    const addCategoryForm = document.getElementById('addCategoryForm');
    const newCategoryNameInput = document.getElementById('newCategoryName');
    const editModal = document.getElementById('editModal');
    const editCategoryForm = document.getElementById('editCategoryForm');
    const editCategoryIdInput = document.getElementById('editCategoryId');
    const editCategoryNameInput = document.getElementById('editCategoryName');
    const categoryGrid = document.getElementById('categoryGrid');
    const categoryCount = document.getElementById('categoryCount');
    const notification = document.getElementById('notification');

    // 카테고리 추가 폼 이벤트
    if (addCategoryForm) {
        addCategoryForm.addEventListener('submit', handleAddCategory);
    }

    // 카테고리 수정 폼 이벤트
    if (editCategoryForm) {
        editCategoryForm.addEventListener('submit', handleEditCategory);
    }

    // 카테고리 추가 함수
    function handleAddCategory(e) {
        e.preventDefault();
        
        const name = newCategoryNameInput.value.trim();
        if (!name) {
            showNotification('카테고리명을 입력해주세요.', 'error');
            return;
        }

        // 로딩 상태 설정
        setFormLoading(addCategoryForm, true);

        fetch(`/menu/${window.storeId}/categories/create/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': window.csrfToken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                newCategoryNameInput.value = '';
                addCategoryToGrid(data.category);
                updateCategoryCount();
            } else {
                showNotification(data.error || '카테고리 추가에 실패했습니다.', 'error');
            }
        })
        .catch(error => {
            console.error('카테고리 추가 오류:', error);
            showNotification('네트워크 오류가 발생했습니다.', 'error');
        })
        .finally(() => {
            setFormLoading(addCategoryForm, false);
        });
    }

    // 카테고리 수정 함수
    function handleEditCategory(e) {
        e.preventDefault();
        
        const categoryId = editCategoryIdInput.value;
        const name = editCategoryNameInput.value.trim();
        
        if (!name) {
            showNotification('카테고리명을 입력해주세요.', 'error');
            return;
        }

        // 로딩 상태 설정
        setFormLoading(editCategoryForm, true);

        fetch(`/menu/${window.storeId}/categories/${categoryId}/`, {
            method: 'PUT',
            headers: {
                'X-CSRFToken': window.csrfToken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCategoryInGrid(categoryId, name);
                closeEditModal();
            } else {
                showNotification(data.error || '카테고리 수정에 실패했습니다.', 'error');
            }
        })
        .catch(error => {
            console.error('카테고리 수정 오류:', error);
            showNotification('네트워크 오류가 발생했습니다.', 'error');
        })
        .finally(() => {
            setFormLoading(editCategoryForm, false);
        });
    }

    // 그리드에 카테고리 추가
    function addCategoryToGrid(category) {
        // 빈 상태 메시지 제거
        const emptyState = document.getElementById('emptyState');
        if (emptyState) {
            emptyState.remove();
        }

        const categoryCard = createCategoryCard(category);
        categoryGrid.appendChild(categoryCard);
    }

    // 카테고리 카드 생성
    function createCategoryCard(category) {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'category-card';
        cardDiv.setAttribute('data-category-id', category.id);
        cardDiv.setAttribute('draggable', 'true');
        
        const date = new Date(category.created_at).toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        }).replace(/\./g, '.').replace(/ /g, '');

        cardDiv.innerHTML = `
            <div class="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-600 hover:shadow-md transition-all duration-200 cursor-move">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center space-x-2">
                        <i class="fas fa-grip-vertical text-gray-400 drag-handle"></i>
                        <h3 class="category-name text-lg font-medium text-gray-900 dark:text-white truncate">
                            ${category.name}
                        </h3>
                    </div>
                    <div class="flex space-x-1">
                        <button onclick="editCategory('${category.id}', '${category.name}')" 
                                class="p-2 text-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900 rounded-lg transition-colors"
                                title="수정">
                            <i class="fas fa-edit text-sm"></i>
                        </button>
                        <button onclick="deleteCategory('${category.id}', '${category.name}')" 
                                class="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition-colors"
                                title="삭제">
                            <i class="fas fa-trash text-sm"></i>
                        </button>
                    </div>
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                    <i class="fas fa-calendar mr-1"></i>
                    ${date}
                </div>
            </div>
        `;

        // 새 카드에 드래그 기능 추가 (별도 파일에서 처리)
        if (window.addDragToNewCard) {
            window.addDragToNewCard(cardDiv);
        }

        return cardDiv;
    }

    // 그리드에서 카테고리 업데이트
    function updateCategoryInGrid(categoryId, newName) {
        const categoryCard = document.querySelector(`[data-category-id="${categoryId}"]`);
        if (categoryCard) {
            const nameElement = categoryCard.querySelector('.category-name');
            if (nameElement) {
                nameElement.textContent = newName;
            }
            
            // 수정 버튼의 onclick 속성도 업데이트
            const editButton = categoryCard.querySelector('button[onclick*="editCategory"]');
            if (editButton) {
                editButton.setAttribute('onclick', `editCategory('${categoryId}', '${newName}')`);
            }
        }
    }

    // 그리드에서 카테고리 제거
    function removeCategoryFromGrid(categoryId) {
        const categoryCard = document.querySelector(`[data-category-id="${categoryId}"]`);
        if (categoryCard) {
            categoryCard.style.opacity = '0';
            categoryCard.style.transform = 'scale(0.9)';
            setTimeout(() => {
                categoryCard.remove();
                updateCategoryCount();
                
                // 카테고리가 모두 제거되면 빈 상태 표시
                const remainingCards = document.querySelectorAll('.category-card');
                if (remainingCards.length === 0) {
                    showEmptyState();
                }
            }, 300);
        }
    }

    // 빈 상태 표시
    function showEmptyState() {
        const emptyStateDiv = document.createElement('div');
        emptyStateDiv.id = 'emptyState';
        emptyStateDiv.className = 'col-span-full text-center py-12';
        emptyStateDiv.innerHTML = `
            <div class="w-24 h-24 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <i class="fas fa-tags text-gray-400 text-3xl"></i>
            </div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">카테고리가 없습니다</h3>
            <p class="text-gray-500 dark:text-gray-400">첫 번째 카테고리를 추가해보세요</p>
        `;
        categoryGrid.appendChild(emptyStateDiv);
    }

    // 카테고리 개수 업데이트
    function updateCategoryCount() {
        const count = document.querySelectorAll('.category-card').length;
        if (categoryCount) {
            categoryCount.textContent = `총 ${count}개의 카테고리`;
        }
    }

    // 폼 로딩 상태 설정
    function setFormLoading(form, isLoading) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (isLoading) {
            form.classList.add('loading');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>처리중...';
            }
        } else {
            form.classList.remove('loading');
            if (submitButton) {
                submitButton.disabled = false;
                if (form === addCategoryForm) {
                    submitButton.innerHTML = '<i class="fas fa-plus mr-2"></i>카테고리 추가';
                } else if (form === editCategoryForm) {
                    submitButton.innerHTML = '저장';
                }
            }
        }
    }

    // 알림 표시
    function showNotification(message, type = 'info') {
        const notificationIcon = document.getElementById('notificationIcon');
        const notificationMessage = document.getElementById('notificationMessage');
        
        // 아이콘 설정
        let iconClass = '';
        let iconColor = '';
        switch (type) {
            case 'success':
                iconClass = 'fas fa-check-circle';
                iconColor = 'text-green-500';
                break;
            case 'error':
                iconClass = 'fas fa-exclamation-circle';
                iconColor = 'text-red-500';
                break;
            case 'warning':
                iconClass = 'fas fa-exclamation-triangle';
                iconColor = 'text-yellow-500';
                break;
            default:
                iconClass = 'fas fa-info-circle';
                iconColor = 'text-blue-500';
        }
        
        notificationIcon.innerHTML = `<i class="${iconClass} ${iconColor}"></i>`;
        notificationMessage.textContent = message;
        
        // 알림 표시
        notification.classList.remove('hidden');
        notification.classList.add('show');
        
        // 3초 후 자동 숨김
        setTimeout(() => {
            hideNotification();
        }, 3000);
    }

    // 알림 숨김
    function hideNotification() {
        notification.classList.add('hide');
        setTimeout(() => {
            notification.classList.add('hidden');
            notification.classList.remove('show', 'hide');
        }, 300);
    }

    // 전역 함수들
    window.editCategory = function(categoryId, currentName) {
        editCategoryIdInput.value = categoryId;
        editCategoryNameInput.value = currentName;
        openEditModal();
    };

    window.deleteCategory = function(categoryId, categoryName) {
        if (!confirm(`"${categoryName}" 카테고리를 삭제하시겠습니까?\n\n이 카테고리를 사용하는 메뉴들에서 카테고리가 제거됩니다.`)) {
            return;
        }

        fetch(`/menu/${window.storeId}/categories/${categoryId}/delete/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': window.csrfToken,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                removeCategoryFromGrid(categoryId);
            } else {
                showNotification(data.error || '카테고리 삭제에 실패했습니다.', 'error');
            }
        })
        .catch(error => {
            console.error('카테고리 삭제 오류:', error);
            showNotification('네트워크 오류가 발생했습니다.', 'error');
        });
    };

    // 수정 모달 열기
    function openEditModal() {
        editModal.classList.remove('hidden');
        editCategoryNameInput.focus();
        document.body.style.overflow = 'hidden';
    }

    // 수정 모달 닫기
    window.closeEditModal = function() {
        editModal.classList.add('hidden');
        document.body.style.overflow = '';
        editCategoryForm.reset();
    };

    // ESC 키로 모달 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !editModal.classList.contains('hidden')) {
            closeEditModal();
        }
    });

    // 알림 클릭시 숨김
    if (notification) {
        notification.addEventListener('click', hideNotification);
    }

    // 드래그&드롭 기능은 별도 파일(category-drag-drop.js)에서 처리
}); 