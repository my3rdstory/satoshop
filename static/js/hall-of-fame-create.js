let selectedFile = null;

function generateYearTags() {
    const yearTagsContainer = document.getElementById('yearTags');
    
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tag-btn year-tag';
    btn.dataset.year = 2025;
    btn.textContent = '2025년';
    btn.onclick = () => selectYear(2025);
    yearTagsContainer.appendChild(btn);
}

function selectYear(year) {
    document.querySelectorAll('.year-tag').forEach(tag => {
        tag.classList.remove('selected');
    });
    
    const selectedTag = document.querySelector(`.year-tag[data-year="${year}"]`);
    if (selectedTag) {
        selectedTag.classList.add('selected');
        document.getElementById('selectedYear').value = year;
    }
}

function selectMonth(month) {
    document.querySelectorAll('.month-tag').forEach(tag => {
        tag.classList.remove('selected');
    });
    
    const selectedTag = document.querySelector(`.month-tag[data-month="${month}"]`);
    if (selectedTag) {
        selectedTag.classList.add('selected');
        document.getElementById('selectedMonth').value = month;
    }
}

function handleImageSelect(file) {
    if (file.size > 10 * 1024 * 1024) {
        alert('파일 크기는 10MB를 초과할 수 없습니다.');
        return;
    }
    
    if (!file.type.startsWith('image/')) {
        alert('이미지 파일만 업로드 가능합니다.');
        return;
    }
    
    selectedFile = file;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('imagePreview').src = e.target.result;
        document.getElementById('imagePreviewContainer').classList.add('show');
        document.getElementById('imageUploadArea').style.display = 'none';
        
        const fileSize = (file.size / 1024).toFixed(2);
        document.getElementById('imageInfo').innerHTML = `
            <strong>파일명:</strong> ${file.name}<br>
            <strong>크기:</strong> ${fileSize} KB<br>
            <strong>타입:</strong> ${file.type}
        `;
    };
    reader.readAsDataURL(file);
    
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    document.getElementById('imageInput').files = dataTransfer.files;
}

function removeImage() {
    selectedFile = null;
    document.getElementById('imageInput').value = '';
    document.getElementById('imagePreviewContainer').classList.remove('show');
    document.getElementById('imageUploadArea').style.display = 'block';
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.month-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            selectMonth(tag.dataset.month);
        });
    });

    generateYearTags();

    const imageUploadArea = document.getElementById('imageUploadArea');
    const imageInput = document.getElementById('imageInput');

    imageUploadArea.addEventListener('click', () => {
        imageInput.click();
    });

    imageUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        imageUploadArea.classList.add('dragover');
    });

    imageUploadArea.addEventListener('dragleave', () => {
        imageUploadArea.classList.remove('dragover');
    });

    imageUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        imageUploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            handleImageSelect(files[0]);
        }
    });

    imageInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleImageSelect(e.target.files[0]);
        }
    });

    document.getElementById('hallOfFameForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!document.getElementById('selectedYear').value) {
            alert('년도를 선택해주세요.');
            return;
        }
        
        if (!document.getElementById('selectedMonth').value) {
            alert('월을 선택해주세요.');
            return;
        }
        
        if (!selectedFile) {
            alert('이미지를 업로드해주세요.');
            return;
        }
        
        document.getElementById('processingOverlay').classList.add('show');
        document.getElementById('submitBtn').disabled = true;
        
        this.submit();
    });

    let formChanged = false;
    document.querySelectorAll('input, textarea').forEach(element => {
        element.addEventListener('change', () => {
            formChanged = true;
        });
    });

    window.addEventListener('beforeunload', (e) => {
        if (formChanged && !document.getElementById('processingOverlay').classList.contains('show')) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});
