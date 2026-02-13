/**
 * 사용자 로컬 시간대 변환 유틸리티
 * Django 템플릿에서 서버 시간으로 렌더링된 날짜/시간을 사용자 로컬 시간대로 변환
 */

// 시간대 변환 함수
function convertToLocalTime(dateString, format = 'datetime') {
    try {
        // Django 날짜 형식 파싱 (예: "2024년 1월 15일 14:30")
        const koreanDateRegex = /(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2}):(\d{2})/;
        const match = dateString.match(koreanDateRegex);
        
        if (!match) {
            return dateString; // 파싱 실패 시 원본 반환
        }
        
        const [, year, month, day, hour, minute] = match;
        
        // 한국 시간대로 Date 객체 생성
        const koreaTime = new Date();
        koreaTime.setFullYear(parseInt(year), parseInt(month) - 1, parseInt(day));
        koreaTime.setHours(parseInt(hour), parseInt(minute), 0, 0);
        
        // 한국 시간대 오프셋 고려 (UTC+9)
        const koreaOffset = 9 * 60; // 분 단위
        const localOffset = koreaTime.getTimezoneOffset(); // 로컬 시간대 오프셋
        
        // 시간대 차이 계산하여 로컬 시간으로 변환
        const timeDiff = (koreaOffset + localOffset) * 60 * 1000; // 밀리초 단위
        const localTime = new Date(koreaTime.getTime() - timeDiff);
        
        // 포맷에 따라 반환
        if (format === 'date') {
            const year = localTime.getFullYear();
            const month = String(localTime.getMonth() + 1).padStart(2, '0');
            const day = String(localTime.getDate()).padStart(2, '0');
            return `${year}. ${month}. ${day}.`;
        } else if (format === 'time') {
            const hour = String(localTime.getHours()).padStart(2, '0');
            const minute = String(localTime.getMinutes()).padStart(2, '0');
            const second = String(localTime.getSeconds()).padStart(2, '0');
            return `${hour}:${minute}:${second}`;
        } else {
            const year = localTime.getFullYear();
            const month = String(localTime.getMonth() + 1).padStart(2, '0');
            const day = String(localTime.getDate()).padStart(2, '0');
            const hour = String(localTime.getHours()).padStart(2, '0');
            const minute = String(localTime.getMinutes()).padStart(2, '0');
            const second = String(localTime.getSeconds()).padStart(2, '0');
            return `${year}. ${month}. ${day}. ${hour}:${minute}:${second}`;
        }
    } catch (error) {
        console.warn('시간대 변환 실패:', error);
        return dateString; // 에러 시 원본 반환
    }
}

// 더 간단한 ISO 날짜 변환 함수
function convertISOToLocalTime(isoString, format = 'datetime') {
    try {
        const date = new Date(isoString);
        
        if (format === 'date') {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}. ${month}. ${day}.`;
        } else if (format === 'time') {
            const hour = String(date.getHours()).padStart(2, '0');
            const minute = String(date.getMinutes()).padStart(2, '0');
            const second = String(date.getSeconds()).padStart(2, '0');
            return `${hour}:${minute}:${second}`;
        } else {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hour = String(date.getHours()).padStart(2, '0');
            const minute = String(date.getMinutes()).padStart(2, '0');
            const second = String(date.getSeconds()).padStart(2, '0');
            return `${year}. ${month}. ${day}. ${hour}:${minute}:${second}`;
        }
    } catch (error) {
        console.warn('ISO 시간대 변환 실패:', error);
        return isoString;
    }
}

// 페이지 로드 시 자동 변환
document.addEventListener('DOMContentLoaded', function() {
    // 사용자 시간대 표시
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const timezoneElements = document.querySelectorAll('.user-timezone');
    timezoneElements.forEach(element => {
        element.textContent = `현재 시간대: ${userTimezone}`;
    });
    
    // data-datetime 속성을 가진 요소들 자동 변환
    const dateTimeElements = document.querySelectorAll('[data-datetime]');
    dateTimeElements.forEach(element => {
        const originalDateTime = element.getAttribute('data-datetime');
        const format = element.getAttribute('data-format') || 'datetime';
        
        // ISO 형식인지 확인
        if (originalDateTime.includes('T') && originalDateTime.includes('Z')) {
            element.textContent = convertISOToLocalTime(originalDateTime, format);
        } else {
            element.textContent = convertToLocalTime(originalDateTime, format);
        }
    });
    
    // 클래스 기반 자동 변환
    const localTimeElements = document.querySelectorAll('.local-time');
    localTimeElements.forEach(element => {
        const originalText = element.textContent;
        const convertedText = convertToLocalTime(originalText);
        
        if (convertedText !== originalText) {
            element.textContent = convertedText;
            element.title = `원본: ${originalText}`;
        }
    });
});

// 수동 변환 함수들을 전역으로 노출
window.convertToLocalTime = convertToLocalTime;
window.convertISOToLocalTime = convertISOToLocalTime; 