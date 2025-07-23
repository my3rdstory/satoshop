import ApiService from '../services/api.js';

export default class RankingScene extends Phaser.Scene {
    constructor() {
        super({ key: 'RankingScene' });
    }
    
    init(data) {
        this.playerData = data || {};
    }
    
    async create() {
        const centerX = this.scale.width / 2;
        const centerY = this.scale.height / 2;
        
        // 타이틀
        this.add.text(centerX, 50, 'GAME OVER', { 
            fontSize: '48px', 
            fill: '#ff0000',
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 플레이어 스코어 표시
        if (this.playerData.score !== undefined) {
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
        }
        
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
            if (rankingData && Array.isArray(rankingData)) {
                rankings = rankingData;
            } else if (rankingData && rankingData.rankings) {
                rankings = rankingData.rankings;
            } else {
                rankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
            }
            
            // 랭킹 표시
            this.displayRankings(rankings);
            
        } catch (error) {
            loadingText.setText('Failed to load rankings');
            console.error('Error loading rankings:', error);
            
            // 로컬 랭킹 표시
            const localRankings = JSON.parse(localStorage.getItem('vamsur_ranking') || '[]');
            this.displayRankings(localRankings);
        }
        
        // 버튼들
        this.createButtons();
        
        // 키보드 단축키
        this.setupKeyboardShortcuts();
    }
    
    displayRankings(rankings) {
        const centerX = this.scale.width / 2;
        const startY = 200;
        
        // 랭킹 제목
        this.add.text(centerX, startY - 30, 'TOP 10 RANKINGS', { 
            fontSize: '32px', 
            fill: '#ffd700',
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 랭킹 배경
        const rankingBg = this.add.rectangle(centerX, startY + 120, 600, 300, 0x000033, 0.8);
        rankingBg.setStrokeStyle(2, 0x0066ff);
        
        // 헤더
        this.add.text(centerX - 250, startY + 10, 'Rank', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        this.add.text(centerX - 100, startY + 10, 'Name', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        this.add.text(centerX + 100, startY + 10, 'Score', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        this.add.text(centerX + 200, startY + 10, 'Wave', { 
            fontSize: '20px', 
            fill: '#fff',
            fontStyle: 'bold'
        });
        
        // 구분선
        this.add.line(centerX, startY + 35, 0, 0, 580, 0, 0x666666).setLineWidth(2);
        
        // 랭킹 목록
        rankings.slice(0, 10).forEach((ranking, index) => {
            const y = startY + 50 + (index * 25);
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
        
        const newGameText = this.add.text(centerX - 120, buttonY, 'New Game [S]', { 
            fontSize: '24px', 
            fill: '#000',
            fontStyle: 'bold'
        }).setOrigin(0.5);
        
        // 메인 메뉴 버튼
        const menuButton = this.add.rectangle(centerX + 120, buttonY, 200, 60, 0x0088ff);
        menuButton.setInteractive();
        menuButton.setStrokeStyle(2, 0x00ffff);
        
        const menuText = this.add.text(centerX + 120, buttonY, 'Main Menu [M]', { 
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
        // S키 - 새 게임
        this.input.keyboard.on('keydown-S', () => {
            const nickname = localStorage.getItem('vamsur_nickname');
            this.scene.start('GameScene', { nickname: nickname });
        });
        
        // M키 - 메인 메뉴
        this.input.keyboard.on('keydown-M', () => {
            this.scene.start('MainMenu');
        });
        
        // ESC키 - 메인 메뉴
        this.input.keyboard.on('keydown-ESC', () => {
            this.scene.start('MainMenu');
        });
    }
}