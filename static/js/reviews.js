(function () {
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

  document.addEventListener('DOMContentLoaded', () => {
    ['createReviewModal', 'editReviewModal'].forEach((modalId) => {
      setupModal(modalId);
    });

    ['createReviewModal', 'editReviewModal'].forEach((modalId) => {
      const modal = document.getElementById(modalId);
      if (!modal) {
        return;
      }
      setupRatingControls(modal);
      setupDropzones(modal);
    });
  });

  function setupModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) {
      return;
    }

    const openButtons = document.querySelectorAll(`[data-open-modal="${modalId}"]`);
    const closeButtons = modal.querySelectorAll('[data-close-modal]');

    const openModal = () => {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
      document.body.classList.add('overflow-hidden');
      modal.dispatchEvent(new CustomEvent('modal:open'));
    };

    const closeModal = () => {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      document.body.classList.remove('overflow-hidden');
      modal.dispatchEvent(new CustomEvent('modal:close'));
    };

    openButtons.forEach((button) => {
      button.addEventListener('click', openModal);
    });

    closeButtons.forEach((button) => {
      button.addEventListener('click', closeModal);
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        closeModal();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal();
      }
    });
  }

  function setupRatingControls(modal) {
    modal.querySelectorAll('[data-rating-control]').forEach((control) => {
      const input = control.querySelector('input[name="rating"]');
      if (!input) {
        return;
      }

      const defaultValue = Number(input.dataset.default || input.value || 0);
      const dots = Array.from(control.querySelectorAll('[data-score]'));
      const previewLabel = control.querySelector('[data-rating-preview]');

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
        dot.addEventListener('mouseenter', () => {
          updateDots(dotValue);
        });
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

      modal.addEventListener('modal:open', () => {
        const currentValue = Number(input.value || defaultValue || 0);
        setRating(currentValue);
      });

      modal.addEventListener('modal:close', () => {
        const currentValue = Number(input.value || defaultValue || 0);
        setRating(currentValue);
      });

      setRating(defaultValue);
    });
  }

  function setupDropzones(modal) {
    modal.querySelectorAll('[data-review-dropzone]').forEach((zone) => {
      const inputId = zone.dataset.targetInput;
      const previewId = zone.dataset.previewContainer;
      const maxFiles = Number(zone.dataset.maxFiles || 5);
      const existingCount = Number(zone.dataset.existingCount || 0);

      const input = document.getElementById(inputId);
      const preview = previewId ? document.getElementById(previewId) : null;
      const remainingElement = zone.querySelector('[data-dropzone-remaining]');

      if (!input) {
        return;
      }

      let selectedFiles = [];
      const previewUrlMap = new Map();

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
      };

      const addFile = (file) => {
        if (existingCount + selectedFiles.length >= maxFiles) {
          alert(`이미지는 최대 ${maxFiles}개까지 업로드할 수 있습니다.`);
          return;
        }
        if (!file.type.startsWith('image/')) {
          alert('이미지 파일만 업로드할 수 있습니다.');
          return;
        }
        if (file.size > MAX_FILE_SIZE) {
          const size = (file.size / 1024 / 1024).toFixed(2);
          alert(`\"${file.name}\" 파일이 10MB를 초과합니다. (${size}MB)`);
          return;
        }
        selectedFiles.push(file);
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
          alert(`이미지는 최대 ${maxFiles}개까지 업로드할 수 있습니다.`);
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
      });

      modal.addEventListener('modal:close', reset);
      updateRemaining();
    });
  }
})();
