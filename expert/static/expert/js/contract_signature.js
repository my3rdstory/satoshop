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
            submitButton.disabled = !(hasSignature && confirmed);
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

        if (hiddenInput.value) {
            updatePreview(hiddenInput.value);
        }
        updateButtonState();
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSignaturePads);
} else {
    initSignaturePads();
}
