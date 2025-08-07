import KeyboardManager from '../managers/KeyboardManager.js';

export default class MainMenuScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MainMenu' });
        this.keyboardManager = null;
    }

    async create() {
        const centerX = this.scale.width/2;
        const centerY = this.scale.height/2;
        
        // 키보드 매니저 초기화
        this.keyboardManager = new KeyboardManager(this);
        await this.keyboardManager.load();
        this.keyboardManager.setupKeys();
        
        // BGM이 없으면 생성
        if (!this.sound.get('bgm')) {
            const bgm = this.sound.add('bgm', { loop: true, volume: 0.5 });
            bgm.play();
        }
        
        // 음악 상태 표시
        this.musicStatusText = this.add.text(this.scale.width - 16, 16, this.getMusicStatus(), {
            fontSize: '20px',
            fill: '#fff'
        }).setOrigin(1, 0);
        
        this.add.text(centerX, centerY - 100, 'To the Selker!', { fontSize: '56px', fill: '#fff' }).setOrigin(0.5);
        
        // 서브 타이틀 추가
        this.add.text(centerX, centerY - 40, '"당신은 셀커에 성공할 수 있습니까?"', { 
            fontSize: '20px', 
            fill: '#ffd700',
            fontStyle: 'italic',
            padding: { top: 5, bottom: 5 }
        }).setOrigin(0.5);

        const startButton = this.add.text(centerX, centerY + 20, 'Start Game', { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        startButton.on('pointerdown', () => {
            const name = localStorage.getItem('vamsur_nickname');
            this.scene.start('GameScene', { nickname: name });
        });

        const rankingButton = this.add.text(centerX, centerY + 70, 'Rankings', { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        rankingButton.on('pointerdown', () => {
            this.scene.start('RankingScene', {});  // 빈 데이터로 전달하여 최고 점수 표시
        });

        const settingsButton = this.add.text(centerX, centerY + 120, 'Settings', { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        settingsButton.on('pointerdown', () => {
            this.scene.start('Settings');
        });
        
        // 키보드 단축키 안내 (동적 생성)
        const shortcuts = [];
        if (this.keyboardManager) {
            const actions = this.keyboardManager.getAllActionsForScene();
            actions.forEach(action => {
                shortcuts.push(`[${action.key}] ${action.description}`);
            });
        }
        this.add.text(centerX, centerY + 200, shortcuts.join(' | '), { fontSize: '20px', fill: '#999' }).setOrigin(0.5);
    }
    
    update() {
        if (this.keyboardManager) {
            if (this.keyboardManager.isActionPressed('startGame')) {
                const name = localStorage.getItem('vamsur_nickname');
                this.scene.start('GameScene', { nickname: name });
            }
            
            if (this.keyboardManager.isActionPressed('openRanking')) {
                this.scene.start('RankingScene', {});
            }
            
            if (this.keyboardManager.isActionPressed('openSettings')) {
                this.scene.start('Settings');
            }
            
            if (this.keyboardManager.isActionPressed('toggleMusic')) {
                this.toggleMusic();
            }
        }
    }
    
    toggleMusic() {
        const bgm = this.sound.get('bgm');
        if (bgm) {
            if (bgm.isPlaying) {
                bgm.pause();
                this.showMusicStatus('Music OFF');
            } else {
                bgm.resume();
                this.showMusicStatus('Music ON');
            }
            // 상태 텍스트 업데이트
            if (this.musicStatusText) {
                this.musicStatusText.setText(this.getMusicStatus());
            }
        }
    }
    
    getMusicStatus() {
        const bgm = this.sound.get('bgm');
        return bgm && bgm.isPlaying ? '♪ Music ON' : '♪ Music OFF';
    }
    
    showMusicStatus(status) {
        const centerX = this.scale.width / 2;
        const centerY = this.scale.height / 2;
        
        const statusText = this.add.text(centerX, centerY - 150, status, {
            fontSize: '28px',
            fill: status.includes('ON') ? '#0f0' : '#f00'
        }).setOrigin(0.5);
        
        this.tweens.add({
            targets: statusText,
            alpha: 0,
            y: centerY - 180,
            duration: 1000,
            onComplete: () => statusText.destroy()
        });
    }
}