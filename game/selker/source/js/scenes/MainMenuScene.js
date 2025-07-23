export default class MainMenuScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MainMenu' });
    }

    create() {
        const centerX = this.scale.width/2;
        const centerY = this.scale.height/2;
        
        this.add.text(centerX, centerY - 100, 'To the Selker!', { fontSize: '48px', fill: '#fff' }).setOrigin(0.5);

        const startButton = this.add.text(centerX, centerY, 'Start Game', { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        startButton.on('pointerdown', () => {
            const name = localStorage.getItem('vamsur_nickname');
            this.scene.start('GameScene', { nickname: name });
        });

        const rankingButton = this.add.text(centerX, centerY + 50, 'Rankings', { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        rankingButton.on('pointerdown', () => {
            this.scene.start('RankingScene');
        });

        const settingsButton = this.add.text(centerX, centerY + 100, 'Settings', { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        settingsButton.on('pointerdown', () => {
            this.scene.start('Settings');
        });
        
        // S키 단축키 추가
        this.add.text(centerX, centerY + 200, 'Press [S] to Start', { fontSize: '20px', fill: '#999' }).setOrigin(0.5);
        
        this.input.keyboard.on('keydown-S', () => {
            const name = localStorage.getItem('vamsur_nickname');
            this.scene.start('GameScene', { nickname: name });
        });
    }
}