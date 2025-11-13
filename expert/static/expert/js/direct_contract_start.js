document.addEventListener('DOMContentLoaded', () => {
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card) => {
        card.addEventListener('mouseenter', () => card.classList.add('is-highlighted'));
        card.addEventListener('mouseleave', () => card.classList.remove('is-highlighted'));
    });

    applyStatCardMotion();
});

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
