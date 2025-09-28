(function () {
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  let historyInitialized = false;

  function openModal(modal) {
    if (!modal) {
      return;
    }
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden');
    modal.dispatchEvent(new CustomEvent('modal:open', { bubbles: true }));
  }

  function closeModal(modal) {
    if (!modal) {
      return;
    }
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
    modal.dispatchEvent(new CustomEvent('modal:close', { bubbles: true }));
  }

  function ensureEscapeListener() {
    if (document.__reviewsEscapeListenerAdded) {
      return;
    }
    document.__reviewsEscapeListenerAdded = true;
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') {
        return;
      }
      document.querySelectorAll('[data-review-modal]').forEach((modal) => {
        if (!modal.classList.contains('hidden')) {
          closeModal(modal);
        }
      });
    });
  }

  function setupModal(modal) {
    if (!modal || modal.dataset.reviewModalInitialized === '1') {
      return;
    }
    modal.dataset.reviewModalInitialized = '1';
    ensureEscapeListener();

    const modalId = modal.id;
    document.querySelectorAll(`[data-open-modal="${modalId}"]`).forEach((button) => {
      if (button.dataset.reviewModalTriggerInitialized === '1') {
        return;
      }
      button.dataset.reviewModalTriggerInitialized = '1';
      button.addEventListener('click', (event) => {
        event.preventDefault();
        openModal(modal);
      });
    });

    modal.querySelectorAll('[data-close-modal]').forEach((button) => {
      button.addEventListener('click', () => closeModal(modal));
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        closeModal(modal);
      }
    });
  }

  function initModals(root = document) {
    root.querySelectorAll('[data-review-modal]').forEach((modal) => setupModal(modal));
  }

  function setupRatingControl(control) {
    if (!control || control.dataset.reviewRatingInitialized === '1') {
      return;
    }
    control.dataset.reviewRatingInitialized = '1';

    const input = control.querySelector('input[name="rating"]');
    if (!input) {
      console.warn('[Reviews] Rating input not found for control');
      return;
    }

    const dots = Array.from(control.querySelectorAll('[data-score]'));
    const previewLabel = control.querySelector('[data-rating-preview]');
    const defaultValue = Number(input.dataset.default || input.value || 0);
    const modalElement = control.closest('[data-review-modal]');

    const updateDots = (value) => {
      dots.forEach((dot) => {
        const dotValue = Number(dot.dataset.score || 0);
        const isActive = value > 0 && dotValue <= value;
        dot.classList.toggle('active', isActive);
      });
      if (previewLabel) {
        previewLabel.textContent = value > 0 ? `${value}점` : '선택 없음';
      }
    };

    const setRating = (value) => {
      input.value = value > 0 ? value : '';
      updateDots(value);
    };

    dots.forEach((dot) => {
      const dotValue = Number(dot.dataset.score || 0);
      dot.setAttribute('role', 'button');
      dot.setAttribute('tabindex', '0');
      dot.addEventListener('click', (event) => {
        event.preventDefault();
        setRating(dotValue);
      });
      dot.addEventListener('mouseenter', () => updateDots(dotValue));
      dot.addEventListener('mouseleave', () => {
        const currentValue = Number(input.value || 0);
        updateDots(currentValue);
      });
      dot.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          setRating(dotValue);
        }
      });
    });

    if (modalElement) {
      modalElement.addEventListener('modal:open', () => {
        const currentValue = Number(input.value || defaultValue || 0);
        setRating(currentValue);
      });

      modalElement.addEventListener('modal:close', () => {
        const currentValue = Number(input.value || defaultValue || 0);
        setRating(currentValue);
      });
    }

    setRating(defaultValue);
  }

  function initRatingControls(root = document) {
    root.querySelectorAll('[data-rating-control]').forEach((control) => setupRatingControl(control));
  }

  function setupDropzone(zone) {
    if (!zone || zone.dataset.reviewDropzoneInitialized === '1') {
      return;
    }
    zone.dataset.reviewDropzoneInitialized = '1';

    const inputId = zone.dataset.targetInput;
    const previewId = zone.dataset.previewContainer;
    const maxFiles = Number(zone.dataset.maxFiles || 5);
    const existingCount = Number(zone.dataset.existingCount || 0);

    const input = document.getElementById(inputId);
    const preview = previewId ? document.getElementById(previewId) : null;
    const remainingElement = zone.querySelector('[data-dropzone-remaining]');
    const messageElement = zone.querySelector('[data-dropzone-message]');

    if (!input) {
      return;
    }

    let selectedFiles = [];
    const previewUrlMap = new Map();
    let messageTimeout = null;

    const hideMessage = () => {
      if (!messageElement) {
        return;
      }
      messageElement.classList.add('hidden');
      messageElement.textContent = '';
      if (messageTimeout) {
        clearTimeout(messageTimeout);
        messageTimeout = null;
      }
    };

    const showMessage = (text) => {
      if (!messageElement) {
        console.warn('[Reviews] Dropzone message:', text);
        return;
      }
      messageElement.textContent = text;
      messageElement.classList.remove('hidden');
      if (messageTimeout) {
        clearTimeout(messageTimeout);
      }
      messageTimeout = setTimeout(hideMessage, 4000);
    };

    const updateRemaining = () => {
      if (!remainingElement) {
        return;
      }
      const remaining = Math.max(0, maxFiles - existingCount - selectedFiles.length);
      remainingElement.textContent = remaining;
    };

    const syncInput = () => {
      const transfer = new DataTransfer();
      selectedFiles.forEach((file) => transfer.items.add(file));
      input.files = transfer.files;
    };

    const renderPreview = () => {
      if (!preview) {
        return;
      }
      preview.innerHTML = '';
      selectedFiles.forEach((file, index) => {
        let url = previewUrlMap.get(file);
        if (!url) {
          url = URL.createObjectURL(file);
          previewUrlMap.set(file, url);
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'review-preview-item';

        const image = document.createElement('img');
        image.src = url;
        image.alt = file.name;
        wrapper.appendChild(image);

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'review-preview-remove bg-black/60 text-white text-xs px-2 py-1 rounded-lg';
        button.textContent = '삭제';
        button.addEventListener('click', () => removeFile(index));
        wrapper.appendChild(button);

        preview.appendChild(wrapper);
      });
    };

    const clearObjectUrls = () => {
      previewUrlMap.forEach((url) => URL.revokeObjectURL(url));
      previewUrlMap.clear();
    };

    const reset = () => {
      selectedFiles = [];
      input.value = '';
      syncInput();
      clearObjectUrls();
      if (preview) {
        preview.innerHTML = '';
      }
      updateRemaining();
      hideMessage();
    };

    const addFile = (file) => {
      if (existingCount + selectedFiles.length >= maxFiles) {
        console.warn('[Reviews] Dropzone limit reached', { modalId: zone.closest('[data-review-modal]')?.id, maxFiles });
        showMessage(`이미지는 최대 ${maxFiles}개까지 업로드할 수 있습니다.`);
        return;
      }
      if (!file.type.startsWith('image/')) {
        console.warn('[Reviews] Non-image file rejected', { fileName: file.name, type: file.type });
        showMessage('이미지 파일만 업로드할 수 있습니다.');
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        const size = (file.size / 1024 / 1024).toFixed(2);
        console.warn('[Reviews] Oversize file rejected', { fileName: file.name, sizeMB: size });
        showMessage(`"${file.name}" 파일이 10MB를 초과합니다. (${size}MB)`);
        return;
      }
      selectedFiles.push(file);
      console.log('[Reviews] File added', { fileName: file.name, totalSelected: selectedFiles.length });
      hideMessage();
    };

    const removeFile = (index) => {
      if (index < 0 || index >= selectedFiles.length) {
        return;
      }
      const [removed] = selectedFiles.splice(index, 1);
      const url = previewUrlMap.get(removed);
      if (url) {
        URL.revokeObjectURL(url);
        previewUrlMap.delete(removed);
      }
      syncInput();
      renderPreview();
      updateRemaining();
      console.log('[Reviews] File removed', { fileName: removed.name, totalSelected: selectedFiles.length });
    };

    const handleFiles = (fileList) => {
      const files = Array.from(fileList);
      const availableSlots = maxFiles - existingCount - selectedFiles.length;
      if (availableSlots <= 0) {
        console.warn('[Reviews] No slots left for files', { maxFiles });
        showMessage(`이미지는 최대 ${maxFiles}개까지 업로드할 수 있습니다.`);
        return;
      }
      files.forEach((file) => addFile(file));
      syncInput();
      renderPreview();
      updateRemaining();
      console.log('[Reviews] handleFiles complete', { selectedFiles: selectedFiles.length });
    };

    const dropTrigger = zone.querySelector('[data-drop-trigger]');

    if (dropTrigger) {
      dropTrigger.addEventListener('click', () => {
        if (!input.disabled) {
          input.click();
        }
      });
    } else {
      zone.addEventListener('click', () => {
        if (!input.disabled) {
          input.click();
        }
      });
    }

    zone.addEventListener('dragover', (event) => {
      event.preventDefault();
      if (input.disabled) {
        return;
      }
      zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', (event) => {
      event.preventDefault();
      if (event.target === zone) {
        zone.classList.remove('dragover');
      }
    });

    zone.addEventListener('drop', (event) => {
      event.preventDefault();
      zone.classList.remove('dragover');
      if (input.disabled) {
        return;
      }
      handleFiles(event.dataTransfer.files);
    });

    input.addEventListener('change', (event) => {
      if (!event.target.files) {
        return;
      }
      handleFiles(event.target.files);
      event.target.value = '';
    });

    const modalElement = zone.closest('[data-review-modal]');
    if (modalElement) {
      modalElement.addEventListener('modal:close', reset);
      modalElement.addEventListener('modal:open', hideMessage);
    }
    updateRemaining();
    console.log('[Reviews] Dropzone initialized', { maxFiles, existingCount });
  }

  function initDropzones(root = document) {
    root.querySelectorAll('[data-review-dropzone]').forEach((zone) => setupDropzone(zone));
  }

  function initFormDebug(root = document) {
    root.querySelectorAll('[data-review-modal] form').forEach((form) => {
      if (form.dataset.reviewDebugInitialized === '1') {
        return;
      }
      form.dataset.reviewDebugInitialized = '1';
      form.addEventListener('submit', () => {
        const ratingInput = form.querySelector('input[name="rating"]');
        const filesInput = form.querySelector('input[type="file"]');
        const fileNames = filesInput && filesInput.files ? Array.from(filesInput.files).map((file) => file.name) : [];
        console.log('[Reviews] Form submit', {
          modalId: form.closest('[data-review-modal]')?.id,
          ratingValue: ratingInput ? ratingInput.value : null,
          fileCount: filesInput?.files ? filesInput.files.length : 0,
          fileNames,
        });
      });
    });
  }

  function setupDeleteConfirm(root = document) {
    root.querySelectorAll('form[data-confirm-message]').forEach((form) => {
      if (form.dataset.reviewConfirmInitialized === '1') {
        return;
      }
      form.dataset.reviewConfirmInitialized = '1';
      form.addEventListener('submit', (event) => {
        const message = form.dataset.confirmMessage || '삭제하시겠습니까?';
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });
  }

  function loadReviews(url, pushHistory = true) {
    const reviewsContent = document.getElementById('reviewsContent');
    if (!reviewsContent) {
      return;
    }

    const [fetchUrl, hash] = url.split('#');
    reviewsContent.classList.add('opacity-50', 'pointer-events-none');

    fetch(fetchUrl, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.text();
      })
      .then((html) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newContent = doc.getElementById('reviewsContent');
        if (!newContent) {
          window.location.href = url;
          return;
        }
        reviewsContent.replaceWith(newContent);
        const finalUrl = hash ? `${fetchUrl}#${hash}` : fetchUrl;
        if (pushHistory) {
          window.history.pushState({ reviewsUrl: finalUrl }, '', finalUrl);
        }
        setupReviewComponents(document);
        const reviewsSection = document.getElementById('reviews');
        if (reviewsSection) {
          reviewsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      })
      .catch((error) => {
        console.error('[Reviews] Failed to load review page', error);
        window.location.href = url;
      })
      .finally(() => {
        const refreshedContent = document.getElementById('reviewsContent');
        if (refreshedContent) {
          refreshedContent.classList.remove('opacity-50', 'pointer-events-none');
        }
      });
  }

  function setupPagination() {
    const reviewsContent = document.getElementById('reviewsContent');
    if (!reviewsContent) {
      return;
    }
    reviewsContent.querySelectorAll('[data-review-page-link]').forEach((link) => {
      if (link.dataset.reviewPaginationInitialized === '1') {
        return;
      }
      link.dataset.reviewPaginationInitialized = '1';
      link.addEventListener('click', (event) => {
        event.preventDefault();
        const url = link.getAttribute('href');
        if (!url) {
          return;
        }
        loadReviews(url, true);
      });
    });
  }

  function initHistory() {
    if (historyInitialized) {
      return;
    }
    historyInitialized = true;
    if (!window.history.state || !window.history.state.reviewsUrl) {
      window.history.replaceState({ reviewsUrl: window.location.href }, '', window.location.href);
    }
    window.addEventListener('popstate', (event) => {
      const url = (event.state && event.state.reviewsUrl) || window.location.href;
      loadReviews(url, false);
    });
  }


  function setupSubmitState(root = document) {
    root.querySelectorAll('[data-review-modal]').forEach((modal) => {
      const ratingInput = modal.querySelector('[data-review-rating-input]');
      const contentInput = modal.querySelector('[data-review-content]');
      const submitButton = modal.querySelector('[data-review-submit]');

      if (!submitButton || submitButton.dataset.reviewSubmitInitialized === '1') {
        return;
      }
      submitButton.dataset.reviewSubmitInitialized = '1';

      const toggleButtonState = () => {
        const ratingValue = Number(ratingInput?.value || 0);
        const contentValue = (contentInput?.value || '').trim();
        const isValid = ratingValue > 0 && contentValue.length > 0;
        submitButton.disabled = !isValid;
      };

      if (ratingInput && ratingInput.dataset.reviewSubmitListener !== '1') {
        ratingInput.dataset.reviewSubmitListener = '1';
        const observer = new MutationObserver(toggleButtonState);
        observer.observe(ratingInput, { attributes: true, attributeFilter: ['value'] });
      }

      if (contentInput) {
        const maxLength = Number(contentInput.dataset.maxlength || contentInput.getAttribute('maxlength') || 1000);
        contentInput.addEventListener('input', () => {
          if (contentInput.value.length > maxLength) {
            contentInput.value = contentInput.value.slice(0, maxLength);
          }
          toggleButtonState();
        });
      }

      modal.addEventListener('modal:open', toggleButtonState);
      toggleButtonState();
    });
  }

  function setupReviewComponents(root = document) {
    initModals(root);
    initRatingControls(root);
    initDropzones(root);
    initFormDebug(root);
    setupDeleteConfirm(root);
    setupSubmitState(root);
    setupPagination();
  }

  window.initReviewsUI = () => setupReviewComponents(document);

  document.addEventListener('DOMContentLoaded', () => {
    console.log('[Reviews] DOMContentLoaded - initializing components');
    setupReviewComponents(document);
    initHistory();
  });
})();
