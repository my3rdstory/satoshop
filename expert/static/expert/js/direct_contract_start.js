document.addEventListener('DOMContentLoaded', () => {
    const checklistItems = document.querySelectorAll('.checklist-box li');
    checklistItems.forEach((item) => {
        item.addEventListener('mouseenter', () => item.classList.add('is-highlighted'));
        item.addEventListener('mouseleave', () => item.classList.remove('is-highlighted'));
    });
});
