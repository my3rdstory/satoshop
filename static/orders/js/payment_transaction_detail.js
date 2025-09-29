document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-copy-target]').forEach((button) => {
    const targetSelector = button.getAttribute('data-copy-target');
    if (!targetSelector) {
      return;
    }
    button.addEventListener('click', async () => {
      const target = document.querySelector(targetSelector);
      if (!target) {
        return;
      }
      try {
        await navigator.clipboard.writeText(target.textContent.trim());
        button.classList.add('is-copied');
        const originalLabel = button.getAttribute('data-label');
        if (!button.dataset.activeLabel) {
          button.dataset.activeLabel = originalLabel || button.textContent.trim();
        }
        button.textContent = '복사 완료';
        setTimeout(() => {
          button.textContent = button.dataset.activeLabel;
          button.classList.remove('is-copied');
        }, 1600);
      } catch (error) {
        button.classList.add('is-error');
        button.textContent = '복사 실패';
        setTimeout(() => {
          button.textContent = button.dataset.activeLabel || '복사';
          button.classList.remove('is-error');
        }, 1600);
      }
    });
  });
});
