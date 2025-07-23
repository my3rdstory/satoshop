export default class BootScene extends Phaser.Scene {
    constructor() {
        super({ key: 'Boot' });
    }

    preload() {
        this.load.html('nameform', '/static/game/selker/html/nameform.html');
        // BGM 로드
        this.load.audio('bgm', '/static/game/selker/audio/bgm.mp3');
    }

    create() {
        // 사토삽 로그인 사용자 이름을 자동으로 사용
        const name = window.USER_NICKNAME || localStorage.getItem('vamsur_nickname');
        if (name) {
            localStorage.setItem('vamsur_nickname', name);
            this.scene.start('MainMenu');
        } else {
            // 예외 상황을 위한 폴백
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