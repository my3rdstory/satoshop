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

  const productsUrl = root.dataset.productsUrl;
  const assignUrl = root.dataset.assignUrl;

  const openMatchPanelButton = document.getElementById('openProductMatchPanel');
  const matchPanel = document.getElementById('productMatchPanel');
  const matchCategoryList = document.getElementById('matchCategoryList');
  const matchCategoryCount = document.getElementById('matchCategoryCount');
  const matchProductList = document.getElementById('matchProductList');
  const matchProductEmpty = document.getElementById('matchProductEmpty');
  const matchProductStats = document.getElementById('matchProductStats');
  const matchPrevPage = document.getElementById('matchPrevPage');
  const matchNextPage = document.getElementById('matchNextPage');
  const matchProductSearch = document.getElementById('matchProductSearch');
  const refreshMatchDataButton = document.getElementById('refreshMatchData');

  const matchState = {
    selectedCategoryId: null,
    page: 1,
    pageSize: 30,
    total: 0,
    hasNext: false,
    search: '',
    loading: false,
    products: [],
  };

  let matchSearchTimer = null;

  const rawCsrfFromDom = document.querySelector('input[name=csrfmiddlewaretoken]')?.value;
  const csrfToken = config.csrfToken || rawCsrfFromDom;

  function getCsrfToken() {
    if (csrfToken && csrfToken !== 'undefined' && csrfToken !== 'null' && csrfToken !== 'csrf_token') {
      return csrfToken;
    }

    const cookieEntry = document.cookie
      .split(';')
      .map((pair) => pair.trim())
      .find((pair) => pair.startsWith('csrftoken='));

    if (cookieEntry) {
      return decodeURIComponent(cookieEntry.split('=')[1]);
    }

    return null;
  }

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
    renderMatchCategories();
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

  function getDefaultCategoryId() {
    const defaultCategory = categories.find((item) => item.is_default);
    return defaultCategory ? defaultCategory.id : null;
  }

  function renderMatchCategories() {
    if (!matchCategoryList) return;

    matchCategoryList.innerHTML = '';

    if (!categories.length) {
      matchState.selectedCategoryId = null;
      if (matchCategoryCount) {
        matchCategoryCount.textContent = '총 0개';
      }
      return;
    }

    if (!categories.some((item) => item.id === matchState.selectedCategoryId)) {
      const defaultId = getDefaultCategoryId();
      const fallbackId = defaultId || categories[0].id;
      matchState.selectedCategoryId = fallbackId === null ? null : Number(fallbackId);
    }

    const sorted = [...categories].sort((a, b) => {
      if (a.is_default && !b.is_default) return -1;
      if (!a.is_default && b.is_default) return 1;
      if (a.order === b.order) return a.id - b.id;
      return a.order - b.order;
    });

    sorted.forEach((category) => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div class="match-category-item" data-category-id="${category.id}">
          <div class="match-category-item__title">
            <span>${escapeHtml(category.name)}</span>
            <span class="text-xs px-2 py-0.5 rounded-full ${category.is_default ? 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300' : 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-200'}">
              ${category.is_default ? '기본' : `#${category.order}`}
            </span>
          </div>
          <div class="match-category-item__meta">
            상품 ${category.product_count}개
          </div>
        </div>
      `;

      const item = li.firstElementChild;
      if (Number(matchState.selectedCategoryId) === category.id) {
        item.classList.add('match-category-item--active');
      }

      item.addEventListener('click', () => {
        setSelectedMatchCategory(category.id);
      });

      matchCategoryList.appendChild(li);
    });

    if (matchCategoryCount) {
      matchCategoryCount.textContent = `총 ${sorted.length}개`;
    }

    updateMatchProductSelectionStyles();
  }

  function setSelectedMatchCategory(categoryId) {
    if (matchState.selectedCategoryId === categoryId) {
      return;
    }

    matchState.selectedCategoryId = categoryId === null ? null : Number(categoryId);
    renderMatchCategories();
    updateMatchProductSelectionStyles();
  }

  function isProductInSelectedCategory(product) {
    if (!product) return false;
    if (matchState.selectedCategoryId === null || matchState.selectedCategoryId === undefined) {
      return false;
    }

    return Number(product.category_id) === Number(matchState.selectedCategoryId);
  }

  function updateMatchProductSelectionStyles() {
    if (!matchProductList) return;

    const cards = matchProductList.querySelectorAll('.match-product-card');
    cards.forEach((card) => {
      const productId = Number(card.dataset.productId);
      const product = matchState.products.find((item) => Number(item.id) === productId);
      const isSelected = isProductInSelectedCategory(product);
      card.classList.toggle('match-product-card--selected', isSelected);
    });
  }

  function fetchWithCsrf(url, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    headers['Content-Type'] = 'application/json';
    const token = getCsrfToken();
    if (token) {
      headers['X-CSRFToken'] = token;
    }
    headers['X-Requested-With'] = 'XMLHttpRequest';

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

  function updateCategoryCountsAfterAssign(oldCategoryId, newCategoryId) {
    if (oldCategoryId === newCategoryId) {
      return;
    }

    categories = categories.map((category) => {
      const updated = { ...category };
      if (oldCategoryId && updated.id === oldCategoryId && updated.product_count > 0) {
        updated.product_count -= 1;
      }
      if (newCategoryId && updated.id === newCategoryId) {
        updated.product_count += 1;
      }
      return updated;
    });

    renderCategories();
  }

  function updateMatchPaginationControls() {
    if (!matchPrevPage || !matchNextPage) return;

    matchPrevPage.disabled = matchState.page <= 1 || matchState.loading;
    matchNextPage.disabled = !matchState.hasNext || matchState.loading;

    if (matchProductStats) {
      if (!matchState.total) {
        matchProductStats.textContent = '표시할 상품이 없습니다.';
      } else {
        const start = (matchState.page - 1) * matchState.pageSize + 1;
        const end = Math.min(matchState.total, start + matchState.products.length - 1);
        matchProductStats.textContent = `총 ${matchState.total}개 중 ${start} - ${end}`;
      }
    }
  }

  function renderMatchProducts() {
    if (!matchProductList || !matchProductEmpty) return;

    matchProductList.innerHTML = '';

    if (!matchState.products.length) {
      matchProductEmpty.classList.remove('hidden');
      updateMatchPaginationControls();
      return;
    }

    matchProductEmpty.classList.add('hidden');

    matchState.products.forEach((product) => {
      const card = document.createElement('div');
      card.className = 'match-product-card';
      card.dataset.productId = product.id;
      card.dataset.categoryId = product.category_id ?? '';

      const categoryName = product.category_name || '카테고리 없음';
      const categoryBadge = product.category_id ? 'match-product-card__category' : 'match-product-card__category bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
      const statusClass = product.is_active ? 'match-product-card__status' : 'match-product-card__status match-product-card__status--inactive';
      const statusLabel = product.is_active ? '판매중' : '비활성';
      const stockBadge = product.is_temporarily_out_of_stock
        ? '<span class="match-product-card__status match-product-card__status--inactive"><i class="fas fa-pause"></i> 일시품절</span>'
        : '';

      card.innerHTML = `
        <div class="match-product-card__title">${escapeHtml(product.title)}</div>
        <div class="match-product-card__meta">
          <span class="${categoryBadge}">
            <i class="fas fa-tags"></i> ${escapeHtml(categoryName)}
          </span>
          <span class="${statusClass}">
            <i class="fas ${product.is_active ? 'fa-check' : 'fa-ban'}"></i> ${statusLabel}
          </span>
          ${stockBadge}
          <span class="text-xs text-gray-400 dark:text-gray-500">
            등록 ${product.created_at_display}
          </span>
        </div>
        <div class="match-product-card__footer">
          <span>#${product.id}</span>
          <span>${product.price_label}</span>
        </div>
      `;

      if (isProductInSelectedCategory(product)) {
        card.classList.add('match-product-card--selected');
      }

      card.addEventListener('click', () => handleAssignProduct(product, card));
      matchProductList.appendChild(card);
    });

    updateMatchPaginationControls();
    updateMatchProductSelectionStyles();
  }

  function loadMatchProducts({ resetPage = false } = {}) {
    if (!productsUrl) return;
    if (!matchPanel || matchPanel.classList.contains('hidden')) return;

    if (resetPage) {
      matchState.page = 1;
    }

    matchState.loading = true;
    updateMatchPaginationControls();

    const params = new URLSearchParams();
    params.set('page', matchState.page);
    params.set('page_size', matchState.pageSize);
    if (matchState.search) {
      params.set('search', matchState.search);
    }

    fetchWithCsrf(`${productsUrl}?${params.toString()}`, { method: 'GET' })
      .then((response) => {
        if (!response.success) {
          throw new Error(response.error || '상품 목록을 불러오지 못했습니다.');
        }

        matchState.products = response.products || [];
        matchState.total = response.total || 0;
        matchState.hasNext = Boolean(response.has_next);
        matchState.page = response.page || matchState.page;

        renderMatchProducts();
      })
      .catch((error) => {
        console.error('상품 목록 로드 실패', error);
        showNotification(error.message || '상품 목록을 불러오지 못했습니다.', 'error');
      })
      .finally(() => {
        matchState.loading = false;
        updateMatchPaginationControls();
        updateMatchProductSelectionStyles();
      });
  }

  function handleAssignProduct(product, cardElement) {
    if (!assignUrl) {
      showNotification('카테고리 매칭 기능을 사용할 수 없습니다.', 'error');
      return;
    }

    if (!matchState.selectedCategoryId) {
      showNotification('먼저 왼쪽에서 카테고리를 선택해주세요.', 'error');
      return;
    }

    const targetCategoryId = matchState.selectedCategoryId;

    if (Number(product.category_id) === Number(targetCategoryId)) {
      cardElement.classList.add('match-product-card--selected');
      showNotification('이미 선택한 카테고리에 속한 상품입니다.');
      return;
    }

    const payload = {
      product_id: product.id,
      category_id: targetCategoryId,
    };

    cardElement.classList.add('opacity-60');

    fetchWithCsrf(assignUrl, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
      .then((response) => {
        if (!response.success || !response.product) {
          throw new Error(response.error || '상품을 카테고리에 매칭하지 못했습니다.');
        }

        const updatedProduct = response.product;
        const previousCategoryId = product.category_id || null;
        product.category_id = updatedProduct.category_id;
        product.category_name = updatedProduct.category_name;
        cardElement.dataset.categoryId = updatedProduct.category_id ?? '';

        const badge = cardElement.querySelector('.match-product-card__category');
        if (badge) {
          badge.innerHTML = `<i class="fas fa-tags"></i> ${escapeHtml(product.category_name || '카테고리 없음')}`;
          if (product.category_id) {
            badge.className = 'match-product-card__category';
          } else {
            badge.className = 'match-product-card__category bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
          }
        }

        updateCategoryCountsAfterAssign(previousCategoryId, product.category_id || null);
        updateMatchProductSelectionStyles();
        showNotification('상품이 선택한 카테고리에 매칭되었습니다.');
      })
      .catch((error) => {
        console.error('카테고리 매칭 실패', error);
        showNotification(error.message || '상품을 카테고리에 매칭하지 못했습니다.', 'error');
      })
      .finally(() => {
        cardElement.classList.remove('opacity-60');
      });
  }

  function openMatchPanel() {
    if (!matchPanel) return;

    matchPanel.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');

    matchState.search = '';
    if (matchProductSearch) {
      matchProductSearch.value = '';
    }

    renderMatchCategories();
    loadMatchProducts({ resetPage: true });
  }

  function closeMatchPanel() {
    if (!matchPanel) return;
    matchPanel.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
  }

  function refreshMatchPanelData() {
    const promises = [];
    if (listUrl) {
      promises.push(
        fetchWithCsrf(listUrl, { method: 'GET' })
          .then((response) => {
            if (response.success && Array.isArray(response.categories)) {
              categories = response.categories;
              renderCategories();
            }
          })
          .catch((error) => console.error('카테고리 목록 갱신 실패', error))
      );
    }

    Promise.all(promises).finally(() => {
      loadMatchProducts({ resetPage: true });
      showNotification('최신 데이터로 새로고침했습니다.');
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

  if (openMatchPanelButton && matchPanel) {
    openMatchPanelButton.addEventListener('click', openMatchPanel);
  }

  if (matchPanel) {
    document.querySelectorAll('[data-match-dismiss]').forEach((element) => {
      element.addEventListener('click', closeMatchPanel);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !matchPanel.classList.contains('hidden')) {
        closeMatchPanel();
      }
    });
  }

  if (matchPrevPage) {
    matchPrevPage.addEventListener('click', () => {
      if (matchState.page > 1 && !matchState.loading) {
        matchState.page -= 1;
        loadMatchProducts();
      }
    });
  }

  if (matchNextPage) {
    matchNextPage.addEventListener('click', () => {
      if (matchState.hasNext && !matchState.loading) {
        matchState.page += 1;
        loadMatchProducts();
      }
    });
  }

  if (matchProductSearch) {
    matchProductSearch.addEventListener('input', (event) => {
      const value = event.target.value.trim();
      if (matchSearchTimer) {
        clearTimeout(matchSearchTimer);
      }
      matchSearchTimer = setTimeout(() => {
        matchState.search = value;
        loadMatchProducts({ resetPage: true });
      }, 300);
    });
  }

  if (refreshMatchDataButton) {
    refreshMatchDataButton.addEventListener('click', refreshMatchPanelData);
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
