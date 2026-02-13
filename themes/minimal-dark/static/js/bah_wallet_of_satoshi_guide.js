(function() {
  document.addEventListener('DOMContentLoaded', function() {
    const sections = document.querySelectorAll('.guide-section');
    sections.forEach(function(section, index) {
      const toggle = section.querySelector('[data-toggle]');
      const content = section.querySelector('[data-content]');
      const icon = section.querySelector('[data-icon]');

      if (!toggle || !content || !icon) {
        return;
      }

      if (index === 0) {
        section.setAttribute('data-open', 'true');
        content.style.display = 'block';
      }

      toggle.addEventListener('click', function() {
        const isOpen = section.getAttribute('data-open') === 'true';
        if (isOpen) {
          section.setAttribute('data-open', 'false');
          content.style.display = 'none';
        } else {
          section.setAttribute('data-open', 'true');
          content.style.display = 'block';
        }
      });
    });
  });
})();
