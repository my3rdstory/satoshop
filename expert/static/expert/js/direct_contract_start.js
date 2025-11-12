document.addEventListener('DOMContentLoaded', () => {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card) => {
        card.addEventListener('mouseenter', () => card.classList.add('is-highlighted'));
        card.addEventListener('mouseleave', () => card.classList.remove('is-highlighted'));
    });
});
