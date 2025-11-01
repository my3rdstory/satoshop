document.addEventListener('DOMContentLoaded', () => {
    const burger = document.querySelector('.navbar-burger');
    const menu = document.querySelector('#expert-navbar-menu');

    if (burger && menu) {
        burger.addEventListener('click', () => {
            burger.classList.toggle('is-active');
            menu.classList.toggle('is-active');
        });
    }

    if (window.feather) {
        window.feather.replace();
    }
});
