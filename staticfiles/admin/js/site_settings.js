// 사이트 설정 어드민 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    'use strict';
    
    // 유튜브 비디오 ID 입력 필드
    const youtubeInput = document.querySelector('#id_youtube_video_id');
    const autoplayCheckbox = document.querySelector('#id_youtube_autoplay');
    const muteCheckbox = document.querySelector('#id_youtube_mute');
    const loopCheckbox = document.querySelector('#id_youtube_loop');
    const controlsCheckbox = document.querySelector('#id_youtube_controls');
    
    if (youtubeInput) {
        // 미리보기 컨테이너 생성
        const previewContainer = document.createElement('div');
        previewContainer.className = 'youtube-preview';
        previewContainer.innerHTML = `
            <h4 style="margin: 0 0 10px 0; color: #333;">미리보기</h4>
            <iframe id="youtube-preview-iframe" allowfullscreen></iframe>
            <div class="youtube-help">
                <strong>도움말:</strong> 
                <a href="https://www.youtube.com/watch?v=dd2RzyPu4ok" target="_blank">
                    https://www.youtube.com/watch?v=dd2RzyPu4ok
                </a>에서 <code>dd2RzyPu4ok</code> 부분만 입력하세요.
            </div>
        `;
        
        // 입력 필드 다음에 미리보기 추가
        youtubeInput.parentNode.appendChild(previewContainer);
        
        // 유튜브 URL 생성 함수
        function generateYouTubeURL(videoId) {
            if (!videoId || videoId.length !== 11) {
                return '';
            }
            
            const params = [];
            
            if (autoplayCheckbox && autoplayCheckbox.checked) {
                params.push('autoplay=1');
            }
            if (muteCheckbox && muteCheckbox.checked) {
                params.push('mute=1');
            }
            if (loopCheckbox && loopCheckbox.checked) {
                params.push(`loop=1&playlist=${videoId}`);
            }
            if (controlsCheckbox && !controlsCheckbox.checked) {
                params.push('controls=0');
            }
            
            // 기본 매개변수
            params.push(
                'showinfo=0',
                'rel=0',
                'iv_load_policy=3',
                'modestbranding=1',
                'disablekb=1',
                'fs=0',
                'cc_load_policy=0',
                'playsinline=1',
                'enablejsapi=1'
            );
            
            const paramString = params.join('&');
            return `https://www.youtube.com/embed/${videoId}?${paramString}`;
        }
        
        // 미리보기 업데이트 함수
        function updatePreview() {
            const videoId = youtubeInput.value.trim();
            const iframe = document.getElementById('youtube-preview-iframe');
            
            if (videoId && videoId.length === 11) {
                const url = generateYouTubeURL(videoId);
                iframe.src = url;
                previewContainer.classList.add('show');
            } else {
                iframe.src = '';
                previewContainer.classList.remove('show');
            }
        }
        
        // 유튜브 비디오 ID 유효성 검사
        function validateVideoId(videoId) {
            const pattern = /^[a-zA-Z0-9_-]{11}$/;
            return pattern.test(videoId);
        }
        
        // 입력 필드 스타일 업데이트
        function updateInputStyle() {
            const videoId = youtubeInput.value.trim();
            
            if (videoId === '') {
                youtubeInput.style.borderColor = '#e1e5e9';
                return;
            }
            
            if (validateVideoId(videoId)) {
                youtubeInput.style.borderColor = '#28a745';
                youtubeInput.style.boxShadow = '0 0 0 3px rgba(40, 167, 69, 0.1)';
            } else {
                youtubeInput.style.borderColor = '#dc3545';
                youtubeInput.style.boxShadow = '0 0 0 3px rgba(220, 53, 69, 0.1)';
            }
        }
        
        // 이벤트 리스너 등록
        youtubeInput.addEventListener('input', function() {
            updateInputStyle();
            
            // 디바운스를 위한 타이머
            clearTimeout(this.updateTimer);
            this.updateTimer = setTimeout(updatePreview, 500);
        });
        
        // 체크박스 변경 시 미리보기 업데이트
        [autoplayCheckbox, muteCheckbox, loopCheckbox, controlsCheckbox].forEach(checkbox => {
            if (checkbox) {
                checkbox.addEventListener('change', updatePreview);
            }
        });
        
        // 초기 미리보기 표시
        updateInputStyle();
        updatePreview();
    }
    
    // 폼 제출 시 유효성 검사
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const videoId = youtubeInput ? youtubeInput.value.trim() : '';
            
            if (videoId && !validateVideoId(videoId)) {
                e.preventDefault();
                alert('올바른 유튜브 비디오 ID를 입력하세요. (11자리 영숫자, 하이픈, 언더스코어만 허용)');
                youtubeInput.focus();
                return false;
            }
        });
    }
    
    // 도움말 툴팁 추가
    function addTooltips() {
        const helpTexts = document.querySelectorAll('.help');
        helpTexts.forEach(help => {
            help.style.cursor = 'help';
            help.title = help.textContent;
        });
    }
    
    addTooltips();
    
    // 저장 성공 메시지
    const messages = document.querySelectorAll('.messagelist .success');
    messages.forEach(message => {
        if (message.textContent.includes('성공적으로 변경')) {
            message.innerHTML = `
                <i class="fas fa-check-circle"></i> 
                사이트 설정이 성공적으로 저장되었습니다! 
                <a href="/" target="_blank" style="color: white; text-decoration: underline;">
                    홈페이지에서 확인하기
                </a>
            `;
        }
    });
}); 