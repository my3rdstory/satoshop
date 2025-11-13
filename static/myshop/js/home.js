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

  function initFaqSection() {
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
  }

  function initHeroCarousel() {
    const carousel = document.querySelector('[data-hero-carousel]');
    if (!carousel) {
      return;
    }

    const slides = Array.from(carousel.querySelectorAll('[data-hero-slide]'));
    if (!slides.length) {
      return;
    }

    let activeIndex = Math.max(
      0,
      slides.findIndex(function (slide) {
        return slide.classList.contains('is-active');
      })
    );
    let timerId = null;

    const prevButton = carousel.querySelector('[data-carousel-prev]');
    const nextButton = carousel.querySelector('[data-carousel-next]');
    const indicators = Array.from(carousel.querySelectorAll('[data-carousel-indicator]'));

    function getDuration(index) {
      const duration = Number(slides[index].dataset.duration || '6');
      return Math.max(duration, 3) * 1000;
    }

    function activate(index) {
      slides.forEach(function (slide, slideIndex) {
        slide.classList.toggle('is-active', slideIndex === index);
      });
      indicators.forEach(function (indicator) {
        const targetIndex = Number(indicator.dataset.carouselIndicator || 0);
        indicator.classList.toggle('is-active', targetIndex === index);
      });
      activeIndex = index;
    }

    function scheduleNext() {
      clearTimeout(timerId);
      if (slides.length <= 1) {
        return;
      }
      timerId = setTimeout(function () {
        goTo((activeIndex + 1) % slides.length);
      }, getDuration(activeIndex));
    }

    function goTo(index) {
      const normalized = (index + slides.length) % slides.length;
      activate(normalized);
      scheduleNext();
    }

    if (prevButton) {
      prevButton.addEventListener('click', function () {
        goTo(activeIndex - 1);
      });
    }

    if (nextButton) {
      nextButton.addEventListener('click', function () {
        goTo(activeIndex + 1);
      });
    }

    indicators.forEach(function (indicator) {
      indicator.addEventListener('click', function () {
        const targetIndex = Number(indicator.dataset.carouselIndicator || 0);
        goTo(targetIndex);
      });
    });

    carousel.addEventListener('mouseenter', function () {
      clearTimeout(timerId);
    });

    carousel.addEventListener('mouseleave', function () {
      scheduleNext();
    });

    scheduleNext();
  }

  document.addEventListener('DOMContentLoaded', function () {
    initFaqSection();
    initHeroCarousel();
  });
})();
