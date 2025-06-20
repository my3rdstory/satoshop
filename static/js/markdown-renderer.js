/**
 * Markdown Renderer - 마크다운 텍스트를 HTML로 변환하는 유틸리티
 * 
 * 사용법:
 * 1. HTML에서 마크다운 텍스트가 있는 요소에 'markdown-content' 클래스 추가
 * 2. MarkdownRenderer.renderAll() 호출하여 모든 마크다운 요소 렌더링
 * 3. 또는 MarkdownRenderer.render(element) 호출하여 특정 요소만 렌더링
 */

// 중복 로드 방지 - IIFE 사용
(function() {
  // 이미 로드되어 있으면 건너뛰기
  if (typeof window.MarkdownRenderer !== 'undefined') {
    return;
  }

class MarkdownRenderer {
  // 허용되는 이미지 확장자 (Django settings에서 가져올 수 있지만 여기서는 하드코딩)
  static imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'];
  
  // 유튜브 URL 패턴
  static youtubePatterns = [
    /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})/
  ];

  /**
   * 페이지의 모든 .markdown-content 요소를 찾아서 마크다운 렌더링
   */
  static renderAll() {
    const markdownElements = document.querySelectorAll('.markdown-content');
    markdownElements.forEach(element => {
      this.render(element);
    });
  }

  /**
   * 특정 요소의 마크다운 텍스트를 HTML로 렌더링
   * @param {HTMLElement} element - 마크다운 텍스트가 포함된 요소
   */
  static render(element) {
    if (!element) return;

    const markdownText = element.textContent || element.innerText;
    if (!markdownText.trim()) return;

    let renderedHtml;

    // marked 라이브러리가 있으면 사용하되, 추가 처리도 적용
    if (typeof marked !== 'undefined') {
      // marked 설정
      marked.setOptions({
        breaks: true,
        gfm: true,
        sanitize: false,
        smartLists: true,
        smartypants: false
      });
      
      renderedHtml = marked.parse(markdownText.trim());
      // marked로 처리한 후에도 추가 기능들 적용
      renderedHtml = this.applyAdditionalProcessing(renderedHtml);
    } else {
      renderedHtml = this.simpleMarkdownParse(markdownText);
    }

    element.innerHTML = renderedHtml;
  }

  /**
   * marked 라이브러리로 처리된 HTML에 추가 기능 적용
   * @param {string} html - marked로 처리된 HTML
   * @returns {string} - 추가 처리된 HTML
   */
  static applyAdditionalProcessing(html) {
    return html
      // 유튜브 링크를 임베드로 변환
      .replace(/<a[^>]*href="(https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})(?:[^"]*)?)"[^>]*>.*?<\/a>/g, (match, fullUrl, videoId) => {
        return this.renderYouTubeEmbed(videoId);
      })
      
      // 이미지 URL을 반응형 이미지로 변환
      .replace(/<a[^>]*href="(https?:\/\/[^"]+\.(?:jpg|jpeg|png|gif|webp|svg|bmp|ico)(?:\?[^"]*)?)"[^>]*>.*?<\/a>/gi, (match, imageUrl) => {
        const filename = imageUrl.split('/').pop().split('?')[0];
        return this.renderImage(filename, imageUrl);
      })
      
      // 일반 링크에 새 탭 속성 추가
      .replace(/<a([^>]*href="https?:\/\/[^"]*"[^>]*)>/g, '<a$1 target="_blank" rel="noopener noreferrer">')
      
      // 이미지를 반응형으로 변경
      .replace(/<img([^>]*class="[^"]*")([^>]*)>/g, '<img$1 w-full h-auto object-cover"$2>')
      .replace(/<img([^>]*(?!class=)[^>]*)>/g, '<img$1 class="w-full h-auto rounded-lg shadow-sm object-cover">');
  }

  /**
   * 간단한 마크다운 파서 (marked 라이브러리가 없을 때 사용)
   * @param {string} text - 마크다운 텍스트
   * @returns {string} - 변환된 HTML
   */
  static simpleMarkdownParse(text) {
    return text
      // 헤더 처리 (6단계까지)
      .replace(/^###### (.*$)/gim, '<h6>$1</h6>')
      .replace(/^##### (.*$)/gim, '<h5>$1</h5>')
      .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      
      // 강조 처리
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/~~(.*?)~~/g, '<del>$1</del>')
      
      // 유튜브 링크 처리 (링크 처리보다 먼저 해야 함)
      .replace(/(https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})(?:\S*)?)/g, (match, fullUrl, videoId) => {
        return this.renderYouTubeEmbed(videoId);
      })
      
      // 이미지 URL 자동 감지 및 변환 (마크다운 이미지 문법보다 먼저 처리)
      .replace(/(https?:\/\/[^\s]+\.(?:jpg|jpeg|png|gif|webp|svg|bmp|ico)(?:\?[^\s]*)?)/gi, (match, imageUrl) => {
        const filename = imageUrl.split('/').pop().split('?')[0];
        return this.renderImage(filename, imageUrl.trim());
      })
      
      // 마크다운 이미지 처리 (오류 처리 포함)
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
        return this.renderImage(alt, src);
      })
      
      // 일반 링크 처리 (마크다운 링크)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
        return this.renderLink(text, url);
      })
      
      // 일반 URL 자동 링크 처리 (http/https로 시작하는 URL)
      .replace(/(https?:\/\/[^\s]+)/g, (match, url) => {
        // 이미 처리된 유튜브나 이미지 URL은 제외
        if (this.isYouTubeUrl(url.trim()) || this.isImageUrl(url.trim())) {
          return match;
        }
        return this.renderLink(url.trim(), url.trim());
      })
      
      // 인라인 코드 처리
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      
      // 코드 블록 처리 (간단한 버전)
      .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>')
      
      // 인용구 처리
      .replace(/^> (.+)$/gim, '<blockquote>$1</blockquote>')
      
      // 수평선 처리
      .replace(/^---$/gim, '<hr>')
      .replace(/^\*\*\*$/gim, '<hr>')
      
      // 리스트 처리
      .replace(/^\* (.+)$/gim, '<li>$1</li>')
      .replace(/^\- (.+)$/gim, '<li>$1</li>')
      .replace(/^\+ (.+)$/gim, '<li>$1</li>')
      .replace(/^(\d+)\. (.+)$/gim, '<li>$2</li>')
      
      // 리스트를 ul/ol 태그로 감싸기
      .replace(/(<li>.*?<\/li>)/gs, (match) => {
        // 연속된 li 태그들을 ul로 감싸기
        return `<ul>${match}</ul>`;
      })
      
      // 줄바꿈 처리
      .replace(/\n\n/g, '</p><p>')
      .replace(/^(?!<[hul]|<\/[hul]|<blockquote|<hr|<pre|<div|<img)(.+)$/gm, '<p>$1</p>')
      
      // 빈 p 태그 제거
      .replace(/<p><\/p>/g, '')
      .replace(/<p>\s*<\/p>/g, '');
  }

  /**
   * 이미지 렌더링 (오류 처리 포함, 반응형)
   * @param {string} alt - 이미지 alt 텍스트
   * @param {string} src - 이미지 URL
   * @returns {string} - 이미지 HTML 또는 플레이스홀더
   */
  static renderImage(alt, src) {
    // 접근 불가능한 플레이스홀더 URL 처리
    if (src.includes('via.placeholder.com') || 
        src.includes('placeholder') || 
        src.includes('example.com')) {
      return `<div class="bg-gray-200 dark:bg-gray-700 border-2 border-dashed border-gray-400 dark:border-gray-500 rounded-lg p-4 text-center text-gray-500 dark:text-gray-400 my-4">
        <i class="fas fa-image text-2xl mb-2"></i>
        <p class="text-sm font-medium">이미지: ${alt || '이미지'}</p>
        <p class="text-xs text-gray-400 dark:text-gray-500 break-all">${src}</p>
      </div>`;
    }

    // 반응형 이미지 (꽉 차게, 오류 처리 포함)
    return `<div class="my-4 w-full">
      <img src="${src}" alt="${alt}" class="w-full h-auto rounded-lg shadow-sm object-cover" 
           onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
      <div class="bg-gray-200 dark:bg-gray-700 border-2 border-dashed border-gray-400 dark:border-gray-500 rounded-lg p-4 text-center text-gray-500 dark:text-gray-400" style="display:none;">
        <i class="fas fa-exclamation-triangle text-2xl mb-2 text-yellow-500"></i>
        <p class="text-sm font-medium">이미지 로드 실패</p>
        <p class="text-xs">이미지: ${alt || '이미지'}</p>
        <p class="text-xs text-gray-400 dark:text-gray-500 break-all">${src}</p>
      </div>
    </div>`;
  }

  /**
   * 링크 렌더링 (새 탭에서 열기)
   * @param {string} text - 링크 텍스트
   * @param {string} url - 링크 URL
   * @returns {string} - 링크 HTML
   */
  static renderLink(text, url) {
    // URL이 http/https로 시작하지 않으면 추가
    const fullUrl = url.startsWith('http') ? url : `https://${url}`;
    
    return `<a href="${fullUrl}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline">${text}</a>`;
  }

  /**
   * 유튜브 임베드 렌더링 (반응형)
   * @param {string} videoId - 유튜브 비디오 ID
   * @returns {string} - 유튜브 임베드 HTML
   */
  static renderYouTubeEmbed(videoId) {
    return `<div class="my-4 w-full">
      <div class="relative w-full h-0 pb-[56.25%] rounded-lg overflow-hidden shadow-lg">
        <iframe 
          class="absolute top-0 left-0 w-full h-full"
          src="https://www.youtube.com/embed/${videoId}"
          title="YouTube video player"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen>
        </iframe>
      </div>
    </div>`;
  }

  /**
   * URL이 유튜브 URL인지 확인
   * @param {string} url - 확인할 URL
   * @returns {boolean} - 유튜브 URL 여부
   */
  static isYouTubeUrl(url) {
    return this.youtubePatterns.some(pattern => pattern.test(url));
  }

  /**
   * URL이 이미지 URL인지 확인
   * @param {string} url - 확인할 URL
   * @returns {boolean} - 이미지 URL 여부
   */
  static isImageUrl(url) {
    const extension = url.split('.').pop().split('?')[0].toLowerCase();
    return this.imageExtensions.includes(extension);
  }

  /**
   * 특정 셀렉터의 요소들을 마크다운 렌더링
   * @param {string} selector - CSS 셀렉터
   */
  static renderBySelector(selector) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(element => {
      this.render(element);
    });
  }

  /**
   * 마크다운 텍스트를 HTML로 변환 (요소 없이 텍스트만 변환)
   * @param {string} markdownText - 마크다운 텍스트
   * @returns {string} - 변환된 HTML
   */
  static parseText(markdownText) {
    if (typeof marked !== 'undefined') {
      const html = marked.parse(markdownText);
      return this.applyAdditionalProcessing(html);
    } else {
      return this.simpleMarkdownParse(markdownText);
    }
  }
}

// DOM이 로드되면 자동으로 모든 마크다운 요소 렌더링
document.addEventListener('DOMContentLoaded', function() {
  MarkdownRenderer.renderAll();
});

// 전역에서 사용할 수 있도록 window 객체에 추가
window.MarkdownRenderer = MarkdownRenderer;

})(); // IIFE 닫기 