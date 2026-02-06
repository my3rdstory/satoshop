(function() {
  document.addEventListener('DOMContentLoaded', function() {
    const app = document.getElementById('bahPromotionApp');
    if (!app) {
      return;
    }

    const {
      status = '',
      showForm = 'false',
      userHasLightning = 'false',
      maxImages = '4',
      existingCount = '0',
      requiresLightningLogout = 'false',
      logoutUrl = '',
      logoutNext = '',
    } = app.dataset;

    const introSection = document.getElementById('requestIntroSection');
    const formSection = document.getElementById('requestFormSection');
    const completeSection = document.getElementById('requestCompleteSection');
    const completionTitle = document.getElementById('completionTitle');
    const startButton = document.getElementById('startRequestButton');
    const saveButton = document.getElementById('saveRequestButton');
    const fileInput = document.getElementById('id_images');
    const browseButton = document.getElementById('browseImagesButton');
    const dropzone = document.getElementById('imageDropzone');
    const remainingInfo = document.getElementById('imageSlotInfo');
    const remainingValue = document.getElementById('remainingImageCount');
    const consentCheckbox = document.getElementById('id_accept_privacy');
    const previewWrapper = document.getElementById('imagePreviewWrapper');
    const previewContainer = document.getElementById('imagePreviewList');
    const formElement = formSection ? formSection.querySelector('form') : null;
    const deleteCheckboxes = document.querySelectorAll('input[name="delete_images"]');
    const addressModal = document.getElementById('addressSearchModal');
    const addressContainer = document.getElementById('addressSearchContainer');
    const closeAddressModalBtn = document.getElementById('closeAddressModal');
    const addressTriggers = document.querySelectorAll('[data-address-trigger]');
    const dataTransferSupported = typeof DataTransfer !== 'undefined';
    let lastDataTransferError = null;
    let postcodeInstance = null;

    const maxImageCount = parseInt(maxImages, 10) || 4;
    const initialExisting = parseInt(existingCount, 10) || 0;
    const userCanSubmit = userHasLightning === 'true';

    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    const MAX_SIZE_MB = 5;


    function tryCreateDataTransfer() {
      if (!dataTransferSupported) {
        return null;
      }
      try {
        return new DataTransfer();
      } catch (error) {
        lastDataTransferError = error;
        logProgress('data_transfer_unsupported', {
          message: error && error.message ? error.message : String(error),
        });
        return null;
      }
    }

    function normalizeFiles(fileLike) {
      if (!fileLike) {
        return [];
      }
      if (Array.isArray(fileLike)) {
        return fileLike.filter(Boolean);
      }
      if (typeof fileLike.length === 'number') {
        return Array.from(fileLike).filter(Boolean);
      }
      return [];
    }

    function extractDroppedFiles(dataTransfer) {
      if (!dataTransfer) {
        return [];
      }

      const directFiles = normalizeFiles(dataTransfer.files);
      if (directFiles.length) {
        return directFiles;
      }

      if (dataTransfer.items && typeof dataTransfer.items.length === 'number') {
        const filesFromItems = [];
        Array.from(dataTransfer.items).forEach(function(item) {
          if (!item) {
            return;
          }
          if (item.kind === 'file') {
            const file = typeof item.getAsFile === 'function' ? item.getAsFile() : null;
            if (file) {
              filesFromItems.push(file);
            }
          }
        });
        if (filesFromItems.length) {
          return filesFromItems;
        }
      }

      return [];
    }

    function logProgress() {}

    logProgress('init', {
      status,
      showForm,
      existingImageCount: initialExisting,
      maxImageCount,
      DataTransferSupported: dataTransferSupported,
      userCanSubmit,
    });

    function getCsrfToken() {
      if (window.getCsrfToken) {
        return window.getCsrfToken();
      }
      const token = document.querySelector('[name=csrfmiddlewaretoken]');
      return token ? token.value : null;
    }

    function logoutAndRedirect(nextUrl) {
      const csrfToken = getCsrfToken();
      if (!logoutUrl) {
        window.location.href = nextUrl || '/';
        return;
      }

      if (!csrfToken) {
        window.location.href = `${logoutUrl}?next=${encodeURIComponent(nextUrl || '/')}`;
        return;
      }

      const form = document.createElement('form');
      form.method = 'POST';
      form.action = logoutUrl;

      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = csrfToken;
      form.appendChild(csrfInput);

      const nextInput = document.createElement('input');
      nextInput.type = 'hidden';
      nextInput.name = 'next';
      nextInput.value = nextUrl || '/';
      form.appendChild(nextInput);

      document.body.appendChild(form);
      form.submit();
    }

    function revealFormSection() {
      if (!formSection) {
        return;
      }
      formSection.classList.remove('hidden');
      logProgress('reveal_form');
      if (introSection) {
        introSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    function showCompletionSection(kind) {
      if (!completeSection) {
        return;
      }
      if (completionTitle) {
        completionTitle.textContent = kind === 'updated' ? '홍보 요청이 수정되었습니다' : '홍보 요청이 저장되었습니다';
      }
      completeSection.classList.remove('hidden');
      logProgress('show_completion', { status: kind });
    }

    function getDeleteCount() {
      const count = Array.from(deleteCheckboxes).filter(cb => cb.checked).length;
      return count;
    }

    function getSelectedFileCount() {
      return fileInput && fileInput.files ? fileInput.files.length : 0;
    }

    function formatFileSize(bytes) {
      if (typeof bytes !== 'number' || Number.isNaN(bytes) || bytes <= 0) {
        return '';
      }
      const units = ['B', 'KB', 'MB', 'GB'];
      let size = bytes;
      let unitIndex = 0;
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
      }
      return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    }

    function removeSelectedFile(index) {
      if (!fileInput || !fileInput.files) {
        return;
      }

      if (!dataTransferSupported) {
        fileInput.value = '';
        updateImageSlotInfo();
        logProgress('remove_file_reset', { index });
        return;
      }

      const dataTransfer = tryCreateDataTransfer();
      if (!dataTransfer) {
        fileInput.value = '';
        updateImageSlotInfo();
        logProgress('remove_file_reset_fallback', { index });
        return;
      }
      Array.from(fileInput.files).forEach((file, fileIndex) => {
        if (fileIndex !== index) {
          dataTransfer.items.add(file);
        }
      });

      fileInput.files = dataTransfer.files;
      updateImageSlotInfo();
      logProgress('remove_file', { index, remaining: fileInput.files.length });
    }

    function renderImagePreviews() {
      if (!previewContainer || !previewWrapper || !fileInput || !window.FileReader) {
        return;
      }

      previewContainer.innerHTML = '';

      const files = Array.from(fileInput.files || []);
      if (!files.length) {
        previewWrapper.classList.add('hidden');
        return;
      }

      previewWrapper.classList.remove('hidden');

      files.forEach((file, index) => {
        const card = document.createElement('div');
        card.className = 'relative overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm transition-all';

        const imageEl = document.createElement('img');
        imageEl.alt = file.name;
        imageEl.className = 'w-full h-36 object-cover bg-gray-100 dark:bg-gray-800';
        card.appendChild(imageEl);

        const meta = document.createElement('div');
        meta.className = 'absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 px-3 py-2 bg-gray-900/70 dark:bg-gray-950/70 text-white text-xs';
        const nameSpan = document.createElement('span');
        nameSpan.className = 'truncate';
        nameSpan.textContent = file.name;
        const sizeSpan = document.createElement('span');
        sizeSpan.className = 'shrink-0 text-xs uppercase';
        sizeSpan.textContent = formatFileSize(file.size);
        meta.appendChild(nameSpan);
        if (sizeSpan.textContent) {
          meta.appendChild(sizeSpan);
        }
        card.appendChild(meta);

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'absolute top-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-gray-900/70 text-white hover:bg-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-bitcoin focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-gray-900';
        removeButton.setAttribute('aria-label', '선택한 이미지를 제거합니다');
        removeButton.innerHTML = '<i class="fas fa-times"></i>';
        removeButton.addEventListener('click', function() {
          removeSelectedFile(index);
        });
        card.appendChild(removeButton);

        const reader = new FileReader();
        reader.onload = function(event) {
          if (event.target && typeof event.target.result === 'string') {
            imageEl.src = event.target.result;
          }
        };
        reader.readAsDataURL(file);

        previewContainer.appendChild(card);
        logProgress('preview_ready', {
          index,
          name: file.name,
          size: file.size,
          type: file.type,
        });
      });
    }

    function updateImageSlotInfo() {
      if (!remainingValue || !remainingInfo) {
        return;
      }

      const deleteCount = getDeleteCount();
      const selectedFiles = getSelectedFileCount();
      const effectiveExisting = Math.max(initialExisting - deleteCount, 0);
      const remaining = maxImageCount - effectiveExisting - selectedFiles;
      remainingValue.textContent = remaining < 0 ? '0' : String(remaining);

      if (remaining < 0) {
        remainingInfo.classList.remove('text-gray-500', 'dark:text-gray-400');
        remainingInfo.classList.add('text-red-500');
      } else {
        remainingInfo.classList.add('text-gray-500', 'dark:text-gray-400');
        remainingInfo.classList.remove('text-red-500');
      }

      validateFormCompleteness();
      renderImagePreviews();
      logProgress('slot_update', {
        selectedFiles,
        deleteCount,
        effectiveExisting,
        remaining,
      });
    }

    function validateFormCompleteness() {
      if (!saveButton) {
        return;
      }

      const requiredIds = [
        'id_store_name',
        'id_postal_code',
        'id_address',
        'id_address_detail',
        'id_phone_number',
        'id_email',
        'id_introduction',
      ];

      const allFilled = requiredIds.every(id => {
        const input = document.getElementById(id);
        if (!input) {
          return false;
        }
        return input.value && input.value.trim().length > 0;
      });

      const consentGiven = consentCheckbox ? consentCheckbox.checked : true;
      const deleteCount = getDeleteCount();
      const effectiveExisting = Math.max(initialExisting - deleteCount, 0);
      const slotsOk = !remainingInfo || !remainingInfo.classList.contains('text-red-500');

      const canSave = allFilled && consentGiven && slotsOk;
      saveButton.disabled = !canSave;
      logProgress('validation', {
        canSave,
        allFilled,
        consentGiven,
        selectedFiles: getSelectedFileCount(),
        slotsOk,
      });
    }

    function addFilesToInput(rawFiles) {
      const files = normalizeFiles(rawFiles);
      if (!fileInput || !files || !files.length) {
        return;
      }

      const deleteCount = getDeleteCount();
      const effectiveExisting = Math.max(initialExisting - deleteCount, 0);
      const dataTransfer = tryCreateDataTransfer();

      if (!dataTransfer) {
        const maxAllowed = Math.max(maxImageCount - effectiveExisting, 0);
        if (files.length > maxAllowed) {
          window.alert(`이미지는 최대 ${maxImageCount}장까지 업로드할 수 있습니다.`);
          logProgress('file_rejected_limit_fallback', {
            effectiveExisting,
            attempted: files.length,
            maxImageCount,
            fallback: true,
          });
          return;
        }

        for (const file of files) {
          if (!ALLOWED_TYPES.includes(file.type)) {
            window.alert('지원하지 않는 파일 형식입니다. JPEG/PNG/WEBP/GIF만 업로드할 수 있습니다.');
            logProgress('file_rejected_type_fallback', { name: file.name, type: file.type });
            return;
          }
          if (file.size > MAX_SIZE_MB * 1024 * 1024) {
            window.alert(`이미지 크기가 ${MAX_SIZE_MB}MB를 초과했습니다.`);
            logProgress('file_rejected_size_fallback', { name: file.name, size: file.size });
            return;
          }
        }

        if (getSelectedFileCount() > 0) {
          window.alert('브라우저 제한으로 드래그한 이미지를 기존 선택과 합칠 수 없습니다. 다시 선택 버튼을 사용해주세요.');
          logProgress('file_add_failed_merge', {
            currentSelected: getSelectedFileCount(),
            incoming: files.length,
            fallback: true,
          });
          return;
        }

        try {
          fileInput.files = files;
          updateImageSlotInfo();
          logProgress('file_added_direct', {
            addedCount: files.length,
            totalSelected: getSelectedFileCount(),
            fallback: true,
            lastDataTransferError: lastDataTransferError ? lastDataTransferError.message : null,
          });
        } catch (error) {
          logProgress('file_add_failed', {
            message: error && error.message ? error.message : String(error),
            fallback: true,
          });
          window.alert('브라우저가 드래그 앤 드롭 업로드를 완전히 지원하지 않습니다. "이미지 선택하기" 버튼을 사용해주세요.');
        }
        return;
      }

      Array.from(fileInput.files || []).forEach(file => {
        dataTransfer.items.add(file);
      });

      for (const file of files) {
        if (!ALLOWED_TYPES.includes(file.type)) {
          window.alert('지원하지 않는 파일 형식입니다. JPEG/PNG/WEBP/GIF만 업로드할 수 있습니다.');
          logProgress('file_rejected_type', { name: file.name, type: file.type });
          continue;
        }
        if (file.size > MAX_SIZE_MB * 1024 * 1024) {
          window.alert(`이미지 크기가 ${MAX_SIZE_MB}MB를 초과했습니다.`);
          logProgress('file_rejected_size', { name: file.name, size: file.size });
          continue;
        }
        dataTransfer.items.add(file);
      }

      if (effectiveExisting + dataTransfer.items.length > maxImageCount) {
        window.alert(`이미지는 최대 ${maxImageCount}장까지 업로드할 수 있습니다.`);
        logProgress('file_rejected_limit', {
          effectiveExisting,
          attempted: dataTransfer.items.length,
          maxImageCount,
        });
        return;
      }

      fileInput.files = dataTransfer.files;
      updateImageSlotInfo();
      logProgress('file_added', {
        addedCount: files.length,
        totalSelected: fileInput.files.length,
      });
    }

    function handleDrop(event) {
      event.preventDefault();
      event.stopPropagation();
      const droppedFiles = extractDroppedFiles(event.dataTransfer);
      if (droppedFiles.length) {
        addFilesToInput(droppedFiles);
        logProgress('drop', { dropped: droppedFiles.length });
      } else {
        logProgress('drop_no_files', {
          hasDataTransfer: Boolean(event.dataTransfer),
          itemCount: event.dataTransfer && event.dataTransfer.items ? event.dataTransfer.items.length : null,
        });
      }
      dropzone.classList.remove('border-bitcoin', 'bg-bitcoin/10');
    }

    function handlePaste(event) {
      if (!event.clipboardData) {
        return;
      }
      const pastedFiles = extractDroppedFiles(event.clipboardData);
      if (pastedFiles.length) {
        addFilesToInput(pastedFiles);
        logProgress('paste', { pasted: pastedFiles.length });
        event.preventDefault();
      }
    }

    function handleFileInputChange() {
      logProgress('input_change', { totalSelected: getSelectedFileCount() });
      updateImageSlotInfo();
    }

    function handleBrowseClick() {
      if (fileInput) {
        fileInput.click();
      }
      logProgress('dropzone_click');
    }

    function handleCheckboxChange(cb) {
      updateImageSlotInfo();
      logProgress('existing_image_toggle', {
        imageId: cb.value,
        checked: cb.checked,
      });
    }

    function handleAddressTrigger(event) {
      if (event) {
        event.preventDefault();
      }
      openAddressModal();
    }

    function handleFormSubmit() {
      if (saveButton) {
        saveButton.disabled = true;
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>저장 중...';
      }
      if (formElement && window.FormData) {
        try {
          const formData = new FormData(formElement);
          const imageEntries = [];
          formData.forEach(function(value, key) {
            if (key.startsWith('images')) {
              if (value && typeof value === 'object' && 'name' in value) {
                imageEntries.push({ key, name: value.name, size: value.size, type: value.type });
              } else {
                imageEntries.push({ key, value: String(value) });
              }
            }
          });
          logProgress('formdata_snapshot', { images: imageEntries, fieldCount: imageEntries.length });
        } catch (error) {
          logProgress('formdata_error', { message: error && error.message ? error.message : String(error) });
        }
      }
    }

    function handleStartButtonClick() {
      revealFormSection();
    }

    function handleSaveButtonClick(event) {
      if (saveButton && !saveButton.disabled) {
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>저장 중...';
      }
    }

    function attachDragEvents() {
      if (!dropzone) {
        return;
      }
      dropzone.addEventListener('dragenter', handleDrag);
      dropzone.addEventListener('dragover', handleDrag);
      dropzone.addEventListener('dragleave', handleDrag);
      dropzone.addEventListener('drop', handleDrop);
      dropzone.addEventListener('click', handleBrowseClick);
      dropzone.addEventListener('paste', handlePaste);
    }

    function attachCheckboxEvents() {
      deleteCheckboxes.forEach(function(cb) {
        cb.addEventListener('change', function() {
          handleCheckboxChange(cb);
        });
      });
    }

    function attachAddressEvents() {
      if (addressTriggers) {
        addressTriggers.forEach(function(trigger) {
          trigger.addEventListener('click', handleAddressTrigger);
        });
      }

      if (closeAddressModalBtn) {
        closeAddressModalBtn.addEventListener('click', closeAddressModal);
      }

      if (addressModal) {
        addressModal.addEventListener('click', function(event) {
          if (event.target === addressModal) {
            closeAddressModal();
          }
        });
      }
    }

    function handleDrag(event) {
      event.preventDefault();
      event.stopPropagation();
      if (event.type === 'dragover' || event.type === 'dragenter') {
        dropzone.classList.add('border-bitcoin', 'bg-bitcoin/10');
      } else {
        dropzone.classList.remove('border-bitcoin', 'bg-bitcoin/10');
      }
    }

    function openAddressModal() {
      if (!addressModal || !addressContainer) {
        return;
      }
      if (addressModal.classList.contains('flex')) {
        return;
      }
      if (!window.kakao || !window.kakao.Postcode) {
        console.warn('Kakao Postcode script is not loaded.');
        return;
      }

      addressModal.classList.remove('hidden');
      addressModal.classList.add('flex');
      addressContainer.innerHTML = '';

      postcodeInstance = new window.kakao.Postcode({
        oncomplete: function(data) {
          var addr = data.userSelectedType === 'R' ? data.roadAddress : data.jibunAddress;
          if (data.userSelectedType === 'R') {
            var extra = '';
            if (data.bname !== '' && /[동|로|가]$/g.test(data.bname)) {
              extra += data.bname;
            }
            if (data.buildingName !== '' && data.apartment === 'Y') {
              extra += (extra !== '' ? ', ' + data.buildingName : data.buildingName);
            }
            if (extra !== '') {
              addr += ' (' + extra + ')';
            }
          }

          var postalField = document.getElementById('id_postal_code');
          var addressField = document.getElementById('id_address');
          var detailField = document.getElementById('id_address_detail');
          if (postalField) {
            postalField.value = data.zonecode;
          }
          if (addressField) {
            addressField.value = addr;
          }
          if (detailField) {
            detailField.focus();
          }
          validateFormCompleteness();
          closeAddressModal();
        },
        onclose: function() {
          closeAddressModal();
        },
      });

      postcodeInstance.embed(addressContainer);
    }

    function closeAddressModal() {
      if (!addressModal || !addressContainer) {
        return;
      }
      addressModal.classList.add('hidden');
      addressModal.classList.remove('flex');
      setTimeout(function() {
        addressContainer.innerHTML = '';
        postcodeInstance = null;
      }, 150);
    }
    const requiredIds = [
      'id_store_name',
      'id_postal_code',
      'id_address',
      'id_address_detail',
      'id_phone_number',
      'id_email',
      'id_introduction',
    ];
    requiredIds.forEach(function(id) {
      const input = document.getElementById(id);
      if (input) {
        input.addEventListener('input', validateFormCompleteness);
        input.addEventListener('blur', validateFormCompleteness);
      }
    });

    if (consentCheckbox) {
      consentCheckbox.addEventListener('change', validateFormCompleteness);
    }

    updateImageSlotInfo();
    logProgress('ready_for_input');

    if (!userCanSubmit && startButton) {
      startButton.disabled = true;
    }

    if (requiresLightningLogout === 'true') {
      setTimeout(function() {
        const message = '홍보요청은 라이트닝 로그인으로만 가능합니다. 현재 계정을 로그아웃하고 라이트닝 로그인 화면으로 이동할까요?';
        if (window.confirm(message)) {
          logoutAndRedirect(logoutNext || window.location.pathname);
        }
      }, 200);
    }

    if (formElement) {
      formElement.addEventListener('submit', handleFormSubmit);
    }

    if (saveButton) {
      saveButton.addEventListener('click', handleSaveButtonClick);
    }

    if (startButton) {
      startButton.addEventListener('click', handleStartButtonClick);
    }

    if (showForm === 'true') {
      revealFormSection();
    }

    if (status === 'created' || status === 'updated') {
      showCompletionSection(status);
    }

    if (fileInput) {
      fileInput.addEventListener('change', handleFileInputChange);
      fileInput.addEventListener('paste', handlePaste);
    }

    if (browseButton) {
      browseButton.addEventListener('click', handleBrowseClick);
    }

    attachDragEvents();
    attachCheckboxEvents();
    attachAddressEvents();
  });
})();
