(function () {
  const form = document.querySelector('[data-integrity-form]');
  const fileInput = form ? form.querySelector('input[type="file"]') : null;
  const fileNameTarget = form ? form.querySelector('[data-file-name]') : null;

  if (fileInput && fileNameTarget) {
    fileInput.addEventListener('change', () => {
      const file = fileInput.files && fileInput.files[0];
      fileNameTarget.textContent = file ? file.name : '선택된 파일이 없습니다';
    });
  }
})();
