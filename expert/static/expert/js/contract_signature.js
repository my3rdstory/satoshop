const initSignaturePads = () => {
    if (typeof SignaturePad === 'undefined') {
        return;
    }

    const canvases = document.querySelectorAll('[data-signature-canvas]');
    if (!canvases.length) {
        return;
    }

    canvases.forEach((canvas) => {
        const form = canvas.closest('form');
        if (!form) {
            return;
        }

        let hiddenInput = form.querySelector('[data-signature-input]');
        if (!hiddenInput) {
            hiddenInput = form.querySelector('input[name="signature_data"]');
        }
        const clearButton = form.querySelector('[data-signature-clear]');
        const confirmInputs = form.querySelectorAll('[data-signature-confirm]');
        const submitButton = form.querySelector('[data-signature-submit]');
        const previewWrapper = form.querySelector('[data-signature-preview]');
        const previewImage = form.querySelector('[data-signature-preview-img]');
        const paymentStatusInput = form.querySelector('[data-payment-status-input]');

        if (!hiddenInput || !submitButton) {
            return;
        }

        const signaturePad = new SignaturePad(canvas, {
            backgroundColor: 'rgba(15, 23, 42, 0.9)',
            penColor: '#22d3ee',
        });

        function updatePreview(dataUrl) {
            if (!previewWrapper || !previewImage) {
                return;
            }
            if (dataUrl && dataUrl.startsWith('data:image/')) {
                previewWrapper.hidden = false;
                previewImage.src = dataUrl;
            } else {
                previewWrapper.hidden = true;
                previewImage.src = '';
            }
        }

        function updateButtonState() {
            const hasDataUrl = hiddenInput.value && hiddenInput.value.startsWith('data:image/');
            const hasSignature = hasDataUrl || !signaturePad.isEmpty();
            if (!hasDataUrl && hasSignature) {
                hiddenInput.value = signaturePad.toDataURL('image/png');
            }
            const confirmed = confirmInputs.length
                ? Array.from(confirmInputs).every((input) => input.checked)
                : true;
            const paymentSatisfied = !paymentStatusInput || paymentStatusInput.value === 'paid';
            submitButton.disabled = !(hasSignature && confirmed && paymentSatisfied);
        }

        const resizeCanvas = () => {
            const ratio = Math.max(window.devicePixelRatio || 1, 1);
            canvas.width = canvas.offsetWidth * ratio;
            canvas.height = canvas.offsetHeight * ratio;
            canvas.getContext('2d').scale(ratio, ratio);
            signaturePad.clear();
            hiddenInput.value = '';
            updatePreview('');
            updateButtonState();
        };

        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        signaturePad.onEnd = () => {
            const dataUrl = signaturePad.toDataURL('image/png');
            hiddenInput.value = dataUrl;
            updatePreview(dataUrl);
            updateButtonState();
        };

        if (clearButton) {
            clearButton.addEventListener('click', (event) => {
                event.preventDefault();
                signaturePad.clear();
                hiddenInput.value = '';
                updatePreview('');
                updateButtonState();
            });
        }

        if (confirmInputs.length) {
            confirmInputs.forEach((input) => {
                input.addEventListener('change', updateButtonState);
            });
        }

        if (paymentStatusInput) {
            paymentStatusInput.addEventListener('input', updateButtonState);
            paymentStatusInput.addEventListener('change', updateButtonState);
        }

        if (hiddenInput.value) {
            updatePreview(hiddenInput.value);
        }
        updateButtonState();

        form.addEventListener('submit', () => {
            if (!submitButton) {
                return;
            }
            submitButton.disabled = true;
            submitButton.dataset.originalLabel = submitButton.dataset.originalLabel || submitButton.innerHTML;
            submitButton.innerHTML = '진행 중입니다... 잠시만 기다려 주세요.';
        });
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSignaturePads);
} else {
    initSignaturePads();
}

const fallbackCopyText = (text) => {
    return new Promise((resolve, reject) => {
        try {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            textarea.style.top = '0';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();
            const succeeded = document.execCommand && document.execCommand('copy');
            document.body.removeChild(textarea);
            if (succeeded) {
                resolve();
            } else {
                reject(new Error('execCommand failed'));
            }
        } catch (error) {
            reject(error);
        }
    });
};

const promptCopy = (text) => {
    return new Promise((resolve, reject) => {
        const result = window.prompt('복사 버튼이 차단되어 직접 복사해주세요.', text);
        if (result !== null) {
            resolve();
        } else {
            reject(new Error('prompt dismissed'));
        }
    });
};

const copyShareUrl = async (text) => {
    if (!text) {
        throw new Error('empty text');
    }
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        try {
            await navigator.clipboard.writeText(text);
            return;
        } catch (error) {
            // continue to fallback
        }
    }
    try {
        await fallbackCopyText(text);
        return;
    } catch (error) {
        // continue to prompt fallback
    }
    await promptCopy(text);
};

document.addEventListener('click', (event) => {
    const button = event.target.closest('.copy-share-url');
    if (!button) {
        return;
    }
    const url = button.getAttribute('data-share-url');
    if (!url) {
        return;
    }
    copyShareUrl(url)
        .then(() => {
            button.classList.add('is-success');
            button.textContent = '복사 완료';
            setTimeout(() => {
                button.classList.remove('is-success');
                button.textContent = '링크 복사';
            }, 1800);
        })
        .catch(() => {
            button.classList.add('is-danger');
            button.textContent = '복사 실패';
            setTimeout(() => {
                button.classList.remove('is-danger');
                button.textContent = '링크 복사';
            }, 2000);
        });
});
