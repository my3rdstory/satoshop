(function () {
  const feedbackClassMap = {
    success: 'text-green-600 dark:text-green-300',
    error: 'text-red-600 dark:text-red-300',
    warning: 'text-amber-600 dark:text-amber-300',
    info: 'text-gray-500 dark:text-gray-400',
  };

  const getCsrfToken = () => {
    const csrfForm = document.querySelector('#featured-csrf input[name="csrfmiddlewaretoken"]');
    if (csrfForm) {
      return csrfForm.value;
    }
    const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
    return cookieMatch ? cookieMatch[1] : '';
  };

  const setFeedback = (element, message, variant = 'info') => {
    if (!element) return;
    element.textContent = message || '';
    element.className = `text-xs ${feedbackClassMap[variant] || feedbackClassMap.info}`;
  };

  const createSelectedElement = (payload) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'selected-card';
    wrapper.dataset.selectedItem = 'true';
    wrapper.dataset.itemId = payload.id;

    const order = document.createElement('div');
    order.className = 'order-indicator';
    order.dataset.orderIndicator = 'true';
    order.textContent = '0';

    const body = document.createElement('div');
    body.className = 'flex-1';

    const title = document.createElement('p');
    title.className = 'selected-title';
    title.textContent = payload.title || '';

    const meta = document.createElement('p');
    meta.className = 'selected-meta';
    meta.textContent = payload.metaPrimary || '';

    body.appendChild(title);
    if (payload.metaPrimary) {
      body.appendChild(meta);
    }
    if (payload.metaSecondary) {
      const sub = document.createElement('p');
      sub.className = 'selected-meta-secondary';
      sub.textContent = payload.metaSecondary;
      body.appendChild(sub);
    }
    if (payload.badge) {
      const badge = document.createElement('span');
      badge.className = 'selected-badge';
      badge.textContent = payload.badge;
      body.appendChild(badge);
    }

    const actions = document.createElement('div');
    actions.className = 'selected-actions';

    const upButton = document.createElement('button');
    upButton.type = 'button';
    upButton.className = 'action-btn';
    upButton.dataset.move = 'up';
    upButton.setAttribute('aria-label', '위로 이동');
    upButton.innerHTML = '<i class="fas fa-chevron-up"></i>';

    const downButton = document.createElement('button');
    downButton.type = 'button';
    downButton.className = 'action-btn';
    downButton.dataset.move = 'down';
    downButton.setAttribute('aria-label', '아래로 이동');
    downButton.innerHTML = '<i class="fas fa-chevron-down"></i>';

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'action-btn danger';
    removeButton.dataset.remove = 'true';
    removeButton.setAttribute('aria-label', '선택 해제');
    removeButton.innerHTML = '<i class="fas fa-times"></i>';

    actions.appendChild(upButton);
    actions.appendChild(downButton);
    actions.appendChild(removeButton);

    wrapper.appendChild(order);
    wrapper.appendChild(body);
    wrapper.appendChild(actions);
    return wrapper;
  };

  const syncOrderIndicators = (selectedList, placeholder, counterEl, limit, saveButton, state, availableButtons) => {
    const items = Array.from(selectedList.querySelectorAll('[data-selected-item]'));
    items.forEach((item, index) => {
      const indicator = item.querySelector('[data-order-indicator]') || item.querySelector('[data-order-indicator="true"]');
      if (indicator) {
        indicator.textContent = String(index + 1);
      }
    });
    state.selectedIds = items.map((item) => Number(item.dataset.itemId));
    if (placeholder) {
      placeholder.classList.toggle('hidden', items.length > 0);
    }
    if (counterEl) {
      counterEl.textContent = `${state.selectedIds.length} / ${limit}`;
    }
    if (saveButton && !state.saving) {
      saveButton.disabled = !state.dirty;
    }
    if (availableButtons) {
      const selectedSet = new Set(state.selectedIds);
      availableButtons.forEach((button) => {
        const id = Number(button.dataset.itemId);
        button.classList.toggle('is-selected', selectedSet.has(id));
      });
    }
  };

  const bindSection = (section, csrfToken) => {
    const selectedList = section.querySelector('[data-selected-list]');
    const placeholder = section.querySelector('[data-selected-empty]');
    const counterEl = section.querySelector('[data-selection-counter]');
    const saveButton = section.querySelector('[data-save-featured]');
    const feedback = section.querySelector('[data-feedback]');
    const availableButtons = Array.from(section.querySelectorAll('[data-available-item]'));
    const limit = Number(section.dataset.limit || '0');
    const updateUrl = section.dataset.updateUrl;
    if (!selectedList || !counterEl) {
      return;
    }
    const state = {
      itemType: section.dataset.itemType,
      limit,
      updateUrl,
      selectedIds: Array.from(selectedList.querySelectorAll('[data-selected-item]')).map((item) => Number(item.dataset.itemId)),
      dirty: false,
      saving: false,
    };

    const refreshUi = () => {
      syncOrderIndicators(selectedList, placeholder, counterEl, limit, saveButton, state, availableButtons);
    };

    const handleAvailableClick = (button) => {
      const id = Number(button.dataset.itemId);
      if (state.selectedIds.includes(id)) {
        setFeedback(feedback, '이미 선택된 항목입니다.', 'warning');
        return;
      }
      if (state.selectedIds.length >= limit) {
        setFeedback(feedback, `최대 ${limit}개까지만 선택할 수 있습니다.`, 'warning');
        return;
      }
      const payload = {
        id,
        title: button.dataset.title || '',
        metaPrimary: button.dataset.metaprimary || '',
        metaSecondary: button.dataset.metasecondary || '',
        badge: button.dataset.badge || '',
      };
      const element = createSelectedElement(payload);
      selectedList.appendChild(element);
      state.dirty = true;
      setFeedback(feedback, '선택 영역에 추가했습니다.', 'success');
      refreshUi();
    };

    const handleMove = (item, direction) => {
      if (!item) return;
      if (direction === 'up') {
        const prev = item.previousElementSibling;
        if (prev) {
          selectedList.insertBefore(item, prev);
          state.dirty = true;
          refreshUi();
        }
      } else if (direction === 'down') {
        const next = item.nextElementSibling;
        if (next) {
          selectedList.insertBefore(next, item);
          state.dirty = true;
          refreshUi();
        }
      }
    };

    const handleRemove = (item) => {
      if (!item) return;
      item.remove();
      state.dirty = true;
      refreshUi();
      setFeedback(feedback, '선택 목록에서 제외했습니다.', 'info');
    };

    availableButtons.forEach((button) => {
      button.addEventListener('click', () => handleAvailableClick(button));
    });

    selectedList.addEventListener('click', (event) => {
      const actionBtn = event.target.closest('[data-move], [data-remove]');
      if (!actionBtn) {
        return;
      }
      const card = actionBtn.closest('[data-selected-item]');
      if (!card) {
        return;
      }
      if (actionBtn.dataset.move) {
        handleMove(card, actionBtn.dataset.move);
        return;
      }
      if (actionBtn.dataset.remove !== undefined) {
        handleRemove(card);
      }
    });

    const saveChanges = () => {
      if (!state.dirty || state.saving) {
        return;
      }
      state.saving = true;
      saveButton.disabled = true;
      setFeedback(feedback, '저장 중입니다...', 'info');

      fetch(state.updateUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          item_type: state.itemType,
          selected_ids: state.selectedIds,
        }),
      })
        .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) {
            throw new Error(data && data.error ? data.error : '저장에 실패했습니다.');
          }
          state.dirty = false;
          setFeedback(feedback, data.message || '저장되었습니다.', 'success');
        })
        .catch((error) => {
          setFeedback(feedback, error.message, 'error');
        })
        .finally(() => {
          state.saving = false;
          refreshUi();
        });
    };

    if (saveButton) {
      saveButton.addEventListener('click', saveChanges);
    }

    refreshUi();
  };

  document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = getCsrfToken();
    document.querySelectorAll('[data-featured-section]').forEach((section) => {
      bindSection(section, csrfToken);
    });
  });
})();
