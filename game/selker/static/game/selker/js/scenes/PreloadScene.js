import WaveConfig from '../config/WaveConfig.js';
import EnemyManager from '../managers/EnemyManager.js';
import ItemManager from '../managers/ItemManager.js';

export default class PreloadScene extends Phaser.Scene {
    constructor() {
        super({ key: 'PreloadScene' });
    }

    preload() {
        const centerX = this.scale.width / 2;
        const centerY = this.scale.height / 2;
        
        // 게임 타이틀
        this.add.text(centerX, centerY - 150, 'To the Selker!', { 
            fontSize: '56px', 
            fill: '#fff' 
        }).setOrigin(0.5);
        
        // 로딩 텍스트
        const loadingText = this.add.text(centerX, centerY - 50, 'Loading...', {
            fontSize: '24px',
            fill: '#ffffff'
        }).setOrigin(0.5);
        
        // 로딩바 배경
        const progressBarBg = this.add.rectangle(centerX, centerY, 400, 30, 0x222222);
        progressBarBg.setStrokeStyle(2, 0x444444);
        
        // 로딩바 (진행 상태)
        const progressBar = this.add.rectangle(centerX - 200, centerY, 0, 26, 0x00ff00);
        progressBar.setOrigin(0, 0.5);
        
        // 퍼센트 텍스트
        const percentText = this.add.text(centerX, centerY + 40, '0%', {
            fontSize: '20px',
            fill: '#ffffff'
        }).setOrigin(0.5);
        
        // 현재 로딩 중인 파일 표시
        const assetText = this.add.text(centerX, centerY + 80, '', {
            fontSize: '16px',
            fill: '#888888'
        }).setOrigin(0.5);
        
        // 로딩 이벤트 리스너
        this.load.on('progress', (value) => {
            progressBar.width = 400 * value;
            percentText.setText(parseInt(value * 100) + '%');
            
            // 로딩 텍스트 애니메이션
            const dots = '.'.repeat((Math.floor(value * 10) % 4));
            loadingText.setText('Loading' + dots);
        });
        
        this.load.on('fileprogress', (file) => {
            assetText.setText('Loading: ' + file.key);
        });
        
        this.load.on('complete', () => {
            assetText.setText('Complete!');
            loadingText.setText('Ready!');
        });
        
        // 모든 에셋 로드
        this.loadAllAssets();
    }
    
    loadAllAssets() {
        // 이미지 에셋
        this.load.svg('player', '/static/game/selker/img/Bitcoin.svg', { width: 25, height: 25 });
        this.load.svg('poo', '/static/game/selker/img/poo.svg', { width: 30, height: 30 });
        
        // 사운드 에셋 (bgm.mp3만 존재, 나머지는 주석 처리)
        this.load.audio('bgm', '/static/game/selker/audio/bgm.mp3');
        // this.load.audio('laser', '/static/game/selker/audio/laser.wav');
        // this.load.audio('explosion', '/static/game/selker/audio/explosion.wav');
        // this.load.audio('powerup', '/static/game/selker/audio/powerup.wav');
        // this.load.audio('gameover', '/static/game/selker/audio/gameover.wav');
        // this.load.audio('bossBgm', '/static/game/selker/audio/boss_bgm.mp3');
        // this.load.audio('bossHit', '/static/game/selker/audio/boss_hit.wav');
        // this.load.audio('bossExplosion', '/static/game/selker/audio/boss_explosion.wav');
        
        // HTML 폼
        this.load.html('nameform', '/static/game/selker/html/nameform.html');
    }

    async create() {
        // 추가 로딩 텍스트
        const centerX = this.scale.width / 2;
        const centerY = this.scale.height / 2;
        const loadingText = this.add.text(centerX, centerY + 120, 'Initializing game systems...', {
            fontSize: '16px',
            fill: '#888888'
        }).setOrigin(0.5);
        
        // 적 매니저 로드
        loadingText.setText('Loading enemy configurations...');
        const enemyManager = new EnemyManager(this);
        await enemyManager.load();
        
        // 적 이미지들 동적 로드
        enemyManager.preloadEnemies();
        if (this.load.list.size > 0) {
            await new Promise(resolve => {
                this.load.once('complete', resolve);
                this.load.start();
            });
        }
        
        this.game.enemyManager = enemyManager;
        
        // 아이템 매니저 로드
        loadingText.setText('Loading item configurations...');
        const itemManager = new ItemManager(this);
        await itemManager.load();
        this.game.itemManager = itemManager;
        
        // 웨이브 설정 로드
        loadingText.setText('Loading wave configurations...');
        const waveConfig = new WaveConfig();
        await waveConfig.load();
        this.game.waveConfig = waveConfig;
        
        // 사토삽 로그인 사용자 이름 설정
        const name = window.USER_NICKNAME || localStorage.getItem('vamsur_nickname');
        if (name) {
            localStorage.setItem('vamsur_nickname', name);
        }
        
        loadingText.setText('Starting game...');
        
        // 잠시 대기 후 메인 메뉴로 전환
        this.time.delayedCall(300, () => {
            this.scene.start('MainMenu');
        });
    }
}