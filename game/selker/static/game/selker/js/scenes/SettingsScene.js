import KeyboardManager from '../managers/KeyboardManager.js';

export default class SettingsScene extends Phaser.Scene {
    constructor() {
        super({ key: 'Settings' });
        this.keyboardManager = null;
    }

    preload() {
        this.load.html('nameform', 'nameform.html');
    }

    async create() {
        const centerX = this.scale.width/2;
        
        // 키보드 매니저 초기화
        this.keyboardManager = new KeyboardManager(this);
        await this.keyboardManager.load();
        this.keyboardManager.setupKeys();
        
        this.add.text(centerX, 100, 'Settings', { fontSize: '48px', fill: '#fff' }).setOrigin(0.5);

        // Nickname settings
        this.add.text(centerX - 200, 200, 'Nickname:', { fontSize: '32px', fill: '#fff' });
        const nameText = this.add.text(centerX, 200, localStorage.getItem('vamsur_nickname') || 'Not Set', { fontSize: '32px', fill: '#0f0' });
        const changeButton = this.add.text(centerX + 200, 200, 'Change', { fontSize: '32px', fill: '#0f0' }).setInteractive();
        changeButton.on('pointerdown', () => {
            const element = this.add.dom(centerX, 250).createFromCache('nameform');
            element.addListener('click');
            element.on('click', (event) => {
                if (event.target.name === 'submitButton') {
                    const inputText = element.getChildByName('nameField');
                    if (inputText.value !== '') {
                        localStorage.setItem('vamsur_nickname', inputText.value);
                        nameText.setText(inputText.value);
                        element.removeListener('click');
                        element.setVisible(false);
                    }
                }
            });
        });

        // Sound settings
        this.add.text(centerX - 200, 300, 'Sound:', { fontSize: '32px', fill: '#fff' });
        const soundStatus = this.game.sound.mute ? 'OFF' : 'ON';
        const soundButton = this.add.text(centerX, 300, soundStatus, { fontSize: '32px', fill: '#0f0' }).setInteractive();
        soundButton.on('pointerdown', () => {
            this.game.sound.mute = !this.game.sound.mute;
            soundButton.setText(this.game.sound.mute ? 'OFF' : 'ON');
        });

        // Reset Data
        const resetButton = this.add.text(centerX, 400, 'Reset Game Data', { fontSize: '32px', fill: '#f00' }).setOrigin(0.5).setInteractive();
        resetButton.on('pointerdown', () => {
            localStorage.removeItem('vamsur_nickname');
            localStorage.removeItem('vamsur_ranking');
            this.scene.start('Boot');
        });

        const backKey = this.keyboardManager?.getActionKey('returnToMainMenu') || 'C';
        const backButton = this.add.text(centerX, 500, `Back to Menu [${backKey}]`, { fontSize: '32px', fill: '#0f0' }).setOrigin(0.5).setInteractive();
        backButton.on('pointerdown', () => {
            this.scene.start('MainMenu');
        });
    }
    
    update() {
        if (this.keyboardManager) {
            if (this.keyboardManager.isActionPressed('returnToMainMenu')) {
                this.scene.start('MainMenu');
            }
        }
    }
}