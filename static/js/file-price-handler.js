// 파일 앱 가격 및 할인 처리 공통 함수

// 환율 관련 변수
let currentExchangeRate = null;

// 가격 타입 선택 함수
window.selectPriceType = function(type) {
    // 모든 카드 초기화
    document.querySelectorAll('.price-type-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // 선택된 카드 활성화
    const selectedCard = document.querySelector(`[onclick="selectPriceType('${type}')"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    // 라디오 버튼 선택
    const radioButton = document.getElementById(`price_display_${type}`);
    if (radioButton) {
        radioButton.checked = true;
    }
    
    // 가격 입력 필드 표시/숨김
    const satsPriceSection = document.getElementById('sats-price-section');
    const krwPriceSection = document.getElementById('krw-price-section');
    
    satsPriceSection.style.display = 'none';
    krwPriceSection.style.display = 'none';
    
    if (type === 'sats') {
        satsPriceSection.style.display = 'block';
    } else if (type === 'krw') {
        krwPriceSection.style.display = 'block';
        loadExchangeRate();
    }
    
}


// 환율 정보 로드
async function loadExchangeRate() {
    try {
        const response = await fetch('/api/exchange-rate/');
        const data = await response.json();
        
        if (data.success) {
            currentExchangeRate = data.btc_krw_rate;
            updatePriceConversion();
        }
    } catch (error) {
        console.error('환율 API 호출 실패:', error);
    }
}

// 가격 변환 정보 업데이트
function updatePriceConversion() {
    const priceKrwInput = document.getElementById('id_price_krw');
    if (!priceKrwInput) return;
    
    const krwValue = parseFloat(priceKrwInput.value);
    const exchangeInfo = document.querySelector('#krw-price-section .exchange-info');
    const convertedAmount = document.querySelector('#krw-price-section .converted-amount');
    
    if (exchangeInfo && convertedAmount) {
        if (krwValue && krwValue > 0 && currentExchangeRate) {
            const btcAmount = krwValue / currentExchangeRate;
            const satsAmount = Math.round(btcAmount * 100_000_000);
            convertedAmount.textContent = `약 ${satsAmount.toLocaleString()} sats`;
            exchangeInfo.classList.remove('hidden');
        } else {
            exchangeInfo.classList.add('hidden');
        }
    }
}

// 초기화 함수
window.initializeFilePriceHandler = function() {
    // 원화 입력 시 실시간 변환
    const priceKrwInput = document.getElementById('id_price_krw');
    if (priceKrwInput) {
        priceKrwInput.addEventListener('input', updatePriceConversion);
    }
    
}