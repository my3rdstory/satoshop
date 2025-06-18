// 공지사항 게시판 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeNoticeBoard();
});

function initializeNoticeBoard() {
    // 댓글 관련 기능 초기화
    initializeComments();
    
    // 폼 검증 초기화
    initializeFormValidation();
    
    // 검색 기능 초기화
    initializeSearch();
    
    // 삭제 확인 초기화
    initializeDeleteConfirm();
}

// 댓글 관련 기능
function initializeComments() {
    // 답글 버튼 클릭 이벤트
    document.querySelectorAll('.reply-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            toggleReplyForm(commentId);
        });
    });
    
    // 답글 취소 버튼
    document.querySelectorAll('.reply-cancel-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            hideReplyForm(commentId);
        });
    });
    
    // 댓글 수정 버튼
    document.querySelectorAll('.comment-edit-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            showEditForm(commentId);
        });
    });
    
    // 댓글 수정 취소 버튼
    document.querySelectorAll('.edit-cancel-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            hideEditForm(commentId);
        });
    });
}

// 답글 폼 토글
function toggleReplyForm(commentId) {
    const replyForm = document.getElementById(`reply-form-${commentId}`);
    if (replyForm) {
        replyForm.classList.toggle('active');
        
        if (replyForm.classList.contains('active')) {
            const textarea = replyForm.querySelector('.reply-textarea');
            if (textarea) {
                textarea.focus();
            }
        }
    }
}

// 답글 폼 숨기기
function hideReplyForm(commentId) {
    const replyForm = document.getElementById(`reply-form-${commentId}`);
    if (replyForm) {
        replyForm.classList.remove('active');
        
        // 텍스트 영역 초기화
        const textarea = replyForm.querySelector('.reply-textarea');
        if (textarea) {
            textarea.value = '';
        }
    }
}

// 댓글 수정 폼 표시
function showEditForm(commentId) {
    const commentContent = document.getElementById(`comment-content-${commentId}`);
    const editForm = document.getElementById(`edit-form-${commentId}`);
    
    if (commentContent && editForm) {
        commentContent.style.display = 'none';
        editForm.style.display = 'block';
        
        const textarea = editForm.querySelector('textarea');
        if (textarea) {
            textarea.focus();
            // 커서를 끝으로 이동
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }
    }
}

// 댓글 수정 폼 숨기기
function hideEditForm(commentId) {
    const commentContent = document.getElementById(`comment-content-${commentId}`);
    const editForm = document.getElementById(`edit-form-${commentId}`);
    
    if (commentContent && editForm) {
        commentContent.style.display = 'block';
        editForm.style.display = 'none';
    }
}

// 폼 검증
function initializeFormValidation() {
    // 공지사항 작성/수정 폼
    const noticeForm = document.getElementById('notice-form');
    if (noticeForm) {
        noticeForm.addEventListener('submit', function(e) {
            if (!validateNoticeForm()) {
                e.preventDefault();
            }
        });
    }
    
    // 댓글 폼
    const commentForms = document.querySelectorAll('.comment-form');
    commentForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const textarea = form.querySelector('textarea');
            if (textarea && !textarea.value.trim()) {
                e.preventDefault();
                showMessage('댓글 내용을 입력해주세요.', 'error');
                textarea.focus();
            }
        });
    });
}

// 공지사항 폼 검증
function validateNoticeForm() {
    const title = document.getElementById('id_title');
    const content = document.getElementById('id_content');
    
    if (!title || !title.value.trim()) {
        showMessage('제목을 입력해주세요.', 'error');
        if (title) title.focus();
        return false;
    }
    
    if (!content || !content.value.trim()) {
        showMessage('내용을 입력해주세요.', 'error');
        if (content) content.focus();
        return false;
    }
    
    if (title.value.trim().length > 200) {
        showMessage('제목은 200자 이하로 입력해주세요.', 'error');
        title.focus();
        return false;
    }
    
    return true;
}

// 검색 기능
function initializeSearch() {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    
    if (searchForm && searchInput) {
        // 검색어 하이라이트
        highlightSearchTerm();
        
        // 검색 입력 시 실시간 검색 (옵션)
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // 실시간 검색 기능 (필요시 구현)
            }, 500);
        });
    }
}

// 검색어 하이라이트
function highlightSearchTerm() {
    const urlParams = new URLSearchParams(window.location.search);
    const searchTerm = urlParams.get('search');
    
    if (searchTerm) {
        const titles = document.querySelectorAll('.notice-item-title');
        titles.forEach(title => {
            const text = title.textContent;
            const highlightedText = text.replace(
                new RegExp(searchTerm, 'gi'),
                `<mark>$&</mark>`
            );
            title.innerHTML = highlightedText;
        });
    }
}

// 삭제 확인
function initializeDeleteConfirm() {
    // 공지사항 삭제
    const deleteButtons = document.querySelectorAll('.delete-notice-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('정말로 이 공지사항을 삭제하시겠습니까?')) {
                e.preventDefault();
            }
        });
    });
    
    // 댓글 삭제
    const commentDeleteForms = document.querySelectorAll('.comment-delete-form');
    commentDeleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('정말로 이 댓글을 삭제하시겠습니까?')) {
                e.preventDefault();
            }
        });
    });
}

// 메시지 표시
function showMessage(message, type = 'info') {
    // 기존 메시지 제거
    const existingMessage = document.querySelector('.notice-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = `notice-message notice-message-${type}`;
    messageDiv.innerHTML = `
        <span>${message}</span>
        <button type="button" class="notice-message-close">&times;</button>
    `;
    
    // 메시지 스타일 추가
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        ${type === 'error' ? 'background-color: #dc3545;' : 
          type === 'success' ? 'background-color: #28a745;' : 
          'background-color: #007bff;'}
    `;
    
    // 닫기 버튼 스타일
    const closeBtn = messageDiv.querySelector('.notice-message-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0;
        line-height: 1;
    `;
    
    // 페이지에 추가
    document.body.appendChild(messageDiv);
    
    // 닫기 버튼 이벤트
    closeBtn.addEventListener('click', () => {
        messageDiv.remove();
    });
    
    // 자동 제거 (5초 후)
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}

// 텍스트 영역 자동 크기 조절
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

// 텍스트 영역에 자동 크기 조절 적용
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('.form-textarea, .comment-textarea, .reply-textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
        
        // 초기 크기 조절
        autoResizeTextarea(textarea);
    });
});

// 스크롤 시 헤더 고정 (선택사항)
function initializeStickyHeader() {
    const header = document.querySelector('.notice-header');
    if (!header) return;
    
    let isSticky = false;
    const headerTop = header.offsetTop;
    
    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset;
        
        if (scrollTop > headerTop && !isSticky) {
            header.style.position = 'fixed';
            header.style.top = '0';
            header.style.left = '0';
            header.style.right = '0';
            header.style.zIndex = '100';
            header.style.backgroundColor = 'white';
            header.style.boxShadow = '0 2px 5px rgba(0,0,0,0.1)';
            isSticky = true;
        } else if (scrollTop <= headerTop && isSticky) {
            header.style.position = 'static';
            header.style.boxShadow = 'none';
            isSticky = false;
        }
    });
}

// 이미지 지연 로딩 (선택사항)
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        images.forEach(img => {
            img.src = img.dataset.src;
        });
    }
}

// 유틸리티 함수들
const NoticeUtils = {
    // 시간 포맷팅
    formatDateTime: function(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        // 1분 미만
        if (diff < 60000) {
            return '방금 전';
        }
        
        // 1시간 미만
        if (diff < 3600000) {
            return `${Math.floor(diff / 60000)}분 전`;
        }
        
        // 24시간 미만
        if (diff < 86400000) {
            return `${Math.floor(diff / 3600000)}시간 전`;
        }
        
        // 그 외
        return date.toLocaleDateString('ko-KR');
    },
    
    // 텍스트 길이 제한
    truncateText: function(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    // HTML 태그 제거
    stripHtml: function(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }
}; 