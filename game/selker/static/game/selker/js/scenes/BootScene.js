import WaveConfig from '../config/WaveConfig.js';
import EnemyManager from '../managers/EnemyManager.js';
import ItemManager from '../managers/ItemManager.js';

export default class BootScene extends Phaser.Scene {
    constructor() {
        super({ key: 'Boot' });
    }

    preload() {
        this.load.html('nameform', '/static/game/selker/html/nameform.html');
        // BGM 로드
        this.load.audio('bgm', '/static/game/selker/audio/bgm.mp3');
        // 플레이어 이미지 로드 (Bitcoin SVG) - 크기 조정
        this.load.svg('player', '/static/game/selker/img/Bitcoin.svg', { width: 25, height: 25 });
    }

    async create() {
        // 적 매니저 로드
        const enemyManager = new EnemyManager(this);
        await enemyManager.load();
        
        // 적 이미지들 로드
        enemyManager.preloadEnemies();
        
        // 로드 완료 대기
        this.load.once('complete', () => {
            this.continueCreate(enemyManager);
        });
        
        // 로드가 필요한 경우 시작
        if (this.load.list.size > 0) {
            this.load.start();
        } else {
            this.continueCreate(enemyManager);
        }
    }
    
    async continueCreate(enemyManager) {
        // 게임 전역에서 사용할 수 있도록 저장
        this.game.enemyManager = enemyManager;
        
        // 아이템 매니저 로드
        const itemManager = new ItemManager(this);
        await itemManager.load();
        this.game.itemManager = itemManager;
        
        // 웨이브 설정 로드
        const waveConfig = new WaveConfig();
        await waveConfig.load();
        
        // 게임 전역에서 사용할 수 있도록 저장
        this.game.waveConfig = waveConfig;
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