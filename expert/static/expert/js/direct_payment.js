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
            this.startUrl = element.dataset.paymentStartUrl || '';
            this.cancelUrl = element.dataset.paymentCancelUrl || '';
            this.required = element.dataset.paymentRequired === 'true';
            this.status = element.dataset.paymentStatus || 'idle';
            this.remainingSeconds = parseInt(element.dataset.paymentCountdownRemaining || '0', 10);
            this.totalSeconds = parseInt(element.dataset.paymentCountdownTotal || '60', 10);
            this.paymentHash = element.dataset.paymentHash || '';
            this.csrfToken = element.dataset.paymentCsrf || getCookie('csrftoken');
            this.statusInput = this._locateStatusInput();
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

        handleAction(action, trigger) {
            if (!action) {
                return;
            }
            if (action === 'start') {
                this.performAction(this.startUrl, trigger);
            } else if (action === 'cancel') {
                this.performAction(this.cancelUrl, trigger);
            }
        }

        async performAction(url, trigger) {
            if (!url) {
                return;
            }
            this.setButtonLoading(trigger, true);
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-CSRFToken': this.csrfToken,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: this.buildActionPayload(),
                });
                const html = await response.text();
                if (!response.ok || !html) {
                    throw new Error('결제 정보를 불러오지 못했습니다.');
                }
                if (!html.includes('data-payment-widget-root')) {
                    throw new Error('결제 정보를 불러오지 못했습니다.');
                }
                this.replaceWithHtml(html);
            } catch (error) {
                const message = (error && error.message) || '결제 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.';
                this.updateStatusText(message);
            } finally {
                this.setButtonLoading(trigger, false);
            }
        }

        buildActionPayload() {
            const params = new URLSearchParams();
            if (this.context) {
                params.append('context', this.context);
            }
            if (this.ref) {
                params.append('ref', this.ref);
            }
            if (this.role) {
                params.append('role', this.role);
            }
            return params.toString();
        }

        setButtonLoading(trigger, isLoading) {
            if (!trigger) {
                return;
            }
            if (isLoading) {
                trigger.classList.add('is-loading');
                trigger.setAttribute('disabled', 'disabled');
            } else {
                trigger.classList.remove('is-loading');
                trigger.removeAttribute('disabled');
            }
        }

        replaceWithHtml(html) {
            if (!html || typeof html !== 'string') {
                return;
            }
            if (!html.includes('data-payment-widget-root')) {
                this.updateStatusText('결제 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.');
                return;
            }
            const placeholderId = this.el.id;
            this.destroy();
            widgetControllers.delete(placeholderId);
            this.el.outerHTML = html;
            const nextElement = document.getElementById(placeholderId);
            if (nextElement) {
                initWidget(nextElement);
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
            const statusInput = this._locateStatusInput();
            if (statusInput) {
                statusInput.value = value;
                statusInput.dispatchEvent(new Event('input', { bubbles: true }));
                statusInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            this.el.dataset.paymentStatus = value;
        }

        _locateStatusInput() {
            if (this.statusInput && document.body.contains(this.statusInput)) {
                return this.statusInput;
            }
            const form = this.el.closest('form');
            if (!form) {
                return null;
            }
            this.statusInput = form.querySelector('[data-payment-status-input]');
            return this.statusInput;
        }

        updateStatusText(text) {
            if (this.statusText) {
                this.statusText.textContent = text;
            }
        }

        refresh() {
            if (!this.refreshUrl) {
                return;
            }
            fetch(this.refreshUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error('새 데이터를 불러오지 못했습니다.');
                    }
                    return response.text();
                })
                .then((html) => {
                    this.replaceWithHtml(html);
                })
                .catch(() => {
                    this.updateStatusText('새 데이터를 불러오지 못했습니다. 다시 시도해주세요.');
                });
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

    document.addEventListener('click', (event) => {
        const actionButton = event.target.closest('[data-payment-action]');
        if (actionButton) {
            event.preventDefault();
            const widget = actionButton.closest('[data-payment-widget-root]');
            if (!widget) {
                return;
            }
            const controller = widgetControllers.get(widget.id);
            if (controller) {
                controller.handleAction(actionButton.dataset.paymentAction, actionButton);
            }
            return;
        }
        const copyTrigger = event.target.closest('[data-payment-copy]');
        if (copyTrigger) {
            event.preventDefault();
            handleInvoiceCopy(copyTrigger);
            return;
        }
        const walletTrigger = event.target.closest('[data-payment-open-wallet]');
        if (walletTrigger) {
            event.preventDefault();
            handleInvoiceWallet(walletTrigger);
        }
    });

    function handleInvoiceCopy(button) {
        const invoiceField = locateInvoiceField(button);
        if (!invoiceField || !invoiceField.value) {
            button.classList.add('is-danger');
            button.textContent = '인보이스 없음';
            window.setTimeout(() => {
                button.classList.remove('is-danger');
                button.textContent = '인보이스 복사';
            }, 1500);
            return;
        }
        const value = invoiceField.value.trim();
        const revert = () => {
            button.classList.remove('is-success');
            button.textContent = '인보이스 복사';
        };
        const markSuccess = () => {
            button.classList.add('is-success');
            button.textContent = '복사 완료';
            window.setTimeout(revert, 1400);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(value).then(markSuccess).catch(() => {
                fallbackCopy(invoiceField, value, markSuccess);
            });
        } else {
            fallbackCopy(invoiceField, value, markSuccess);
        }
    }

    function handleInvoiceWallet(button) {
        const invoiceField = locateInvoiceField(button);
        if (!invoiceField || !invoiceField.value) {
            button.classList.add('is-danger');
            window.setTimeout(() => button.classList.remove('is-danger'), 1200);
            return;
        }
        const rawValue = invoiceField.value.trim();
        const lightningUri = rawValue.startsWith('lightning:') ? rawValue : `lightning:${rawValue}`;
        try {
            window.location.assign(lightningUri);
        } catch (error) {
            console.error('라이트닝 지갑 열기 실패', error);
            button.classList.add('is-danger');
            window.setTimeout(() => button.classList.remove('is-danger'), 1400);
        }
    }

    function locateInvoiceField(element) {
        const widget = element.closest('[data-payment-widget-root]');
        if (!widget) {
            return null;
        }
        return widget.querySelector('[data-payment-invoice-text]');
    }

    function fallbackCopy(field, value, onSuccess) {
        field.focus();
        field.select();
        const copied = document.execCommand('copy');
        if (copied) {
            onSuccess();
        }
    }
})();
