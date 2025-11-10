(() => {
    const widgetControllers = new Map();

    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    };

    class PaymentWidgetController {
        constructor(element) {
            this.el = element;
            this.statusUrl = element.dataset.paymentStatusUrl || '';
            this.refreshUrl = element.dataset.paymentRefreshUrl || '';
            this.context = element.dataset.paymentContext;
            this.ref = element.dataset.paymentRef;
            this.role = element.dataset.paymentRole;
            this.required = element.dataset.paymentRequired === 'true';
            this.status = element.dataset.paymentStatus || 'idle';
            this.remainingSeconds = parseInt(element.dataset.paymentCountdownRemaining || '0', 10);
            this.totalSeconds = parseInt(element.dataset.paymentCountdownTotal || '60', 10);
            this.paymentHash = element.dataset.paymentHash || '';
            this.csrfToken = element.dataset.paymentCsrf || getCookie('csrftoken');
            this.statusInput = element.querySelector('[data-payment-status-input]');
            this.statusText = element.querySelector('[data-payment-status-text]');
            this.countdownText = element.querySelector('[data-payment-countdown-text]');
            this.pollTimer = null;
            this.countdownTimer = null;
        }

        init() {
            if (!this.required) {
                this.updateStatusInput('paid');
                return;
            }
            this.updateStatusInput(this.status);
            if (this.status === 'invoice') {
                if (!Number.isFinite(this.remainingSeconds) || this.remainingSeconds <= 0) {
                    this.remainingSeconds = this.totalSeconds;
                }
                this.startCountdown();
                this.startPolling();
            } else if (this.status === 'paid') {
                this.updateStatusInput('paid');
            }
        }

        startCountdown() {
            this.stopCountdown();
            this.updateCountdownDisplay();
            this.countdownTimer = window.setInterval(() => {
                this.remainingSeconds -= 1;
                if (this.remainingSeconds <= 0) {
                    this.stopCountdown();
                    this.refresh();
                    return;
                }
                this.updateCountdownDisplay();
            }, 1000);
        }

        stopCountdown() {
            if (this.countdownTimer) {
                window.clearInterval(this.countdownTimer);
                this.countdownTimer = null;
            }
        }

        updateCountdownDisplay() {
            if (!this.countdownText) {
                return;
            }
            const seconds = Math.max(0, this.remainingSeconds);
            this.countdownText.textContent = `만료까지 ${seconds}초 남았습니다.`;
        }

        startPolling() {
            if (!this.statusUrl || !this.paymentHash) {
                return;
            }
            this.stopPolling();
            this.poll();
            this.pollTimer = window.setInterval(() => {
                this.poll();
            }, 1000);
        }

        stopPolling() {
            if (this.pollTimer) {
                window.clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        }

        poll() {
            if (!this.statusUrl || !this.paymentHash) {
                return;
            }
            fetch(this.statusUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({
                    context: this.context,
                    ref: this.ref,
                    role: this.role,
                }),
            })
                .then((response) => response.json())
                .then((data) => this.handleStatusResponse(data))
                .catch(() => {
                    this.stopPolling();
                    this.refresh();
                });
        }

        handleStatusResponse(payload) {
            if (!payload || !payload.ok) {
                this.stopPolling();
                this.refresh();
                return;
            }
            if (payload.status === 'paid') {
                this.status = 'paid';
                this.stopCountdown();
                this.stopPolling();
                this.updateStatusInput('paid');
                this.refresh();
                return;
            }
            if (payload.status === 'expired') {
                this.stopCountdown();
                this.stopPolling();
                this.refresh();
                return;
            }
            if (payload.status === 'pending') {
                if (typeof payload.remaining_seconds === 'number') {
                    this.remainingSeconds = payload.remaining_seconds;
                    this.updateCountdownDisplay();
                }
                if (payload.message) {
                    this.updateStatusText(payload.message);
                }
                return;
            }
            if (payload.status === 'skipped') {
                this.status = 'paid';
                this.stopCountdown();
                this.stopPolling();
                this.updateStatusInput('paid');
                return;
            }
            if (payload.status === 'error') {
                this.stopPolling();
                this.refresh();
            }
        }

        updateStatusInput(value) {
            if (this.statusInput) {
                this.statusInput.value = value;
                this.statusInput.dispatchEvent(new Event('input', { bubbles: true }));
                this.statusInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            this.el.dataset.paymentStatus = value;
        }

        updateStatusText(text) {
            if (this.statusText) {
                this.statusText.textContent = text;
            }
        }

        refresh() {
            if (this.refreshUrl) {
                if (window.htmx && typeof window.htmx.ajax === 'function') {
                    window.htmx.ajax('GET', this.refreshUrl, {
                        target: `#${this.el.id}`,
                        swap: 'outerHTML',
                    });
                } else {
                    fetch(this.refreshUrl, {
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    })
                        .then((response) => response.text())
                        .then((html) => {
                            this.el.outerHTML = html;
                        })
                        .catch(() => {
                            this.updateStatusText('새 데이터를 불러오지 못했습니다. 다시 시도해주세요.');
                        });
                }
            }
        }

        destroy() {
            this.stopCountdown();
            this.stopPolling();
        }
    }

    const initWidget = (element) => {
        if (!element.id) {
            return;
        }
        const existing = widgetControllers.get(element.id);
        if (existing) {
            existing.destroy();
        }
        const controller = new PaymentWidgetController(element);
        controller.init();
        widgetControllers.set(element.id, controller);
    };

    const scan = (scope) => {
        scope.querySelectorAll('[data-payment-widget-root]').forEach((element) => {
            initWidget(element);
        });
    };

    document.addEventListener('DOMContentLoaded', () => {
        scan(document);
    });

    document.body.addEventListener('htmx:afterSwap', (event) => {
        const target = event.target;
        if (!target) {
            return;
        }
        if (target.matches('[data-payment-widget-root]')) {
            initWidget(target);
        } else {
            scan(target);
        }
    });

    document.body.addEventListener('htmx:beforeSwap', (event) => {
        const target = event.target;
        if (!target || !target.matches('[data-payment-widget-root]')) {
            return;
        }
        const controller = widgetControllers.get(target.id);
        if (controller) {
            controller.destroy();
            widgetControllers.delete(target.id);
        }
    });
})();
