export default class BootScene extends Phaser.Scene {
    constructor() {
        super({ key: 'Boot' });
    }

    create() {
        // BootScene은 이제 PreloadScene에서 처리하므로 사용하지 않음
        // 닉네임 입력이 필요한 경우를 위해 남겨둠
        const name = window.USER_NICKNAME || localStorage.getItem('vamsur_nickname');
        if (!name) {
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
        } else {
            this.scene.start('MainMenu');
        }
    }
}