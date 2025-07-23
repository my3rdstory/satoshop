// API 서비스
const API_URL = '/selker/api';

export default class ApiService {
    static async saveRanking(data) {
        try {
            const response = await fetch(`${API_URL}/rankings/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save ranking');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error saving ranking:', error);
            // 실패 시 로컬스토리지 사용 (백업)
            this.saveLocalRanking(data.nickname, data.score, data.wave, data.weapon_level, data.play_time);
            return null;
        }
    }
    
    static async getRankings(limit = 10, offset = 0, nickname = null) {
        try {
            let url = `${API_URL}/rankings/list/?limit=${limit}&offset=${offset}`;
            if (nickname) {
                url += `&nickname=${encodeURIComponent(nickname)}`;
            }
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error('Failed to get rankings');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error getting rankings:', error);
            // 실패 시 로컬스토리지에서 가져오기
            return this.getLocalRankings();
        }
    }
    
    static async getTopRankings(limit = 10) {
        try {
            const response = await fetch(`${API_URL}/rankings/top/?limit=${limit}`);
            
            if (!response.ok) {
                throw new Error('Failed to get top rankings');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error getting top rankings:', error);
            return this.getLocalRankings();
        }
    }
    
    // getStats 메서드 제거 (Django에서 미사용)
    
    // 로컬스토리지 백업 메서드
    static getLocalRankings() {
        const rankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
        return {
            rankings: rankings.map((r, idx) => ({
                ...r,
                rank: idx + 1,
                id: idx,
                created_at: new Date().toISOString()
            })),
            total: rankings.length
        };
    }
    
    static saveLocalRanking(name, score, wave = 0, weaponLevel = 0, playTime = 0) {
        let rankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
        rankings.push({ 
            name, 
            score, 
            wave, 
            weapon_level: weaponLevel,
            play_time: playTime,
            created_at: new Date().toISOString()
        });
        rankings.sort((a, b) => b.score - a.score);
        rankings = rankings.slice(0, 10);
        localStorage.setItem('vamsur_ranking', JSON.stringify(rankings));
    }
}