document.addEventListener('DOMContentLoaded', function () {
    const gradientPreview = document.getElementById('gradient_preview');
    const color1Input = document.getElementById('hero_color1');
    const color2Input = document.getElementById('hero_color2');
    const textColorInput = document.getElementById('hero_text_color');

    // 그라디언트 미리보기 업데이트
    function updatePreview() {
        const color1 = color1Input.value;
        const color2 = color2Input.value;
        const textColor = textColorInput.value;

        gradientPreview.style.background = `linear-gradient(135deg, ${color1}, ${color2})`;
        gradientPreview.querySelector('h3').style.color = textColor;
        
        // 색상 값 표시 업데이트
        updateColorDisplays();
    }

    // 색상 값 표시 업데이트
    function updateColorDisplays() {
        const color1Display = document.querySelector('input[name="hero_color1"]').parentElement.querySelector('span');
        const color2Display = document.querySelector('input[name="hero_color2"]').parentElement.querySelector('span');
        const textColorDisplay = document.querySelector('input[name="hero_text_color"]').parentElement.querySelector('span');
        
        if (color1Display) color1Display.textContent = color1Input.value;
        if (color2Display) color2Display.textContent = color2Input.value;
        if (textColorDisplay) textColorDisplay.textContent = textColorInput.value;
    }

    // 이벤트 리스너
    color1Input.addEventListener('input', updatePreview);
    color2Input.addEventListener('input', updatePreview);
    textColorInput.addEventListener('input', updatePreview);

    // 프리셋 색상 선택
    document.querySelectorAll('.preset-color').forEach(preset => {
        preset.addEventListener('click', function () {
            // 모든 프리셋에서 활성화 클래스 제거
            document.querySelectorAll('.preset-color').forEach(p => p.classList.remove('is-active'));
            // 현재 선택된 프리셋에 활성화 클래스 추가
            this.classList.add('is-active');

            const color1 = this.dataset.color1;
            const color2 = this.dataset.color2;
            const textColor = this.dataset.text;

            color1Input.value = color1;
            color2Input.value = color2;
            textColorInput.value = textColor;

            updatePreview();
        });
    });

    // 초기 미리보기 업데이트
    updatePreview();
}); 