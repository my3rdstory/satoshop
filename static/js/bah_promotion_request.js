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
    const deleteCheckboxes = document.querySelectorAll('input[name="delete_images"]');
    const addressModal = document.getElementById('addressSearchModal');
    const addressContainer = document.getElementById('addressSearchContainer');
    const closeAddressModalBtn = document.getElementById('closeAddressModal');
    const addressTriggers = document.querySelectorAll('[data-address-trigger]');

    const maxImageCount = parseInt(maxImages, 10) || 4;
    const initialExisting = parseInt(existingCount, 10) || 0;
    const userCanSubmit = userHasLightning === 'true';

    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    const MAX_SIZE_MB = 5;

    let postcodeInstance = null;

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
    }

    function getDeleteCount() {
      return Array.from(deleteCheckboxes).filter(cb => cb.checked).length;
    }

    function getSelectedFileCount() {
      return fileInput && fileInput.files ? fileInput.files.length : 0;
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
      const hasImages = getSelectedFileCount() + effectiveExisting > 0;
      const slotsOk = !remainingInfo || !remainingInfo.classList.contains('text-red-500');

      const canSave = allFilled && consentGiven && hasImages && slotsOk;
      saveButton.disabled = !canSave;
    }

    function addFilesToInput(files) {
      if (!fileInput || !files || !files.length) {
        return;
      }

      const deleteCount = getDeleteCount();
      const effectiveExisting = Math.max(initialExisting - deleteCount, 0);
      const dataTransfer = new DataTransfer();

      Array.from(fileInput.files || []).forEach(file => {
        dataTransfer.items.add(file);
      });

      for (const file of files) {
        if (!ALLOWED_TYPES.includes(file.type)) {
          window.alert('지원하지 않는 파일 형식입니다. JPEG/PNG/WEBP/GIF만 업로드할 수 있습니다.');
          continue;
        }
        if (file.size > MAX_SIZE_MB * 1024 * 1024) {
          window.alert(`이미지 크기가 ${MAX_SIZE_MB}MB를 초과했습니다.`);
          continue;
        }
        dataTransfer.items.add(file);
      }

      if (effectiveExisting + dataTransfer.items.length > maxImageCount) {
        window.alert(`이미지는 최대 ${maxImageCount}장까지 업로드할 수 있습니다.`);
        return;
      }

      fileInput.files = dataTransfer.files;
      updateImageSlotInfo();
    }

    function handleDrop(event) {
      event.preventDefault();
      event.stopPropagation();
      const files = event.dataTransfer?.files;
      if (files && files.length) {
        addFilesToInput(files);
      }
      dropzone.classList.remove('border-bitcoin', 'bg-bitcoin/10');
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
      if (!addressModal.classList.contains('hidden')) {
        return;
      }
      if (!window.daum || !window.daum.Postcode) {
        console.warn('Daum Postcode script is not loaded.');
        return;
      }

      addressModal.classList.remove('hidden');
      addressModal.classList.add('flex');
      addressContainer.innerHTML = '';

      postcodeInstance = new window.daum.Postcode({
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
          closeAddressModal();
          validateFormCompleteness();
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
      }, 200);
    }

    if (startButton) {
      startButton.addEventListener('click', revealFormSection);
    }

    if (showForm === 'true') {
      revealFormSection();
    }

    if (status === 'created' || status === 'updated') {
      showCompletionSection(status);
    }

    if (fileInput) {
      fileInput.addEventListener('change', updateImageSlotInfo);
    }

    if (browseButton && fileInput) {
      browseButton.addEventListener('click', function() {
        fileInput.click();
      });
    }

    if (dropzone) {
      dropzone.addEventListener('dragenter', handleDrag);
      dropzone.addEventListener('dragover', handleDrag);
      dropzone.addEventListener('dragleave', handleDrag);
      dropzone.addEventListener('drop', handleDrop);
      dropzone.addEventListener('click', function() {
        if (fileInput) {
          fileInput.click();
        }
      });
    }

    deleteCheckboxes.forEach(function(cb) {
      cb.addEventListener('change', updateImageSlotInfo);
    });

    if (addressTriggers) {
      addressTriggers.forEach(function(trigger) {
        ['click', 'focus'].forEach(function(evt) {
          trigger.addEventListener(evt, function() {
            openAddressModal();
          });
        });
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
  });
})();
