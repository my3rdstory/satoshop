document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.querySelector('[data-signature-canvas]');
    const hiddenInput = document.querySelector('[data-signature-input]');
    const clearButton = document.querySelector('[data-signature-clear]');
    const confirmInputs = document.querySelectorAll('[data-signature-confirm]');
    const submitButton = document.querySelector('[data-signature-submit]');

    if (!canvas || !hiddenInput || typeof SignaturePad === 'undefined') {
        return;
    }

    const signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        penColor: '#22d3ee',
    });

    const resizeCanvas = () => {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext('2d').scale(ratio, ratio);
        signaturePad.clear();
        hiddenInput.value = '';
        updateButtonState();
    };

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    const updateButtonState = () => {
        if (!submitButton) {
            return;
        }
        const hasSignature = hiddenInput.value && hiddenInput.value.length > 20;
        const confirmed = confirmInputs.length
            ? Array.from(confirmInputs).every((input) => input.checked)
            : true;
        submitButton.disabled = !(hasSignature && confirmed);
    };

    signaturePad.onEnd = () => {
        hiddenInput.value = signaturePad.toDataURL('image/png');
        updateButtonState();
    };

    if (clearButton) {
        clearButton.addEventListener('click', (event) => {
            event.preventDefault();
            signaturePad.clear();
            hiddenInput.value = '';
            updateButtonState();
        });
    }

    if (confirmInputs.length) {
        confirmInputs.forEach((input) => {
            input.addEventListener('change', updateButtonState);
        });
    }

    updateButtonState();
});
