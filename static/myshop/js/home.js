(function () {
  function toggleItem(item, expand) {
    const content = item.querySelector('.faq-content');
    if (!content) {
      return;
    }

    if (expand) {
      item.classList.add('is-open');
      item.setAttribute('aria-expanded', 'true');
      content.style.maxHeight = content.scrollHeight + 'px';
    } else {
      item.classList.remove('is-open');
      item.setAttribute('aria-expanded', 'false');
      content.style.maxHeight = '0px';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const faqContainer = document.querySelector('[data-faq]');
    if (!faqContainer) {
      return;
    }

    const faqItems = Array.from(faqContainer.querySelectorAll('.faq-item'));
    faqItems.forEach(function (item) {
      const trigger = item.querySelector('.faq-trigger');
      const content = item.querySelector('.faq-content');
      if (!trigger || !content) {
        return;
      }

      // 초기 높이 설정
      toggleItem(item, false);

      trigger.addEventListener('click', function () {
        const willOpen = !item.classList.contains('is-open');
        if (willOpen) {
          faqItems.forEach(function (other) {
            if (other !== item) {
              toggleItem(other, false);
            }
          });
        }
        toggleItem(item, willOpen);
      });
    });
  });
})();
