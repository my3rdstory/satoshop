import ApiService from '../services/api.js';
import KeyboardManager from '../managers/KeyboardManager.js';

export default class RankingScene extends Phaser.Scene {
    constructor() {
        super({ key: 'RankingScene' });
        this.keyboardManager = null;
    }
    
    init(data) {
        this.playerData = data || {};
    }
    
    async create() {
        const centerX = this.scale.width / 2;
        const centerY = this.scale.height / 2;
        
        // 키보드 매니저 초기화
        this.keyboardManager = new KeyboardManager(this);
        await this.keyboardManager.load();
        this.keyboardManager.setupKeys();
        
        // 타이틀 - GAME OVER 또는 RANKINGS
        const title = this.playerData.score !== undefined ? 'GAME OVER' : 'RANKINGS';
        const titleColor = this.playerData.score !== undefined ? '#ff0000' : '#ffd700';
        this.add.text(centerX, 50, title, { 
            fontSize: '48px', 
            fill: titleColor,
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 현재 게임 스코어 또는 최고 스코어 표시
        await this.displayMyScore();
        
        // 로딩 텍스트
        const loadingText = this.add.text(centerX, centerY, 'Loading rankings...', { 
            fontSize: '24px', 
            fill: '#999' 
        }).setOrigin(0.5);
        
        // 랭킹 가져오기
        try {
            const rankingData = await ApiService.getTopRankings(10);
            loadingText.destroy();
            
            let rankings;
            if (rankingData && rankingData.rankings) {
                // DB에서 가져온 랭킹 사용
                rankings = rankingData.rankings;
            } else if (rankingData && Array.isArray(rankingData)) {
                rankings = rankingData;
            } else {
                // DB 랭킹이 없을 때만 localStorage 사용
                rankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
            }
            
            // 랭킹 표시
            this.displayRankings(rankings);
            
        } catch (error) {
            loadingText.setText('Failed to load rankings');
            console.error('Error loading rankings:', error);
            
            // API 실패 시에만 로컬 랭킹 표시
            const localRankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
            this.displayRankings(localRankings);
        }
        
        // 버튼들
        this.createButtons();
        
        // 키보드 단축키
        this.setupKeyboardShortcuts();
    }
    
    async displayMyScore() {
        const centerX = this.scale.width / 2;
        const nickname = localStorage.getItem('vamsur_nickname');
        
        if (this.playerData.score !== undefined) {
            // 방금 끝난 게임의 점수 표시
            const scoreBox = this.add.rectangle(centerX, 120, 400, 80, 0x333333, 0.8);
            scoreBox.setStrokeStyle(2, 0xffffff);
            
            this.add.text(centerX, 120, 
                `Your Score: ${this.playerData.score}\n` +
                `Wave: ${this.playerData.wave} | Weapon Lv: ${this.playerData.weaponLevel}`, 
                { 
                    fontSize: '24px', 
                    fill: '#fff',
                    align: 'center'
                }
            ).setOrigin(0.5);
        } else if (nickname) {
            // 나의 최고 점수 가져오기
            try {
                const myRankings = await ApiService.getRankings(1, 0, nickname);
                if (myRankings && myRankings.rankings && myRankings.rankings.length > 0) {
                    const myBest = myRankings.rankings[0];
                    
                    const scoreBox = this.add.rectangle(centerX, 120, 400, 80, 0x444444, 0.8);
                    scoreBox.setStrokeStyle(2, 0xffd700);
                    
                    this.add.text(centerX, 120, 
                        `My Best Score: ${myBest.score}\n` +
                        `Wave: ${myBest.wave} | Weapon Lv: ${myBest.weapon_level}`, 
                        { 
                            fontSize: '24px', 
                            fill: '#ffd700',
                            align: 'center'
                        }
                    ).setOrigin(0.5);
                }
            } catch (error) {
                // localStorage에서 찾기
                const localRankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
                const myBest = localRankings.find(r => r.name === nickname || r.nickname === nickname);
                
                if (myBest) {
                    const scoreBox = this.add.rectangle(centerX, 120, 400, 80, 0x444444, 0.8);
                    scoreBox.setStrokeStyle(2, 0xffd700);
                    
                    this.add.text(centerX, 120, 
                        `My Best Score: ${myBest.score}\n` +
                        `Wave: ${myBest.wave || 0} | Weapon Lv: ${myBest.weapon_level || 0}`, 
                        { 
                            fontSize: '24px', 
                            fill: '#ffd700',
                            align: 'center'
                        }
                    ).setOrigin(0.5);
                }
            }
        }
    }
    
    displayRankings(rankings) {
        const centerX = this.scale.width / 2;
        const startY = 250;  // 200에서 250으로 조정하여 더 아래로
        
        // 랭킹 제목
        this.add.text(centerX, startY - 60, 'TOP 10 RANKINGS', {  // -40에서 -60으로 더 위로
            fontSize: '32px', 
            fill: '#ffd700',
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 랭킹 배경 (더 크게 조정)
        const rankingBg = this.add.rectangle(centerX, startY + 140, 600, 340, 0x000033, 0.8);  // y위치와 높이 조정
        rankingBg.setStrokeStyle(2, 0x0066ff);
        
        // 헤더
        this.add.text(centerX - 250, startY + 20, 'Rank', {  // +10에서 +20으로
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        this.add.text(centerX - 100, startY + 20, 'Name', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        this.add.text(centerX + 100, startY + 20, 'Score', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        this.add.text(centerX + 200, startY + 20, 'Wave', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        
        // 구분선
        this.add.line(centerX, startY + 45, 0, 0, 580, 0, 0x666666).setLineWidth(2);  // +35에서 +45로
        
        // 랭킹 목록
        rankings.slice(0, 10).forEach((ranking, index) => {
            const y = startY + 65 + (index * 28);  // +50에서 +65로, 간격도 25에서 28로
            const isCurrentPlayer = ranking.nickname === this.playerData.nickname && 
                                  ranking.score === this.playerData.score;
            const color = isCurrentPlayer ? '#ffff00' : '#ffffff';
            
            // 순위
            const rank = ranking.rank || (index + 1);
            this.add.text(centerX - 250, y, rank.toString(), { 
                fontSize: '18px', 
                fill: color 
            });
            
            // 이름
            const name = ranking.nickname || ranking.name || 'Unknown';
            this.add.text(centerX - 100, y, name.substring(0, 15), { 
                fontSize: '18px', 
                fill: color 
            });
            
            // 점수
            this.add.text(centerX + 100, y, ranking.score.toString(), { 
                fontSize: '18px', 
                fill: color 
            });
            
            // 웨이브
            if (ranking.wave) {
                this.add.text(centerX + 200, y, ranking.wave.toString(), { 
                    fontSize: '18px', 
                    fill: color 
                });
            }
        });
    }
    
    createButtons() {
        const centerX = this.scale.width / 2;
        const buttonY = this.scale.height - 100;
        
        // 새 게임 버튼
        const newGameButton = this.add.rectangle(centerX - 120, buttonY, 200, 60, 0x00ff00);
        newGameButton.setInteractive();
        newGameButton.setStrokeStyle(2, 0x00ffff);
        
        const newGameKey = this.keyboardManager?.getActionKey('startGame') || 'S';
        const newGameText = this.add.text(centerX - 120, buttonY, `New Game [${newGameKey}]`, { 
            fontSize: '24px', 
            fill: '#000',
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 메인 메뉴 버튼
        const menuButton = this.add.rectangle(centerX + 120, buttonY, 200, 60, 0x0088ff);
        menuButton.setInteractive();
        menuButton.setStrokeStyle(2, 0x00ffff);
        
        const menuKey = this.keyboardManager?.getActionKey('returnToMainMenu') || 'C';
        const menuText = this.add.text(centerX + 120, buttonY, `Main Menu [${menuKey}]`, { 
            fontSize: '24px', 
            fill: '#fff',
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 버튼 호버 효과
        newGameButton.on('pointerover', () => {
            newGameButton.setFillStyle(0x66ff66);
            this.input.setDefaultCursor('pointer');
        });
        
        newGameButton.on('pointerout', () => {
            newGameButton.setFillStyle(0x00ff00);
            this.input.setDefaultCursor('default');
        });
        
        menuButton.on('pointerover', () => {
            menuButton.setFillStyle(0x66aaff);
            this.input.setDefaultCursor('pointer');
        });
        
        menuButton.on('pointerout', () => {
            menuButton.setFillStyle(0x0088ff);
            this.input.setDefaultCursor('default');
        });
        
        // 버튼 클릭 이벤트
        newGameButton.on('pointerdown', () => {
            const nickname = localStorage.getItem('vamsur_nickname');
            this.scene.start('GameScene', { nickname: nickname });
        });
        
        menuButton.on('pointerdown', () => {
            this.scene.start('MainMenu');
        });
    }
    
    setupKeyboardShortcuts() {
        // 키보드 매니저로 대체됨
    }
    
    update() {
        if (this.keyboardManager) {
            if (this.keyboardManager.isActionPressed('startGame')) {
                const nickname = localStorage.getItem('vamsur_nickname');
                this.scene.start('GameScene', { nickname: nickname });
            }
            
            if (this.keyboardManager.isActionPressed('returnToMainMenu')) {
                this.scene.start('MainMenu');
            }
        }
    }
}