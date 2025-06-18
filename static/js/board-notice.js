/**
 * 공지사항 전용 JavaScript - board-notice.js
 */

// ===== 댓글 관련 기능 =====

/**
 * 답글 폼 토글
 */
function toggleReplyForm(commentId) {
    const replyForm = document.getElementById('reply-form-' + commentId);
    if (replyForm.classList.contains('active')) {
        replyForm.classList.remove('active');
    } else {
        // 다른 열린 답글 폼들 닫기
        document.querySelectorAll('.reply-form.active').forEach(form => {
            form.classList.remove('active');
        });
        replyForm.classList.add('active');
        replyForm.querySelector('textarea').focus();
    }
}

/**
 * 댓글 삭제
 */
function deleteComment(commentId) {
    if (confirm('정말로 이 댓글을 삭제하시겠습니까?')) {
        // 댓글 삭제를 위한 폼 생성 및 제출
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/boards/comment/' + commentId + '/delete/';
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        
        form.appendChild(csrfInput);
        document.body.appendChild(form);
        form.submit();
    }
}

// ===== 댓글 수정 관련 기능 =====

/**
 * 댓글 수정 페이지 초기화
 */
function initCommentEdit() {
    const contentTextarea = document.getElementById('id_content');
    const contentCounter = document.getElementById('content-counter');
    const commentForm = document.getElementById('comment-form');
    
    if (!contentTextarea || !contentCounter || !commentForm) {
        return;
    }
    
    // 글자수 카운터 업데이트
    function updateContentCounter() {
        const length = contentTextarea.value.length;
        contentCounter.textContent = length;
        
        // 글자수에 따른 색상 변경
        if (length > 1000) {
            contentCounter.style.color = '#dc3545';
        } else if (length > 500) {
            contentCounter.style.color = '#ffc107';
        } else {
            contentCounter.style.color = '';
        }
    }
    
    contentTextarea.addEventListener('input', updateContentCounter);
    
    // 초기 카운터 설정
    updateContentCounter();
    
    // 폼 제출 시 확인
    commentForm.addEventListener('submit', function(e) {
        const content = contentTextarea.value.trim();
        
        if (!content) {
            e.preventDefault();
            alert('댓글 내용을 입력해주세요.');
            contentTextarea.focus();
            return;
        }
        
        if (!confirm('댓글을 수정하시겠습니까?')) {
            e.preventDefault();
        }
    });
    
    // 변경사항 감지
    const originalContent = contentTextarea.value;
    
    function hasChanges() {
        return contentTextarea.value !== originalContent;
    }
    
    // 페이지 이탈 시 경고
    window.addEventListener('beforeunload', function(e) {
        if (hasChanges()) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
    
    // 취소 버튼 클릭 시 확인
    const cancelButton = document.querySelector('a[href*="notice"]');
    if (cancelButton) {
        cancelButton.addEventListener('click', function(e) {
            if (hasChanges()) {
                if (!confirm('변경사항이 저장되지 않습니다. 정말 나가시겠습니까?')) {
                    e.preventDefault();
                }
            }
        });
    }
    

}



// ===== 공지사항 작성/수정 관련 기능 =====

/**
 * 공지사항 폼 초기화
 */
function initNoticeForm() {
    const titleInput = document.getElementById('id_title');
    const contentTextarea = document.getElementById('id_content');
    const titleCounter = document.getElementById('title-counter');
    const contentCounter = document.getElementById('content-counter');
    const noticeForm = document.querySelector('form');
    
    // 제목 글자수 카운터
    if (titleInput && titleCounter) {
        function updateTitleCounter() {
            const length = titleInput.value.length;
            titleCounter.textContent = length;
            
            if (length > 100) {
                titleCounter.style.color = '#dc3545';
            } else if (length > 80) {
                titleCounter.style.color = '#ffc107';
            } else {
                titleCounter.style.color = '';
            }
        }
        
        titleInput.addEventListener('input', updateTitleCounter);
        updateTitleCounter();
    }
    
    // 내용 글자수 카운터
    if (contentTextarea && contentCounter) {
        function updateContentCounter() {
            const length = contentTextarea.value.length;
            contentCounter.textContent = length;
            
            if (length > 5000) {
                contentCounter.style.color = '#dc3545';
            } else if (length > 3000) {
                contentCounter.style.color = '#ffc107';
            } else {
                contentCounter.style.color = '';
            }
        }
        
        contentTextarea.addEventListener('input', updateContentCounter);
        updateContentCounter();
    }
    
    // 폼 제출 시 유효성 검사
    if (noticeForm) {
        noticeForm.addEventListener('submit', function(e) {
            const title = titleInput ? titleInput.value.trim() : '';
            const content = contentTextarea ? contentTextarea.value.trim() : '';
            
            if (!title) {
                e.preventDefault();
                alert('제목을 입력해주세요.');
                if (titleInput) titleInput.focus();
                return;
            }
            
            if (!content) {
                e.preventDefault();
                alert('내용을 입력해주세요.');
                if (contentTextarea) contentTextarea.focus();
                return;
            }
            
            if (title.length > 100) {
                e.preventDefault();
                alert('제목은 100자 이내로 입력해주세요.');
                if (titleInput) titleInput.focus();
                return;
            }
            
            if (content.length > 5000) {
                e.preventDefault();
                alert('내용은 5000자 이내로 입력해주세요.');
                if (contentTextarea) contentTextarea.focus();
                return;
            }
        });
        
        // 변경사항 감지 (페이지 이탈 시 경고만)
        initChangeDetection(titleInput, contentTextarea);
    }
}

/**
 * 변경사항 감지 기능 초기화 (자동 저장 없이 페이지 이탈 시 경고만)
 */
function initChangeDetection(titleInput, contentTextarea) {
    if (!titleInput && !contentTextarea) return;
    
    const originalTitle = titleInput ? titleInput.value : '';
    const originalContent = contentTextarea ? contentTextarea.value : '';
    
    function hasChanges() {
        const currentTitle = titleInput ? titleInput.value : '';
        const currentContent = contentTextarea ? contentTextarea.value : '';
        return currentTitle !== originalTitle || currentContent !== originalContent;
    }
    
    // 페이지 이탈 시 경고
    window.addEventListener('beforeunload', function(e) {
        if (hasChanges()) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
    
    // 취소 버튼 클릭 시 확인
    const cancelButton = document.querySelector('a[href*="notice"]');
    if (cancelButton) {
        cancelButton.addEventListener('click', function(e) {
            if (hasChanges()) {
                if (!confirm('변경사항이 저장되지 않습니다. 정말 나가시겠습니까?')) {
                    e.preventDefault();
                }
            }
        });
    }
}



/**
 * URL 자동 링크 기능 초기화
 */
function initAutoLinkFeature(textarea) {
    if (!textarea) return;
    
    let isProcessing = false;
    
    // URL 패턴 정규식
    const urlPattern = /(https?:\/\/[^\s<>"']+)/gi;
    
    // 텍스트에서 URL을 찾아 링크로 변환
    function convertUrlsToLinks(text) {
        return text.replace(urlPattern, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    }
    
    // 실시간 미리보기 영역 생성
    function createPreviewArea() {
        const previewContainer = document.createElement('div');
        previewContainer.className = 'url-preview-container';
        previewContainer.style.cssText = `
            margin-top: 10px;
            padding: 12px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background-color: #f9fafb;
            font-size: 0.9rem;
            line-height: 1.5;
            display: none;
        `;
        
        const previewLabel = document.createElement('div');
        previewLabel.textContent = '미리보기 (URL이 자동으로 링크됩니다):';
        previewLabel.style.cssText = `
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
            font-size: 0.85rem;
        `;
        
        const previewContent = document.createElement('div');
        previewContent.className = 'url-preview-content';
        previewContent.style.cssText = `
            color: #4b5563;
            white-space: pre-wrap;
            word-break: break-word;
        `;
        
        previewContainer.appendChild(previewLabel);
        previewContainer.appendChild(previewContent);
        
        // textarea 다음에 미리보기 영역 삽입
        textarea.parentNode.insertBefore(previewContainer, textarea.nextSibling);
        
        return { container: previewContainer, content: previewContent };
    }
    
    const preview = createPreviewArea();
    let previewTimer;
    
    // 미리보기 업데이트
    function updatePreview() {
        const text = textarea.value;
        const hasUrls = urlPattern.test(text);
        
        if (hasUrls && text.trim()) {
            const convertedText = convertUrlsToLinks(text);
            preview.content.innerHTML = convertedText;
            preview.container.style.display = 'block';
        } else {
            preview.container.style.display = 'none';
        }
        
        // 정규식 상태 초기화
        urlPattern.lastIndex = 0;
    }
    
    // 입력 이벤트 리스너
    textarea.addEventListener('input', function() {
        if (isProcessing) return;
        
        clearTimeout(previewTimer);
        previewTimer = setTimeout(updatePreview, 300);
    });
    
    // 포커스 이벤트
    textarea.addEventListener('focus', function() {
        if (textarea.value.trim()) {
            updatePreview();
        }
    });
    
    // 초기 미리보기 업데이트
    if (textarea.value.trim()) {
        updatePreview();
    }
    
    // 폼 제출 시 실제 링크 변환 (선택사항)
    const form = textarea.closest('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const text = textarea.value;
            const hasUrls = urlPattern.test(text);
            
            if (hasUrls) {
                // 사용자에게 링크 변환 확인
                const shouldConvert = confirm('텍스트에 URL이 포함되어 있습니다. 자동으로 링크로 변환하시겠습니까?');
                
                if (shouldConvert) {
                    isProcessing = true;
                    textarea.value = convertUrlsToLinks(text);
                    
                    // 글자수 카운터 업데이트
                    const event = new Event('input', { bubbles: true });
                    textarea.dispatchEvent(event);
                }
            }
            
            // 정규식 상태 초기화
            urlPattern.lastIndex = 0;
        });
    }
}

// ===== 검색 관련 기능 =====

/**
 * 검색 기능 초기화
 */
function initSearch() {
    const searchInput = document.querySelector('.search-input');
    const searchForm = document.querySelector('.search-form');
    
    if (!searchInput || !searchForm) return;
    
    // 검색어 하이라이트
    const searchQuery = new URLSearchParams(window.location.search).get('search');
    if (searchQuery) {
        highlightSearchTerms(searchQuery);
    }
    
    // 검색 입력 시 실시간 검증
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        // 너무 짧은 검색어 경고
        if (query.length > 0 && query.length < 2) {
            this.style.borderColor = '#ffc107';
        } else {
            this.style.borderColor = '';
        }
    });
    
    // 검색 폼 제출 시 검증
    searchForm.addEventListener('submit', function(e) {
        const query = searchInput.value.trim();
        
        if (query.length > 0 && query.length < 2) {
            e.preventDefault();
            alert('검색어는 2자 이상 입력해주세요.');
            searchInput.focus();
            return;
        }
        
        if (query.length > 50) {
            e.preventDefault();
            alert('검색어는 50자 이내로 입력해주세요.');
            searchInput.focus();
            return;
        }
    });
}

/**
 * 검색어 하이라이트
 */
function highlightSearchTerms(query) {
    const titleElements = document.querySelectorAll('.notice-item-title');
    
    titleElements.forEach(element => {
        const text = element.textContent;
        const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
        const highlightedText = text.replace(regex, '<mark>$1</mark>');
        
        if (highlightedText !== text) {
            element.innerHTML = highlightedText;
        }
    });
}

/**
 * 정규식 특수문자 이스케이프
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ===== 유틸리티 함수 =====

/**
 * 스크롤 위치 복원
 */
function restoreScrollPosition() {
    // URL 해시가 있으면 해당 위치로 스크롤
    if (window.location.hash) {
        const element = document.querySelector(window.location.hash);
        if (element) {
            setTimeout(() => {
                element.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        }
    }
}

/**
 * 로딩 상태 표시
 */
function showLoading(element) {
    if (!element) return;
    
    element.style.opacity = '0.6';
    element.style.pointerEvents = 'none';
    
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    spinner.innerHTML = '<div class="spinner"></div>';
    element.appendChild(spinner);
}

/**
 * 로딩 상태 해제
 */
function hideLoading(element) {
    if (!element) return;
    
    element.style.opacity = '';
    element.style.pointerEvents = '';
    
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

/**
 * 토스트 메시지 표시
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // 스타일 적용
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '8px',
        color: 'white',
        fontWeight: '600',
        zIndex: '9999',
        transform: 'translateX(100%)',
        transition: 'transform 0.3s ease'
    });
    
    // 타입별 배경색
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    
    toast.style.backgroundColor = colors[type] || colors.info;
    
    document.body.appendChild(toast);
    
    // 애니메이션
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // 자동 제거
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// ===== 초기화 =====

/**
 * DOM 로드 완료 시 초기화
 */
document.addEventListener('DOMContentLoaded', function() {
    // 현재 페이지에 따라 적절한 초기화 실행
    const path = window.location.pathname;
    
    if (path.includes('/comment/') && path.includes('/edit/')) {
        // 댓글 수정 페이지
        initCommentEdit();
    } else if (path.includes('/create/') || path.includes('/edit/')) {
        // 공지사항 작성/수정 페이지
        initNoticeForm();
    } else if (path.includes('/notice/')) {
        // 공지사항 목록 또는 상세 페이지
        initSearch();
        restoreScrollPosition();
    }
    
    // 모든 페이지에서 공통으로 실행
    initCommonFeatures();
});

/**
 * 공통 기능 초기화
 */
function initCommonFeatures() {
    // 폼 제출 시 중복 방지
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        let isSubmitting = false;
        
        form.addEventListener('submit', function(e) {
            if (isSubmitting) {
                e.preventDefault();
                return;
            }
            
            isSubmitting = true;
            
            // 제출 버튼 비활성화
            const submitButtons = form.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                const originalText = button.textContent;
                button.textContent = '처리 중...';
                
                // 5초 후 복원 (네트워크 오류 등에 대비)
                setTimeout(() => {
                    button.disabled = false;
                    button.textContent = originalText;
                    isSubmitting = false;
                }, 5000);
            });
        });
    });
    
    // 외부 링크에 target="_blank" 추가
    const externalLinks = document.querySelectorAll('a[href^="http"]');
    externalLinks.forEach(link => {
        if (!link.hostname.includes(window.location.hostname)) {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
        }
    });
    
    // 이미지 로딩 오류 처리
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        img.addEventListener('error', function() {
            this.style.display = 'none';
        });
    });
}

// ===== 전역 함수 노출 =====
window.toggleReplyForm = toggleReplyForm;
window.deleteComment = deleteComment;
window.showToast = showToast; 