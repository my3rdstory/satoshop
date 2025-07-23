export default class BootScene extends Phaser.Scene {
    constructor() {
        super({ key: 'Boot' });
    }

    preload() {
        this.load.html('nameform', '/static/selker/html/nameform.html');
        // BGM 로드
        this.load.audio('bgm', '/static/selker/audio/bgm.mp3');
    }

    create() {
        const name = localStorage.getItem('vamsur_nickname');
        if (name) {
            this.scene.start('MainMenu');
        } else {
            this.add.text(this.scale.width/2, this.scale.height*0.3, 'Enter Your Nickname', { fontSize: '48px', fill: '#fff' }).setOrigin(0.5);
            const element = this.add.dom(this.scale.width/2, this.scale.height*0.5).createFromCache('nameform');
            element.addListener('click');
            element.on('click', (event) => {
                if (event.target.name === 'submitButton') {
                    const inputText = element.getChildByName('nameField');
                    if (inputText.value !== '') {
                        localStorage.setItem('vamsur_nickname', inputText.value);
                        element.removeListener('click');
                        element.setVisible(false);
                        this.scene.start('MainMenu');
                    }
                }
            });
        }
    }
}