'use strict';

(function() {
  const mobileMenuButton = document.getElementById('mobile-menu-button');
  const mobileMenu = document.getElementById('mobile-menu');

  function setMenuState(open) {
    if (!mobileMenu) {
      return;
    }

    mobileMenu.classList.toggle('is-open', open);
    mobileMenu.setAttribute('aria-expanded', open ? 'true' : 'false');
    mobileMenu.setAttribute('aria-hidden', open ? 'false' : 'true');
    const icon = mobileMenuButton ? mobileMenuButton.querySelector('.icon') : null;

    if (icon) {
      icon.dataset.state = open ? 'open' : 'closed';
    }
  }

  if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.setAttribute('aria-expanded', 'false');
    mobileMenu.setAttribute('aria-hidden', 'true');

    mobileMenuButton.addEventListener('click', function(event) {
      event.preventDefault();
      const isOpen = !mobileMenu.classList.contains('is-open');
      setMenuState(isOpen);
    });

    mobileMenuButton.addEventListener('keydown', function(event) {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      event.preventDefault();
      const isOpen = !mobileMenu.classList.contains('is-open');
      setMenuState(isOpen);
    });

    mobileMenu.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        setMenuState(false);
      });
    });
  }

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      setMenuState(false);
    }
  });
})();
