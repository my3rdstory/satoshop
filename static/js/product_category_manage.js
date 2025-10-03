(() => {
  const root = document.getElementById('product-category-manage');
  if (!root) return;

  const config = window.productCategoryConfig || {};
  const initialDataElement = document.getElementById('product-category-initial-data');
  let categories = [];

  try {
    categories = initialDataElement ? JSON.parse(initialDataElement.textContent) : [];
    if (!Array.isArray(categories)) {
      categories = [];
    }
  } catch (error) {
    console.error('카테고리 초기 데이터 파싱 오류', error);
    categories = [];
  }

  const listUrl = root.dataset.listUrl;
  const createUrl = root.dataset.createUrl;
  const updateUrlTemplate = root.dataset.updateUrlTemplate;
  const deleteUrlTemplate = root.dataset.deleteUrlTemplate;
  const reorderUrl = root.dataset.reorderUrl;

  const grid = document.getElementById('product-category-grid');
  const countLabel = document.getElementById('product-category-count');
  const createForm = document.getElementById('product-category-create-form');
  const nameInput = document.getElementById('product-category-name');
  const notificationRoot = document.getElementById('product-category-notification');
  const notificationPanel = notificationRoot ? notificationRoot.querySelector('.notification-panel') : null;

  const editModal = document.getElementById('product-category-edit-modal');
  const editForm = document.getElementById('product-category-edit-form');
  const editNameInput = document.getElementById('product-category-edit-name');
  let editingCategoryId = null;

  const csrfToken = config.csrfToken || document.querySelector('input[name=csrfmiddlewaretoken]')?.value;

  function escapeHtml(value) {
    return value.replace(/[&<>'"]/g, (match) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    })[match]);
  }

  function showNotification(message, type = 'success') {
    if (!notificationRoot || !notificationPanel) {
      window.alert(message);
      return;
    }

    notificationPanel.classList.toggle('error', type === 'error');
    notificationPanel.innerHTML = `
      <div class="icon">
        <i class="fas ${type === 'error' ? 'fa-times' : 'fa-check'}"></i>
      </div>
      <div class="text-sm">${escapeHtml(message)}</div>
    `;

    notificationRoot.classList.remove('hidden');
    notificationRoot.classList.add('block');

    setTimeout(() => {
      notificationRoot.classList.add('hidden');
      notificationRoot.classList.remove('block');
    }, 3000);
  }

  function buildActionButtons(category) {
    if (category.is_default) {
      return '<span class="text-[11px] px-2 py-1 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">기본 카테고리</span>';
    }

    return [
      '<button type="button" class="action-btn edit" title="이름 수정">',
      '<i class="fas fa-edit"></i>',
      '</button>',
      '<button type="button" class="action-btn delete" title="삭제">',
      '<i class="fas fa-trash"></i>',
      '</button>'
    ].join('');
  }

  function renderCategories() {
    if (!grid) {
      return;
    }

    const sorted = [...categories].sort((a, b) => {
      if (a.order === b.order) {
        return a.id - b.id;
      }
      return a.order - b.order;
    });

    grid.innerHTML = '';

    sorted.forEach((category) => {
      const article = document.createElement('article');
      article.className = 'product-category-card';
      article.dataset.categoryId = String(category.id);
      article.dataset.isDefault = category.is_default ? 'true' : 'false';
      article.innerHTML = `
        <div class="category-card-surface">
          <div class="flex items-start justify-between gap-3 mb-3">
            <div class="flex items-center gap-3">
              <div class="flex flex-col gap-2">
                <button type="button" class="reorder-btn" data-direction="up" title="위로 이동">
                  <i class="fas fa-chevron-up"></i>
                </button>
                <button type="button" class="reorder-btn" data-direction="down" title="아래로 이동">
                  <i class="fas fa-chevron-down"></i>
                </button>
              </div>
              <div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white truncate">${escapeHtml(category.name)}</h3>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <i class="fas fa-box-open mr-1"></i>${category.product_count}개 상품
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              ${buildActionButtons(category)}
            </div>
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400">정렬 순서: ${category.order}</div>
        </div>
      `;

      grid.appendChild(article);
    });

    if (countLabel) {
      countLabel.textContent = `총 ${sorted.length}개`;
    }

    attachCardListeners();
  }

  function updateOrdersAndPersist() {
    categories.sort((a, b) => a.order - b.order || a.id - b.id);

    let orderCounter = 1;
    categories.forEach((category) => {
      if (category.is_default) {
        category.order = 0;
      } else {
        category.order = orderCounter;
        orderCounter += 1;
      }
    });

    const payload = {
      orders: categories.map((category) => ({
        id: category.id,
        order: category.order,
      })),
    };

    fetchWithCsrf(reorderUrl, {
      method: 'POST',
      body: JSON.stringify(payload),
    }).then((response) => {
      if (!response.success) {
        showNotification(response.error || '카테고리 순서 변경에 실패했습니다.', 'error');
        return;
      }
      showNotification('카테고리 순서가 변경되었습니다.');
      renderCategories();
    }).catch((error) => {
      console.error(error);
      showNotification('카테고리 순서 변경에 실패했습니다.', 'error');
    });
  }

  function attachCardListeners() {
    const cards = grid.querySelectorAll('.product-category-card');
    cards.forEach((card) => {
      const categoryId = Number(card.dataset.categoryId);
      const category = categories.find((item) => item.id === categoryId);
      if (!category) {
        return;
      }

      const reorderButtons = card.querySelectorAll('.reorder-btn');
      reorderButtons.forEach((button) => {
        button.addEventListener('click', () => {
          const direction = button.dataset.direction;
          if (!direction) return;

          if (category.is_default) {
            showNotification('기본 카테고리는 순서를 변경할 수 없습니다.', 'error');
            return;
          }

          const sorted = [...categories].sort((a, b) => a.order - b.order || a.id - b.id);
          const currentIndex = sorted.findIndex((item) => item.id === categoryId);

          if (currentIndex === -1) return;

          if (direction === 'up' && currentIndex === 0) return;
          if (direction === 'down' && currentIndex === sorted.length - 1) return;

          const swapIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
          if (swapIndex < 0 || swapIndex >= sorted.length) return;

          const targetCategory = sorted[swapIndex];
          if (targetCategory.is_default) {
            // 기본 카테고리는 맨 위 고정
            return;
          }

          const tmpOrder = category.order;
          category.order = targetCategory.order;
          targetCategory.order = tmpOrder;

          updateOrdersAndPersist();
        });
      });

      const editButton = card.querySelector('.action-btn.edit');
      if (editButton) {
        editButton.addEventListener('click', () => openEditModal(category));
      }

      const deleteButton = card.querySelector('.action-btn.delete');
      if (deleteButton) {
        deleteButton.addEventListener('click', () => handleDelete(category));
      }
    });
  }

  function fetchWithCsrf(url, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    headers['Content-Type'] = 'application/json';
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    return fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers,
    }).then(async (response) => {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const errorMessage = data.error || '요청 처리 중 오류가 발생했습니다.';
        throw new Error(errorMessage);
      }
      return data;
    });
  }

  function handleCreate(event) {
    event.preventDefault();
    const name = nameInput.value.trim();
    if (!name) {
      showNotification('카테고리 이름을 입력해주세요.', 'error');
      nameInput.focus();
      return;
    }

    fetchWithCsrf(createUrl, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }).then((response) => {
      if (!response.success || !response.category) {
        showNotification(response.error || '카테고리 생성에 실패했습니다.', 'error');
        return;
      }

      categories.push(response.category);
      nameInput.value = '';
      showNotification('새 카테고리가 추가되었습니다.');
      renderCategories();
    }).catch((error) => {
      console.error(error);
      showNotification(error.message || '카테고리 생성에 실패했습니다.', 'error');
    });
  }

  function openEditModal(category) {
    editingCategoryId = category.id;
    editNameInput.value = category.name;
    editModal.classList.remove('hidden');
  }

  function closeEditModal() {
    editingCategoryId = null;
    editModal.classList.add('hidden');
  }

  function handleEditSubmit(event) {
    event.preventDefault();
    if (!editingCategoryId) {
      closeEditModal();
      return;
    }

    const newName = editNameInput.value.trim();
    if (!newName) {
      showNotification('카테고리 이름을 입력해주세요.', 'error');
      return;
    }

    const category = categories.find((item) => item.id === editingCategoryId);
    if (!category) {
      closeEditModal();
      return;
    }

    const url = updateUrlTemplate.replace('/0/', `/${editingCategoryId}/`);

    fetchWithCsrf(url, {
      method: 'PUT',
      body: JSON.stringify({ name: newName }),
    }).then((response) => {
      if (!response.success || !response.category) {
        showNotification(response.error || '카테고리 수정에 실패했습니다.', 'error');
        return;
      }

      category.name = response.category.name;
      category.product_count = response.category.product_count;
      closeEditModal();
      showNotification('카테고리 이름이 수정되었습니다.');
      renderCategories();
    }).catch((error) => {
      console.error(error);
      showNotification(error.message || '카테고리 수정에 실패했습니다.', 'error');
    });
  }

  function handleDelete(category) {
    if (category.is_default) {
      showNotification('기본 카테고리는 삭제할 수 없습니다.', 'error');
      return;
    }

    if (!window.confirm(`"${category.name}" 카테고리를 삭제하시겠습니까?`)) {
      return;
    }

    const url = deleteUrlTemplate.replace('/0/', `/${category.id}/`);

    fetchWithCsrf(url, {
      method: 'DELETE',
    }).then((response) => {
      if (!response.success) {
        showNotification(response.error || '카테고리 삭제에 실패했습니다.', 'error');
        return;
      }

      categories = categories.filter((item) => item.id !== category.id);
      showNotification('카테고리가 삭제되었습니다.');
      renderCategories();
    }).catch((error) => {
      console.error(error);
      showNotification(error.message || '카테고리 삭제에 실패했습니다.', 'error');
    });
  }

  function handleModalDismiss(event) {
    if (event.target.dataset.modalDismiss !== undefined) {
      closeEditModal();
    }
  }

  if (createForm) {
    createForm.addEventListener('submit', handleCreate);
  }

  if (editForm) {
    editForm.addEventListener('submit', handleEditSubmit);
  }

  if (editModal) {
    editModal.addEventListener('click', handleModalDismiss);
  }

  renderCategories();

  // 필요 시 서버 상태와 동기화
  if (listUrl) {
    fetchWithCsrf(listUrl, { method: 'GET' })
      .then((response) => {
        if (response.success && Array.isArray(response.categories)) {
          categories = response.categories;
          renderCategories();
        }
      })
      .catch((error) => console.error('카테고리 목록 갱신 실패', error));
  }
})();
