document.addEventListener('DOMContentLoaded', () => {
    initFeatureCardHover();
    applyStatCardMotion();
    initExpertHeroCarousel();
});

function initFeatureCardHover() {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card) => {
        card.addEventListener('mouseenter', () => card.classList.add('is-highlighted'));
        card.addEventListener('mouseleave', () => card.classList.remove('is-highlighted'));
    });
}

function initExpertHeroCarousel() {
    const carousel = document.querySelector('[data-expert-hero-carousel]');
    if (!carousel) {
        return;
    }

    const slides = Array.from(carousel.querySelectorAll('[data-expert-hero-slide]'));
    if (!slides.length) {
        return;
    }

    const prevButton = carousel.querySelector('[data-expert-carousel-prev]');
    const nextButton = carousel.querySelector('[data-expert-carousel-next]');
    const indicators = Array.from(carousel.querySelectorAll('[data-expert-carousel-indicator]'));
    let activeIndex = Math.max(0, slides.findIndex((slide) => slide.classList.contains('is-active')));
    if (activeIndex < 0) {
        activeIndex = 0;
        slides[0].classList.add('is-active');
    }
    let timerId = null;

    const getDuration = (index) => {
        const raw = Number(slides[index].dataset.duration || '6');
        return Math.max(raw, 3) * 1000;
    };

    const activate = (index) => {
        slides.forEach((slide, idx) => {
            slide.classList.toggle('is-active', idx === index);
        });
        indicators.forEach((indicator) => {
            const target = Number(indicator.dataset.expertCarouselIndicator || 0);
            indicator.classList.toggle('is-active', target === index);
        });
        activeIndex = index;
    };

    const scheduleNext = () => {
        clearTimeout(timerId);
        if (slides.length <= 1) {
            return;
        }
        timerId = setTimeout(() => goTo(activeIndex + 1), getDuration(activeIndex));
    };

    const goTo = (index) => {
        const normalized = (index + slides.length) % slides.length;
        activate(normalized);
        scheduleNext();
    };

    if (prevButton) {
        prevButton.addEventListener('click', () => goTo(activeIndex - 1));
    }

    if (nextButton) {
        nextButton.addEventListener('click', () => goTo(activeIndex + 1));
    }

    indicators.forEach((indicator) => {
        indicator.addEventListener('click', () => {
            const target = Number(indicator.dataset.expertCarouselIndicator || 0);
            goTo(target);
        });
    });

    carousel.addEventListener('mouseenter', () => clearTimeout(timerId));
    carousel.addEventListener('mouseleave', () => scheduleNext());

    scheduleNext();
}

function applyStatCardMotion() {
    const statCards = document.querySelectorAll('.stat-card');
    if (!statCards.length) {
        return;
    }

    const randomBetween = (min, max) => Math.random() * (max - min) + min;
    const toPercent = (value) => `${value.toFixed(1)}%`;
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

    statCards.forEach((card) => {
        const duration = randomBetween(10, 18);
        const delay = randomBetween(-4, 3);
        const direction = Math.random() > 0.5 ? 'alternate' : 'alternate-reverse';

        const startX = randomBetween(-18, -6);
        const startY = randomBetween(-16, -6);
        const endX = randomBetween(-15, -5);
        const endY = randomBetween(-14, -6);
        const midX = randomBetween(-4, 12);
        const midY = randomBetween(-2, 11);

        const baseScale = randomBetween(0.9, 1.1);
        const peakScale = clamp(baseScale + randomBetween(0.05, 0.3), 1, 1.35);

        const opacityStart = randomBetween(0.25, 0.45);
        const opacityPeak = clamp(opacityStart + randomBetween(0.15, 0.35), 0.45, 0.8);

        const hueA = Math.floor(randomBetween(180, 320));
        const hueB = (hueA + Math.floor(randomBetween(20, 120))) % 360;

        const set = (prop, value) => card.style.setProperty(prop, value);

        set('--pulse-duration', `${duration.toFixed(2)}s`);
        set('--pulse-delay', `${delay.toFixed(2)}s`);
        set('--pulse-direction', direction);

        set('--pulse-start-x', toPercent(startX));
        set('--pulse-start-y', toPercent(startY));
        set('--pulse-mid-x', toPercent(midX));
        set('--pulse-mid-y', toPercent(midY));
        set('--pulse-end-x', toPercent(endX));
        set('--pulse-end-y', toPercent(endY));

        set('--pulse-scale', baseScale.toFixed(2));
        set('--pulse-scale-peak', peakScale.toFixed(2));

        set('--pulse-opacity-start', opacityStart.toFixed(2));
        set('--pulse-opacity-peak', opacityPeak.toFixed(2));
        set('--pulse-opacity-end', opacityStart.toFixed(2));

        set('--pulse-hue-a', hueA.toString());
        set('--pulse-hue-b', hueB.toString());
    });
}
