document.addEventListener('DOMContentLoaded', () => {
    const ctaButtons = document.querySelectorAll('[data-scroll-target]');

    ctaButtons.forEach((button) => {
        button.addEventListener('click', (event) => {
            const targetId = event.currentTarget.getAttribute('data-scroll-target');
            if (!targetId) {
                return;
            }
            const target = document.getElementById(targetId);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});
