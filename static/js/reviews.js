(function () {
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const X_POST_URL_REGEX = /(https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/[A-Za-z0-9_]+\/status\/\d+(?:\?[^\s]*)?)/i;
  const TRAILING_PUNCTUATION_REGEX = /[).,]+$/;
  const EMBED_DEBOUNCE_MS = 350;
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
      syncInput();
    });

    const modalElement = zone.closest('[data-review-modal]');
    if (modalElement) {
      modalElement.addEventListener('modal:close', reset);
      modalElement.addEventListener('modal:open', hideMessage);
    }
    updateRemaining();
  }

  function initDropzones(root = document) {
    root.querySelectorAll('[data-review-dropzone]').forEach((zone) => setupDropzone(zone));
  }

  function normalizeXPostUrl(url) {
    if (!url) {
      return '';
    }
    let trimmed = url.trim();
    if (!trimmed) {
      return '';
    }
    if (trimmed.slice(0, 7).toLowerCase() === 'http://') {
      trimmed = `https://${trimmed.slice(7)}`;
    }
    return trimmed.replace(TRAILING_PUNCTUATION_REGEX, '');
  }

  function extractXPostUrl(text) {
    if (!text) {
      return null;
    }
    const match = text.match(X_POST_URL_REGEX);
    if (!match) {
      return null;
    }
    return normalizeXPostUrl(match[0]);
  }

  function createCsrfFetch() {
    if (typeof window.fetchWithCsrf === 'function') {
      return window.fetchWithCsrf;
    }
    return (url, options = {}) => {
      const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
      };
      const token = typeof window.getCsrfToken === 'function' ? window.getCsrfToken() : null;
      if (token) {
        headers['X-CSRFToken'] = token;
      }
      return fetch(url, {
        ...options,
        headers,
        credentials: 'same-origin',
      });
    };
  }

  function resolveEmbedEndpoint(element) {
    if (!element) {
      return null;
    }
    if (element.dataset && element.dataset.reviewEmbedEndpoint) {
      return element.dataset.reviewEmbedEndpoint;
    }
    if (typeof element.closest === 'function') {
      const ancestor = element.closest('[data-review-embed-endpoint]');
      if (ancestor && ancestor.dataset) {
        return ancestor.dataset.reviewEmbedEndpoint || null;
      }
    }
    return null;
  }

  const fetchEmbedPreview = (() => {
    let cachedFetcher = null;
    const cache = new Map();

    return (endpoint, url, options = {}) => {
      const { signal, useCache = true } = options || {};
      const cacheKey = useCache ? url : null;

      if (cacheKey && cache.has(cacheKey)) {
        return cache.get(cacheKey);
      }

      if (!cachedFetcher) {
        cachedFetcher = createCsrfFetch();
      }

      const request = cachedFetcher(endpoint, {
        method: 'POST',
        body: JSON.stringify({ url }),
        signal,
      })
        .then((response) => {
          if (!response.ok) {
            const error = new Error(`HTTP_${response.status}`);
            error.status = response.status;
            throw error;
          }
          return response.json();
        })
        .catch((error) => {
          if (cacheKey) {
            cache.delete(cacheKey);
          }
          throw error;
        });

      if (cacheKey) {
        cache.set(cacheKey, request);
      }

      return request;
    };
  })();

  function createEmbedView(wrapper) {
    if (!wrapper) {
      return null;
    }

    const authorElement = wrapper.querySelector('[data-review-embed-author]');
    const sourceElement = wrapper.querySelector('[data-review-embed-source]');
    const textElement = wrapper.querySelector('[data-review-embed-text]');
    const linkElement = wrapper.querySelector('[data-review-embed-link]');
    const loadingElement = wrapper.querySelector('[data-review-embed-loading]');
    const errorElement = wrapper.querySelector('[data-review-embed-error]');
    const fallbackLink = linkElement?.getAttribute('href') || null;

    const showElement = (element, show = true) => {
      if (!element) {
        return;
      }
      element.classList.toggle('hidden', !show);
    };

    const clearContent = () => {
      if (textElement) {
        textElement.textContent = '';
      }
      if (authorElement) {
        authorElement.textContent = '';
        showElement(authorElement, false);
      }
      if (sourceElement) {
        sourceElement.textContent = '';
        showElement(sourceElement, false);
      }
      if (linkElement) {
        if (fallbackLink) {
          linkElement.setAttribute('href', fallbackLink);
        } else {
          linkElement.removeAttribute('href');
        }
        showElement(linkElement, false);
      }
    };

    const hideStatuses = () => {
      showElement(loadingElement, false);
      showElement(errorElement, false);
      if (errorElement) {
        errorElement.textContent = '';
      }
    };

    const showWrapper = () => {
      wrapper.classList.remove('hidden');
    };

    const hideWrapper = () => {
      wrapper.classList.add('hidden');
      clearContent();
      hideStatuses();
    };

    return {
      showLoading() {
        showWrapper();
        hideStatuses();
        clearContent();
        showElement(loadingElement, true);
      },
      showError(message) {
        showWrapper();
        hideStatuses();
        clearContent();
        if (errorElement) {
          errorElement.textContent = message || '미리보기를 불러오지 못했습니다.';
          showElement(errorElement, true);
        }
      },
      showPreview(preview) {
        if (!preview) {
          hideWrapper();
          return;
        }
        showWrapper();
        hideStatuses();

        if (textElement) {
          textElement.textContent = preview.text || '';
        }

        if (authorElement) {
          if (preview.author_name) {
            authorElement.textContent = `작성자: ${preview.author_name}`;
            showElement(authorElement, true);
          } else {
            showElement(authorElement, false);
          }
        }

        if (sourceElement) {
          const provider = preview.provider_name || 'X';
          sourceElement.textContent = `출처: ${provider}`;
          showElement(sourceElement, true);
        }

        if (linkElement) {
          const linkUrl = preview.url || fallbackLink;
          if (linkUrl) {
            linkElement.setAttribute('href', linkUrl);
            showElement(linkElement, true);
          } else {
            showElement(linkElement, false);
          }
        }
      },
      hide() {
        hideWrapper();
      },
    };
  }

  function setupEmbedPreview(modal, form, contentInput) {
    if (!modal || !form || !contentInput) {
      return;
    }
    if (modal.dataset.reviewEmbedInitialized === '1') {
      return;
    }

    const endpoint = form.dataset.reviewEmbedEndpoint;
    if (!endpoint) {
      return;
    }

    const wrapper = modal.querySelector('[data-review-embed-wrapper]');
    if (!wrapper) {
      return;
    }

    const view = createEmbedView(wrapper);
    if (!view) {
      return;
    }

    modal.dataset.reviewEmbedInitialized = '1';

    const clearButton = wrapper.querySelector('[data-review-embed-clear]');

    let currentUrl = null;
    let debounceTimer = null;
    let abortController = null;

    const resetView = () => {
      if (abortController) {
        abortController.abort();
      }
      abortController = null;
      currentUrl = null;
      view.hide();
    };

    const requestPreview = (url) => {
      if (abortController) {
        abortController.abort();
      }
      abortController = new AbortController();
      const requestedUrl = url;

      view.showLoading();
      fetchEmbedPreview(endpoint, url, { signal: abortController.signal })
        .then((payload) => {
          if (!payload) {
            throw new Error('EMPTY_RESPONSE');
          }
          if (!payload.success) {
            const error = new Error(payload.message || '미리보기를 불러오지 못했습니다.');
            error.userMessage = payload.message;
            throw error;
          }
          if (currentUrl !== requestedUrl) {
            return;
          }
          view.showPreview(payload.preview);
        })
        .catch((error) => {
          if (error && error.name === 'AbortError') {
            return;
          }
          if (currentUrl !== requestedUrl) {
            return;
          }
          const message = (error && error.userMessage) || '미리보기를 불러오지 못했습니다.';
          view.showError(message);
        });
    };

    const handleContentChange = () => {
      const url = extractXPostUrl(contentInput.value);
      if (!url) {
        resetView();
        return;
      }
      if (url === currentUrl) {
        return;
      }
      currentUrl = url;
      requestPreview(url);
    };

    const scheduleContentCheck = () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
      debounceTimer = setTimeout(handleContentChange, EMBED_DEBOUNCE_MS);
    };

    contentInput.addEventListener('input', scheduleContentCheck);
    contentInput.addEventListener('paste', () => {
      setTimeout(scheduleContentCheck, 0);
    });

    if (clearButton) {
      clearButton.addEventListener('click', () => {
        resetView();
      });
    }

    modal.addEventListener('modal:open', () => {
      setTimeout(scheduleContentCheck, 0);
    });

    modal.addEventListener('modal:close', () => {
      resetView();
    });
  }

  function setupReviewListEmbeds(root = document) {
    if (!root) {
      return;
    }

    root.querySelectorAll('[data-review-embed-container]').forEach((container) => {
      if (container.dataset.reviewEmbedInitialized === '1') {
        return;
      }

      const url = normalizeXPostUrl(container.dataset.reviewEmbedUrl || '');
      if (!url) {
        return;
      }

      const endpoint = resolveEmbedEndpoint(container);
      if (!endpoint) {
        return;
      }

      const view = createEmbedView(container);
      if (!view) {
        return;
      }

      container.dataset.reviewEmbedInitialized = '1';
      container.dataset.reviewEmbedUrl = url;

      view.showLoading();
      fetchEmbedPreview(endpoint, url)
        .then((payload) => {
          if (!payload) {
            throw new Error('EMPTY_RESPONSE');
          }
          if (!payload.success) {
            const error = new Error(payload.message || '미리보기를 불러오지 못했습니다.');
            error.userMessage = payload.message;
            throw error;
          }
          view.showPreview(payload.preview);
        })
        .catch((error) => {
          const message = (error && error.userMessage) || '미리보기를 불러오지 못했습니다.';
          view.showError(message);
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

  function formatReviewErrors(errors) {
    if (!errors) {
      return null;
    }

    if (Array.isArray(errors)) {
      return errors
        .map((item) => {
          if (!item) {
            return null;
          }
          if (typeof item === 'string') {
            return item;
          }
          if (typeof item === 'object' && 'message' in item) {
            return item.message;
          }
          return String(item);
        })
        .filter(Boolean)
        .join('\n');
    }

    if (typeof errors === 'object') {
      const messages = [];
      Object.values(errors).forEach((value) => {
        if (!value) {
          return;
        }
        if (Array.isArray(value)) {
          const nested = formatReviewErrors(value);
          if (nested) {
            messages.push(nested);
          }
          return;
        }
        if (typeof value === 'object' && 'message' in value) {
          messages.push(value.message);
          return;
        }
        messages.push(String(value));
      });
      return messages.join('\n');
    }

    return String(errors);
  }

  function setFormError(form, message) {
    const errorElement = form.querySelector('[data-review-error]');
    if (!errorElement) {
      if (message) {
        console.warn('[Reviews] Form error:', message);
      }
      return;
    }

    if (message) {
      errorElement.textContent = message;
      errorElement.classList.remove('hidden');
    } else {
      errorElement.textContent = '';
      errorElement.classList.add('hidden');
    }
  }

  function setupAjaxForms(root = document) {
    root.querySelectorAll('form[data-review-form]').forEach((form) => {
      if (form.dataset.reviewFormAjaxInitialized === '1') {
        return;
      }
      form.dataset.reviewFormAjaxInitialized = '1';

      form.addEventListener('submit', (event) => {
        if (event.defaultPrevented) {
          return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();

        const submitButton =
          form.querySelector('[data-review-submit]') || form.querySelector('button[type="submit"]');
        const modal = form.closest('[data-review-modal]');
        const formType = form.dataset.reviewForm;

        const setLoadingState = (isLoading) => {
          if (typeof form.__reviewsSetLoadingState === 'function') {
            form.__reviewsSetLoadingState(isLoading);
            return;
          }
          if (!submitButton) {
            return;
          }
          if (isLoading) {
            submitButton.disabled = true;
            submitButton.classList.add('cursor-wait');
            submitButton.setAttribute('aria-busy', 'true');
          } else {
            submitButton.disabled = false;
            submitButton.classList.remove('cursor-wait');
            submitButton.removeAttribute('aria-busy');
          }
        };

        const revalidateButtonState = () => {
          if (typeof form.__reviewsToggleSubmitState === 'function') {
            form.__reviewsToggleSubmitState();
          }
        };

        const requestOptions = {
          method: (form.getAttribute('method') || 'post').toUpperCase(),
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: new FormData(form),
          credentials: 'same-origin',
        };

        setFormError(form, null);
        setLoadingState(true);

        fetch(form.getAttribute('action'), requestOptions)
          .then((response) => {
            if (response.status === 403) {
              throw new Error('FORBIDDEN');
            }
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
              return response.json();
            }
            return response.text().then((text) => {
              throw new Error(text || 'UNEXPECTED_RESPONSE');
            });
          })
          .then((data) => {
            if (!data || !data.success) {
              const message = data && (data.message || formatReviewErrors(data.errors));
              setFormError(form, message || '요청을 처리하지 못했습니다.');
              throw new Error('VALIDATION');
            }

            const reviewsUrl = data.reviews_url || data.anchor || data.url || window.location.href;
            if (modal) {
              closeModal(modal);
            }

            const reviewsContent = document.getElementById('reviewsContent');
            let updatePromise;

            if (data.html && reviewsContent) {
              reviewsContent.innerHTML = data.html;
              setupReviewComponents(reviewsContent);
              if (data.page) {
                updateReviewCurrentPage(data.page);
              }
              if (data.anchor || data.url) {
                const historyUrl = data.anchor || data.url;
                window.history.pushState({ reviewsUrl: historyUrl }, '', historyUrl);
              }
              updatePromise = Promise.resolve({ page: data.page });
            } else {
              updatePromise = loadReviews(reviewsUrl, true);
            }

            return updatePromise.then((payload) => {
              setFormError(form, null);
              if (formType === 'create') {
                form.reset();
                updateReviewCurrentPage((payload && payload.page) || data.page || 1);
              }
              return data;
            });
          })
          .catch((error) => {
            if (error.message === 'VALIDATION') {
              return;
            }
            if (error.message === 'FORBIDDEN') {
              setFormError(form, '권한이 없습니다.');
              return;
            }
            console.error('[Reviews] 요청 처리 중 오류', error);
            window.location.href = form.getAttribute('action');
          })
          .finally(() => {
            setLoadingState(false);
            revalidateButtonState();
          });
      });
    });
  }

  function updateReviewCurrentPage(page) {
    if (!page) {
      return;
    }
    document.querySelectorAll('[data-review-current-page]').forEach((input) => {
      if (input instanceof HTMLInputElement) {
        input.value = String(page);
      }
    });
  }

  function loadReviews(url, pushHistory = true) {
    const reviewsContent = document.getElementById('reviewsContent');
    if (!reviewsContent) {
      return Promise.resolve(null);
    }

    const [fetchUrl] = url.split('#');
    const baseUrl = window.location.href;
    const requestUrl = new URL(fetchUrl, baseUrl);
    requestUrl.searchParams.set('fragment', 'reviews');

    reviewsContent.classList.add('opacity-50', 'pointer-events-none');

    return fetch(requestUrl.toString(), {
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          return response.json();
        }
        return response.text().then((text) => {
          throw new Error(`Unexpected response: ${text.slice(0, 100)}`);
        });
      })
      .then((payload) => {
        if (!payload || typeof payload.html !== 'string') {
          throw new Error('Invalid review fragment payload');
        }
        reviewsContent.innerHTML = payload.html;
        updateReviewCurrentPage(payload.page);
        setupReviewComponents(reviewsContent);

        const historyUrl = payload.anchor || payload.url || fetchUrl;
        if (pushHistory && historyUrl) {
          window.history.pushState({ reviewsUrl: historyUrl }, '', historyUrl);
        }

        if (pushHistory) {
          const reviewsSection = document.getElementById('reviews');
          if (reviewsSection) {
            reviewsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }

        return payload;
      })
      .catch((error) => {
        console.error('[Reviews] Failed to load review page', error);
        window.location.href = url;
        throw error;
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
      if (submitButton.textContent && !submitButton.dataset.reviewSubmitOriginal) {
        submitButton.dataset.reviewSubmitOriginal = submitButton.textContent.trim();
      }

      const form = submitButton.closest('form');

      const setLoadingState = (isLoading) => {
        if (isLoading) {
          submitButton.textContent = '저장 중...';
          submitButton.disabled = true;
          submitButton.classList.add('cursor-wait');
          submitButton.setAttribute('aria-busy', 'true');
        } else {
          if (submitButton.dataset.reviewSubmitOriginal) {
            submitButton.textContent = submitButton.dataset.reviewSubmitOriginal;
          }
          submitButton.classList.remove('cursor-wait');
          submitButton.removeAttribute('aria-busy');
          toggleButtonState();
        }
      };

      const toggleButtonState = () => {
        const ratingValue = Number(ratingInput?.value || 0);
        const contentValue = (contentInput?.value || '').trim();
        const isValid = ratingValue > 0 && contentValue.length > 0;
        if (!submitButton.classList.contains('cursor-wait')) {
          submitButton.disabled = !isValid;
        }
      };

      if (form) {
        form.__reviewsSetLoadingState = setLoadingState;
        form.__reviewsToggleSubmitState = toggleButtonState;
      }

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

      if (modal && form && contentInput) {
        setupEmbedPreview(modal, form, contentInput);
      }

      if (form && form.dataset.reviewSubmitLoadingInitialized !== '1') {
        form.dataset.reviewSubmitLoadingInitialized = '1';
        form.addEventListener('submit', () => {
          setLoadingState(true);
        });
      }

      modal.addEventListener('modal:open', () => {
        setLoadingState(false);
        toggleButtonState();
      });
      modal.addEventListener('modal:close', () => {
        setLoadingState(false);
        toggleButtonState();
      });
      toggleButtonState();
    });
  }

  function setupReviewComponents(root = document) {
    initModals(root);
    initRatingControls(root);
    initDropzones(root);
    setupDeleteConfirm(root);
    setupAjaxForms(root);
    setupSubmitState(root);
    setupReviewListEmbeds(root);
    setupPagination();
  }

  window.initReviewsUI = () => setupReviewComponents(document);

  document.addEventListener('DOMContentLoaded', () => {
    setupReviewComponents(document);
    initHistory();
  });
})();
