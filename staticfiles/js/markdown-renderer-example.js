/**
 * MarkdownRenderer 사용법 예제
 */

// 1. 페이지 로드 시 자동으로 모든 .markdown-content 요소 렌더링
// (별도 코드 불필요 - MarkdownRenderer가 자동으로 처리)

// 2. 특정 요소만 렌더링
document.addEventListener('DOMContentLoaded', function() {
  const specificElement = document.getElementById('my-markdown');
  if (specificElement) {
    MarkdownRenderer.render(specificElement);
  }
});

// 3. 동적으로 추가된 마크다운 요소 렌더링
function addMarkdownContent() {
  const container = document.getElementById('dynamic-container');
  const newElement = document.createElement('div');
  newElement.className = 'markdown-content';
  newElement.textContent = '# 동적 제목\n\n**굵은 텍스트**와 *기울임 텍스트*';
  
  container.appendChild(newElement);
  
  // 새로 추가된 요소 렌더링
  MarkdownRenderer.render(newElement);
}

// 4. 특정 셀렉터로 렌더링
function renderCustomSelector() {
  MarkdownRenderer.renderBySelector('.custom-markdown');
}

// 5. 텍스트만 변환 (요소 없이)
function convertTextOnly() {
  const markdownText = '## 제목\n\n이것은 **마크다운** 텍스트입니다.';
  const htmlResult = MarkdownRenderer.parseText(markdownText);
  console.log(htmlResult);
  return htmlResult;
}

// 6. AJAX로 받은 마크다운 데이터 처리
function handleAjaxMarkdown(markdownData) {
  const container = document.getElementById('ajax-content');
  container.innerHTML = `<div class="markdown-content">${markdownData}</div>`;
  
  // 새로 추가된 마크다운 렌더링
  MarkdownRenderer.renderBySelector('#ajax-content .markdown-content');
}

// 7. 폼에서 입력받은 마크다운 미리보기
function previewMarkdown() {
  const textarea = document.getElementById('markdown-input');
  const preview = document.getElementById('markdown-preview');
  
  if (textarea && preview) {
    const markdownText = textarea.value;
    const htmlResult = MarkdownRenderer.parseText(markdownText);
    preview.innerHTML = htmlResult;
  }
}

// 8. 실시간 마크다운 에디터
function setupLiveMarkdownEditor() {
  const textarea = document.getElementById('markdown-editor');
  const preview = document.getElementById('live-preview');
  
  if (textarea && preview) {
    textarea.addEventListener('input', function() {
      const markdownText = this.value;
      const htmlResult = MarkdownRenderer.parseText(markdownText);
      preview.innerHTML = htmlResult;
    });
  }
}

// HTML 예제:
/*
<!-- CSS 포함 (필수) -->
<link rel="stylesheet" href="{% static 'css/markdown-renderer.css' %}">

<!-- 기본 사용법 -->
<div class="markdown-content prose">
# 제목
**굵은 텍스트**
*기울임 텍스트*

## 링크 예제
[마크다운 링크](https://example.com)
https://www.google.com (자동 링크)

## 이미지 예제
![마크다운 이미지](https://example.com/image.jpg)
https://example.com/auto-image.png (자동 이미지)

## 유튜브 예제
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/dQw4w9WgXcQ

## 코드 예제
`인라인 코드`

```javascript
// 코드 블록
function hello() {
  console.log("Hello World!");
}
```

## 인용구 예제
> 이것은 인용구입니다.
> 여러 줄로 작성할 수 있습니다.

## 리스트 예제
- 항목 1
- 항목 2
  - 하위 항목 1
  - 하위 항목 2

1. 번호 항목 1
2. 번호 항목 2
</div>

<!-- 특정 ID로 렌더링 -->
<div id="my-markdown" class="markdown-content">
## 특정 요소
이 요소는 특별히 렌더링됩니다.
</div>

<!-- 커스텀 클래스로 렌더링 -->
<div class="custom-markdown">
### 커스텀 클래스
이 요소는 커스텀 셀렉터로 렌더링됩니다.
</div>

<!-- 동적 컨테이너 -->
<div id="dynamic-container"></div>

<!-- AJAX 컨텐츠 -->
<div id="ajax-content"></div>

<!-- 마크다운 에디터 -->
<div class="grid grid-cols-2 gap-4">
  <div>
    <textarea id="markdown-editor" class="w-full h-64 p-4 border rounded"></textarea>
  </div>
  <div>
    <div id="live-preview" class="w-full h-64 p-4 border rounded prose"></div>
  </div>
</div>
*/ 