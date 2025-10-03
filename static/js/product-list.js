// 상품 목록 페이지 JavaScript

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 상품 리스트 페이지 초기화
    
    // 상품 카드 호버 효과 초기화
    initProductCardEffects();
    
    // 이미지 로딩 처리
    initImageLoading();
    
    // 상품 카드 클릭 이벤트
    initProductCardClicks();

    // 카테고리 내비게이션 초기화
    initCategoryNavigation();
});

// 상품 카드 호버 효과
function initProductCardEffects() {
    console.log('[category-filter] initProductCardEffects invoked');
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        // 호버 시 그림자 효과 강화
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-2xl');
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-2xl');
            this.style.transform = 'translateY(0)';
        });
    });
}

// 이미지 로딩 처리
function initImageLoading() {
    console.log('[category-filter] initImageLoading invoked');
    const productImages = document.querySelectorAll('.product-card img');
    
    productImages.forEach(img => {
        // 이미지 로딩 중 스켈레톤 효과
        img.addEventListener('load', function() {
            this.classList.add('loaded');
        });
        
        // 이미지 로딩 실패 시 기본 이미지 표시
        img.addEventListener('error', function() {
            this.src = '/static/images/no-image.png';
            this.alt = '이미지를 불러올 수 없습니다';
        });
    });
}

// 상품 카드 클릭 이벤트
function initProductCardClicks() {
    console.log('[category-filter] initProductCardClicks invoked');
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        // 카드 전체 클릭 시 상품 상세 페이지로 이동
        card.addEventListener('click', function(e) {
            // 버튼이나 링크를 클릭한 경우는 제외
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || 
                e.target.closest('a') || e.target.closest('button')) {
                return;
            }
            
            // 상품 링크 찾기
            const productLink = this.querySelector('a[href*="product"]');
            if (productLink) {
                window.location.href = productLink.href;
            }
        });
    });
}

// 카테고리 빠른 이동 내비게이션
function initCategoryNavigation() {
    const root = document.getElementById('productListRoot');
    if (!root) {
        console.warn('[category-filter] initCategoryNavigation: root element not found');
        return;
    }

    console.log('[category-filter] initCategoryNavigation invoked', {
        fetchUrl: root.dataset.categoryUrl,
        isPublic: root.dataset.isPublic,
        defaultCategoryId: root.dataset.defaultCategoryId,
    });

    const fetchUrl = root.dataset.categoryUrl;
    const pills = Array.from(root.querySelectorAll('.category-pill'));
    const sectionsContainer = document.getElementById('categorySectionsContainer');
    if (!fetchUrl || !pills.length || !sectionsContainer) {
        console.warn('[category-filter] initCategoryNavigation: required elements missing', {
            fetchUrlPresent: Boolean(fetchUrl),
            pillsCount: pills.length,
            hasSectionsContainer: Boolean(sectionsContainer),
        });
        return;
    }

    const loadingIndicator = document.getElementById('categoryLoadingIndicator');
    const supportsAbort = typeof AbortController !== 'undefined';

    let activeCategoryId = '';
    let abortController = null;

    const setActivePillById = (categoryId) => {
        pills.forEach((pill) => {
            const pillId = pill.dataset.categoryId || '';
            if (pillId === categoryId) {
                pill.classList.add('category-pill--active');
                pill.setAttribute('aria-pressed', 'true');
            } else {
                pill.classList.remove('category-pill--active');
                pill.setAttribute('aria-pressed', 'false');
            }
        });
    };

    const showLoading = (visible) => {
        if (!loadingIndicator) return;
        loadingIndicator.classList.toggle('hidden', !visible);
    };

    const updateCounts = (counts, totalCount) => {
        if (!counts) return;
        pills.forEach((pill) => {
            const countElement = pill.querySelector('.category-pill__count');
            if (!countElement) {
                return;
            }

            const pillId = pill.dataset.categoryId || '';
            if (!pillId) {
                if (typeof totalCount === 'number') {
                    countElement.textContent = totalCount;
                }
                return;
            }

            if (Object.prototype.hasOwnProperty.call(counts, pillId)) {
                countElement.textContent = counts[pillId];
            }
        });
    };

    const fetchCategory = (categoryId, previousCategoryId) => {
        console.log('[category-filter] fetchCategory invoked', {
            categoryId,
            previousCategoryId,
            supportsAbort,
            abortControllerExists: Boolean(abortController),
        });

        if (supportsAbort && abortController) {
            console.log('[category-filter] aborting previous request');
            abortController.abort();
        }
        abortController = supportsAbort ? new AbortController() : null;

        showLoading(true);

        const url = new URL(fetchUrl, window.location.origin);
        if (categoryId) {
            url.searchParams.set('category_id', categoryId);
        }

        const fetchOptions = {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        };
        if (abortController) {
            fetchOptions.signal = abortController.signal;
        }

        console.log('[category-filter] 요청 시작', {
            categoryId: categoryId || null,
            requestUrl: url.toString(),
        });

        fetch(url.toString(), fetchOptions)
            .then((response) => {
                if (!response.ok) {
                    console.error('[category-filter] 응답 오류 상태', response.status, response.statusText);
                    throw new Error('카테고리 데이터를 불러오지 못했습니다.');
                }
                return response.json();
            })
            .then((data) => {
                if (!data.success) {
                    console.error('[category-filter] 응답 실패', data);
                    throw new Error(data.error || '카테고리 데이터를 불러오지 못했습니다.');
                }

                sectionsContainer.innerHTML = data.html || '';
                activeCategoryId = data.categoryId === null ? '' : String(data.categoryId);
                setActivePillById(activeCategoryId);
                updateCounts(data.counts || {}, data.totalCount);

                // 새로 로드한 상품 카드에 이벤트 재연결
                initProductCardEffects();
                initImageLoading();
                initProductCardClicks();

                console.log('[category-filter] 로드 완료', {
                    activeCategoryId,
                    totalCount: data.totalCount,
                    counts: data.counts,
                });
            })
            .catch((error) => {
                if (error.name === 'AbortError') {
                    return;
                }
                console.error('[category-filter] 로드 실패', error);
                window.alert(error.message || '카테고리 데이터를 불러오지 못했습니다.');
                activeCategoryId = previousCategoryId;
                setActivePillById(previousCategoryId);
            })
            .finally(() => {
                console.log('[category-filter] 요청 종료');
                showLoading(false);
            });
    };

    const handlePillClick = (event) => {
        event.preventDefault();
        const target = event.currentTarget;
        const categoryId = target.dataset.categoryId || '';

        console.log('[category-filter] pill click', { categoryId });

        if (categoryId === activeCategoryId) {
            console.log('[category-filter] 동일 카테고리 클릭 – 요청 생략');
            return;
        }

        const previousCategoryId = activeCategoryId;
        activeCategoryId = categoryId;
        setActivePillById(categoryId);
        fetchCategory(categoryId, previousCategoryId);
    };

    pills.forEach((pill) => {
        pill.addEventListener('click', handlePillClick);
    });

    const hasAllPill = pills.some((pill) => (pill.dataset.categoryId || '') === '');
    if (hasAllPill) {
        activeCategoryId = '';
    } else if (root.dataset.defaultCategoryId) {
        activeCategoryId = String(root.dataset.defaultCategoryId);
    }

    console.log('[category-filter] 초기화 완료', { activeCategoryId });
    setActivePillById(activeCategoryId);
}

// 상품 상태 표시 업데이트
function updateProductStatus(productId, isActive) {
    const productCard = document.querySelector(`[data-product-id="${productId}"]`);
    if (!productCard) return;
    
    const statusBadge = productCard.querySelector('.status-badge');
    const actionButtons = productCard.querySelectorAll('.action-button');
    
    if (isActive) {
        productCard.classList.remove('inactive');
        if (statusBadge) statusBadge.style.display = 'none';
        actionButtons.forEach(btn => btn.disabled = false);
    } else {
        productCard.classList.add('inactive');
        if (statusBadge) statusBadge.style.display = 'block';
        actionButtons.forEach(btn => btn.disabled = true);
    }
}

// 가격 포맷팅 함수
function formatPrice(price, currency = 'sats') {
    if (currency === 'krw') {
        return new Intl.NumberFormat('ko-KR').format(price) + ' 원';
    } else {
        return new Intl.NumberFormat('ko-KR').format(price) + ' sats';
    }
}

// 할인율 계산
function calculateDiscountRate(originalPrice, discountedPrice) {
    if (originalPrice <= 0) return 0;
    return Math.round(((originalPrice - discountedPrice) / originalPrice) * 100);
}

// 상품 검색/필터링 (향후 확장용)
function filterProducts(searchTerm) {
    const productCards = document.querySelectorAll('.product-card');
    const searchLower = searchTerm.toLowerCase();
    
    productCards.forEach(card => {
        const title = card.querySelector('h4')?.textContent.toLowerCase() || '';
        const description = card.querySelector('.description')?.textContent.toLowerCase() || '';
        
        if (title.includes(searchLower) || description.includes(searchLower)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// 상품 정렬 (향후 확장용)
function sortProducts(sortBy) {
    const container = document.querySelector('.grid');
    if (!container) return;
    
    const cards = Array.from(container.querySelectorAll('.product-card'));
    
    cards.sort((a, b) => {
        switch (sortBy) {
            case 'price-low':
                return getProductPrice(a) - getProductPrice(b);
            case 'price-high':
                return getProductPrice(b) - getProductPrice(a);
            case 'name':
                return getProductName(a).localeCompare(getProductName(b));
            default:
                return 0;
        }
    });
    
    // 정렬된 순서로 다시 배치
    cards.forEach(card => container.appendChild(card));
}

// 헬퍼 함수들
function getProductPrice(card) {
    const priceText = card.querySelector('.price')?.textContent || '0';
    return parseInt(priceText.replace(/[^\d]/g, '')) || 0;
}

function getProductName(card) {
    return card.querySelector('h4')?.textContent || '';
}

// 성공 메시지 표시
function showSuccessMessage(message) {
    // 기존 메시지가 있다면 제거
    const existingMessage = document.querySelector('.success-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = 'success-message fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300';
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateX(100%)';
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

// 에러 메시지 표시
function showErrorMessage(message) {
    // 기존 메시지가 있다면 제거
    const existingMessage = document.querySelector('.error-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = 'error-message fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300';
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 5초 후 자동 제거
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateX(100%)';
        setTimeout(() => messageDiv.remove(), 300);
    }, 5000);
} 
