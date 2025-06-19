/**
 * Document Page JavaScript
 * 문서 페이지에서 사용되는 스크립트
 */

class DocumentPage {
    constructor() {
        this.init();
    }

    init() {
        this.setupMarkdownRenderer();
        this.setupScrollToTop();
        this.setupPrintButton();
    }

    /**
     * 마크다운 렌더링 추가 처리
     */
    setupMarkdownRenderer() {
        const contentElement = document.querySelector('.document-content');
        if (contentElement && window.MarkdownRenderer) {
            // 이미 서버에서 렌더링된 HTML이지만, 클라이언트 사이드 추가 처리가 필요한 경우
            // MarkdownRenderer.render(contentElement);
            
            // 외부 링크에 target="_blank" 추가
            this.processExternalLinks(contentElement);
            
            // 테이블에 반응형 래퍼 추가
            this.makeTablesResponsive(contentElement);
        }
    }

    /**
     * 외부 링크 처리
     */
    processExternalLinks(container) {
        const links = container.querySelectorAll('a[href^="http"]');
        links.forEach(link => {
            if (!link.hostname.includes(window.location.hostname)) {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
                
                // 외부 링크 아이콘 추가
                if (!link.querySelector('.external-link-icon')) {
                    const icon = document.createElement('i');
                    icon.className = 'fas fa-external-link-alt external-link-icon ml-1';
                    icon.style.fontSize = '0.75em';
                    link.appendChild(icon);
                }
            }
        });
    }

    /**
     * 테이블 반응형 처리
     */
    makeTablesResponsive(container) {
        const tables = container.querySelectorAll('table');
        tables.forEach(table => {
            if (!table.parentElement.classList.contains('table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive overflow-x-auto';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
    }

    /**
     * 맨 위로 스크롤 버튼
     */
    setupScrollToTop() {
        // 스크롤 버튼 생성
        const scrollButton = document.createElement('button');
        scrollButton.innerHTML = '<i class="fas fa-arrow-up"></i>';
        scrollButton.className = 'fixed bottom-6 right-6 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-all duration-300 opacity-0 invisible z-50';
        scrollButton.id = 'scrollToTop';
        scrollButton.setAttribute('aria-label', '맨 위로 이동');
        document.body.appendChild(scrollButton);

        // 스크롤 이벤트 리스너
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                if (window.pageYOffset > 300) {
                    scrollButton.classList.remove('opacity-0', 'invisible');
                } else {
                    scrollButton.classList.add('opacity-0', 'invisible');
                }
            }, 10);
        });

        // 클릭 이벤트
        scrollButton.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    /**
     * 인쇄 버튼 기능
     */
    setupPrintButton() {
        // 인쇄 버튼이 있다면 이벤트 추가
        const printButton = document.getElementById('printDocument');
        if (printButton) {
            printButton.addEventListener('click', () => {
                window.print();
            });
        }

        // 인쇄 시 스타일 최적화
        window.addEventListener('beforeprint', () => {
            document.body.classList.add('printing');
        });

        window.addEventListener('afterprint', () => {
            document.body.classList.remove('printing');
        });
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    new DocumentPage();
});

// 문서 링크 클릭 시 부드러운 스크롤
document.addEventListener('click', function(e) {
    const link = e.target.closest('a[href^="#"]');
    if (link) {
        e.preventDefault();
        const targetId = link.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
}); 