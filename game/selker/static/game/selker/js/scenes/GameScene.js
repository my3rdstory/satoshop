import MobileControls from '../utils/MobileControls.js';
import ScaleManager from '../utils/ScaleManager.js';
import Boss from '../entities/Boss.js';
import ShooterEnemy from '../entities/ShooterEnemy.js';
import ApiService from '../services/api.js';
import KeyboardManager from '../managers/KeyboardManager.js';

export default class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
    }

    init(data) {
        this.nickname = data.nickname;
        this.player = null;
        this.cursors = null;
        this.mobileControls = null;
        this.enemies = null;
        this.wave = 1;
        this.waveText = null;
        this.waveTimerText = null;
        this.waveTimer = this.game.waveConfig?.getWaveTimer() || 15;
        this.weapons = null;
        this.hp = 100;
        this.hpText = null;
        this.score = 0;
        this.scoreText = null;
        this.items = null;
        this.weaponLevel = 1;
        this.gameOver = false;
        this.boss = null;
        this.bossSpawned = false;
        this.startTime = null;
        this.isPaused = false;
        this.pauseOverlay = null;
        this.pauseText = null;
        this.pauseInstructions = null;
        this.shieldTimers = [];
        this.keyboardManager = null;
    }

    preload() {
        this.load.html('nameform', 'nameform.html');
    }

    async create() {
        const centerX = this.scale.width/2;
        const centerY = this.scale.height/2;
        
        // 스케일 매니저 생성
        this.scaleManager = new ScaleManager(this);
        
        // 키보드 매니저 초기화
        this.keyboardManager = new KeyboardManager(this);
        await this.keyboardManager.load();
        this.keyboardManager.setupKeys();
        
        // 게임 캔버스에 포커스 주기
        this.game.canvas.tabIndex = 1;
        this.game.canvas.focus();
        
        // 캔버스 클릭 시 포커스 유지
        this.game.canvas.addEventListener('click', () => {
            this.game.canvas.focus();
        });
        
        // 게임 시작 시간 기록
        this.startTime = Date.now();
        
        // BGM 재생
        if (!this.sound.get('bgm')) {
            const bgm = this.sound.add('bgm', { loop: true, volume: 0.5 });
            bgm.play();
        }
        
        const playerSize = this.scaleManager.getPlayerSize();
        this.player = this.add.rectangle(centerX, centerY, playerSize, playerSize, 0xffffff);
        this.physics.add.existing(this.player);
        this.player.body.setCollideWorldBounds(true);

        this.cursors = this.input.keyboard.createCursorKeys();
        
        // 모바일 컨트롤 생성
        this.mobileControls = new MobileControls(this);

        this.enemies = this.physics.add.group();
        this.weapons = this.physics.add.group();
        this.items = this.physics.add.group();
        this.shields = this.physics.add.group();
        this.enemyWeapons = this.physics.add.group();

        this.waveText = this.add.text(16, 16, 'Wave: 1', { fontSize: this.scaleManager.getFontSize(32), fill: '#fff' });
        this.waveTimerText = this.add.text(16, 84, 'Next wave: 15s', { fontSize: this.scaleManager.getFontSize(24), fill: '#ff0' });
        this.hpText = this.add.text(16, 50, 'HP: 100', { fontSize: this.scaleManager.getFontSize(32), fill: '#fff' });
        this.scoreText = this.add.text(this.scale.width - 16, 16, 'Score: 0', { fontSize: this.scaleManager.getFontSize(32), fill: '#fff' }).setOrigin(1, 0);
        
        // 무기 레벨 표시
        this.weaponLevelText = this.add.text(16, 118, 'Weapon Lv: 1', { fontSize: this.scaleManager.getFontSize(20), fill: '#0ff' });

        this.time.addEvent({
            delay: 1000,
            callback: this.spawnEnemies,
            callbackScope: this,
            loop: true
        });

        this.time.addEvent({
            delay: (this.game.waveConfig?.getWaveTimer() || 15) * 1000,  // 설정된 시간마다 웨이브 증가
            callback: this.increaseWave,
            callbackScope: this,
            loop: true
        });
        
        // 1초마다 웨이브 타이머 업데이트
        this.time.addEvent({
            delay: 1000,
            callback: () => {
                if (!this.gameOver && !this.isPaused) {
                    this.waveTimer--;
                    if (this.waveTimer <= 0) {
                        this.waveTimer = this.game.waveConfig?.getWaveTimer() || 15;
                    }
                    this.waveTimerText.setText(`Next wave: ${this.waveTimer}s`);
                }
            },
            callbackScope: this,
            loop: true
        });

        this.input.on('pointerdown', (pointer) => {
            if (!this.gameOver && !this.isPaused) {
                this.fireWeapon(pointer);
            }
        });
        
        // 자동 발사 추가
        this.time.addEvent({
            delay: this.game.waveConfig?.getAutoFireDelay() || 500,
            callback: () => {
                if (!this.gameOver && !this.isPaused && this.enemies.children.entries.length > 0) {
                    const nearestEnemy = this.physics.closest(this.player, this.enemies.children.entries);
                    if (nearestEnemy) {
                        this.fireWeapon({ x: nearestEnemy.x, y: nearestEnemy.y });
                    }
                }
            },
            callbackScope: this,
            loop: true
        });

        this.physics.add.collider(this.weapons, this.enemies, (weapon, enemy) => {
            weapon.destroy();
            
            // 보스인 경우
            if (enemy.getData('isBoss')) {
                const boss = enemy.getData('boss');
                const destroyed = boss.takeDamage(10);
                if (!destroyed) {
                    return; // 보스가 아직 살아있음
                }
            } 
            // 총 쏘는 적인 경우
            else if (enemy.getData('isShooter')) {
                const shooter = enemy.getData('shooter');
                const destroyed = shooter.takeDamage();
                if (!destroyed) {
                    return; // 아직 살아있음
                }
            }
            // 일반 적
            else {
                enemy.destroy();
                const normalConfig = this.game.waveConfig?.getEnemyStats('normal');
                this.score += normalConfig?.score || 10;
                this.scoreText.setText('Score: ' + this.score);
                
                // 일반 적만 아이템 드롭
                this.dropItem(enemy);
            }
        });

        this.physics.add.collider(this.player, this.enemies, (player, enemy) => {
            if (!this.gameOver) {
                let damage;
                
                // 보스인 경우
                if (enemy.getData('isBoss')) {
                    const boss = enemy.getData('boss');
                    damage = boss?.damage || 15;
                }
                // 총 쏘는 적인 경우
                else if (enemy.getData('isShooter')) {
                    const shooterConfig = this.game.waveConfig?.getEnemyStats('shooter');
                    damage = shooterConfig?.collisionDamage || 8;
                    const shooter = enemy.getData('shooter');
                    if (shooter) {
                        shooter.destroy();
                    }
                }
                // 일반 적
                else {
                    const normalConfig = this.game.waveConfig?.getEnemyStats('normal');
                    damage = normalConfig?.damage || 10;
                    enemy.destroy();
                }
                
                this.hp -= damage;
                this.hpText.setText('HP: ' + this.hp);
                if (this.hp <= 0) {
                    this.endGame();
                }
            }
        });

        // 방어막과 적 총알 충돌
        this.physics.add.overlap(this.shields, this.enemyWeapons, (shield, bullet) => {
            // 총알 제거
            bullet.destroy();
            
            // 방어막 깜빡임 효과
            shield.setAlpha(0.2);
            this.time.delayedCall(100, () => {
                if (shield && shield.active) {
                    shield.setAlpha(0.8);
                }
            });
        });

        this.physics.add.overlap(this.player, this.items, (player, item) => {
            const itemType = item.getData('type');
            let message = '';
            
            switch (itemType) {
                case 'weapon':
                    this.weaponLevel++;
                    this.weaponLevelText.setText('Weapon Lv: ' + this.weaponLevel);
                    message = 'Weapon UP!';
                    break;
                case 'hp':
                    this.hp = Math.min(100, this.hp + 20);
                    this.hpText.setText('HP: ' + this.hp);
                    message = '+20 HP';
                    break;
                case 'bomb':
                    const bombConfig = this.game.waveConfig?.getBombConfig() || {
                        bossDamagePercent: 0.5,
                        explosionColor: 0xffff00,
                        explosionRadius: 100,
                        explosionDuration: 500
                    };
                    
                    // 보스는 체력 비율 감소, 일반 적은 즉사
                    this.enemies.children.each(enemy => {
                        if (enemy.getData('isBoss')) {
                            const boss = enemy.getData('boss');
                            if (boss && boss.hp) {
                                // 보스 현재 체력의 설정 비율만큼 데미지
                                const damage = Math.floor(boss.hp * bombConfig.bossDamagePercent);
                                boss.takeDamage(damage, true);
                                
                                // 폭발 이펙트 표시
                                const explosion = this.add.circle(boss.sprite.x, boss.sprite.y, 
                                    bombConfig.explosionRadius, bombConfig.explosionColor, 0.8);
                                this.tweens.add({
                                    targets: explosion,
                                    scale: 3,
                                    alpha: 0,
                                    duration: bombConfig.explosionDuration,
                                    onComplete: () => explosion.destroy()
                                });
                            }
                        } else {
                            // 일반 적은 즉사
                            enemy.destroy();
                        }
                    });
                    message = 'BOOM!';
                    break;
                case 'shield':
                    this.createShield();
                    message = 'SHIELD!';
                    break;
            }
            
            // 아이템 획득 메시지 표시
            if (message) {
                const text = this.add.text(this.player.x, this.player.y - 40, message, { 
                    fontSize: '24px', 
                    fill: '#ffff00',
                    fontStyle: 'bold'
                }).setOrigin(0.5);
                
                // 텍스트를 위로 올라가면서 사라지게 하는 애니메이션
                this.tweens.add({
                    targets: text,
                    y: text.y - 50,
                    alpha: 0,
                    duration: 1000,
                    ease: 'Power2',
                    onComplete: () => {
                        text.destroy();
                    }
                });
            }
            
            item.destroy();
        });
    }

    update() {
        // 키보드 매니저를 통한 입력 처리
        if (this.keyboardManager) {
            if (this.keyboardManager.isActionPressed('togglePause')) {
                this.togglePause();
            }
            
            if (this.keyboardManager.isActionPressed('returnToMainMenu')) {
                this.returnToMainMenu();
            }
            
            if (this.keyboardManager.isActionPressed('toggleMusic')) {
                this.toggleBGM();
            }
        }
        
        if (this.gameOver || this.isPaused) {
            return;
        }

        // 방어막 업데이트
        this.updateShields();

        this.player.body.setVelocity(0);

        const playerSpeed = this.scaleManager.getPlayerSpeed();
        
        // 키보드 컨트롤
        if (this.cursors.left.isDown) {
            this.player.body.setVelocityX(-playerSpeed);
        } else if (this.cursors.right.isDown) {
            this.player.body.setVelocityX(playerSpeed);
        }

        if (this.cursors.up.isDown) {
            this.player.body.setVelocityY(-playerSpeed);
        } else if (this.cursors.down.isDown) {
            this.player.body.setVelocityY(playerSpeed);
        }
        
        // 모바일 조이스틱 컨트롤
        if (this.mobileControls.isMobile) {
            const joystickDir = this.mobileControls.getJoystickDirection();
            if (joystickDir.x !== 0 || joystickDir.y !== 0) {
                this.player.body.setVelocityX(joystickDir.x * playerSpeed);
                this.player.body.setVelocityY(joystickDir.y * playerSpeed);
            }
        }

        const enemySpeed = this.scaleManager.getEnemySpeed();
        this.enemies.children.each(enemy => {
            if (enemy.body) {
                this.physics.moveToObject(enemy, this.player, enemySpeed);
            }
        });
        
        // 보스 업데이트
        if (this.boss && this.boss.sprite) {
            this.boss.update();
        }
    }

    spawnEnemies() {
        if (this.gameOver || this.isPaused) return;
        
        const waveConfig = this.game.waveConfig?.getWaveConfig(this.wave);
        
        // 기본 스폰 수: 웨이브 설정에서 가져오기
        let spawnCount = waveConfig?.spawnCount || this.wave;
        
        // 무기 레벨에 따른 추가 스폰
        const weaponBonus = this.game.waveConfig?.getWeaponLevelBonus(this.weaponLevel) || 0;
        spawnCount += weaponBonus;
        
        // 최대 스폰 제한
        spawnCount = Math.min(spawnCount, 15);
        
        for (let i = 0; i < spawnCount; i++) {
            this.spawnEnemy();
        }
    }

    spawnEnemy() {
        const width = this.scale.width;
        const height = this.scale.height;
        const x = Phaser.Math.Between(0, width);
        const y = Phaser.Math.Between(0, height);
        const side = Phaser.Math.Between(0, 3);

        let spawnX, spawnY;

        switch (side) {
            case 0: spawnX = x; spawnY = 0; break;
            case 1: spawnX = width; spawnY = y; break;
            case 2: spawnX = x; spawnY = height; break;
            case 3: spawnX = 0; spawnY = y; break;
        }

        const waveConfig = this.game.waveConfig?.getWaveConfig(this.wave);
        const enemyTypes = waveConfig?.enemyTypes || { normal: 0.7, shooter: 0.3 };
        
        // 적 타입 비율에 따라 생성
        const random = Math.random();
        if (this.wave >= 5 && enemyTypes.shooter && random < enemyTypes.shooter) {
            const shooter = new ShooterEnemy(this, spawnX, spawnY, this.scaleManager);
            this.enemies.add(shooter.sprite);
        } else {
            // 일반 적
            let enemySize = this.scaleManager.getEnemySize();
            
            // 웨이브에 따른 크기 감소
            if (this.game.waveConfig?.shouldReduceEnemySize(this.wave)) {
                enemySize = this.scaleManager.getSmallEnemySize();
            }
            
            const enemy = this.add.rectangle(spawnX, spawnY, enemySize, enemySize, 0xff0000);
            this.physics.add.existing(enemy);
            this.enemies.add(enemy);
        }
    }

    increaseWave() {
        if (this.gameOver || this.isPaused) return;
        
        // 보스 스폰 (웨이브가 끝날 때)
        this.spawnBoss();
        
        // 보스와 함께 추가 적들 스폰 (무기 레벨도 고려)
        let bossWaveSpawn = Math.floor(this.wave * 2 * 0.85); // 15% 감소 적용
        if (this.weaponLevel > 3) {
            bossWaveSpawn += this.weaponLevel - 3;
        }
        for (let i = 0; i < bossWaveSpawn; i++) {
            this.spawnEnemy();
        }
        
        this.wave++;
        this.waveText.setText('Wave: ' + this.wave);
        this.bossSpawned = false; // 다음 웨이브를 위해 리셋
        
        // 웨이브 증가 알림 표시
        const waveAlert = this.add.text(this.scale.width/2, this.scale.height*0.25, `WAVE ${this.wave}!`, { 
            fontSize: '48px', 
            fill: '#ff0000',
            fontStyle: 'bold',
            stroke: '#ffffff',
            strokeThickness: 3
        }).setOrigin(0.5);
        
        // 텍스트 애니메이션
        this.tweens.add({
            targets: waveAlert,
            scale: 1.5,
            alpha: 0,
            duration: 2000,
            ease: 'Power2',
            onComplete: () => {
                waveAlert.destroy();
            }
        });
    }
    
    spawnBoss() {
        if (this.bossSpawned || this.gameOver) return;
        
        // 화면 가장자리에서 보스 스폰
        const side = Phaser.Math.Between(0, 3);
        let spawnX, spawnY;
        
        switch (side) {
            case 0: spawnX = this.scale.width/2; spawnY = 0; break;
            case 1: spawnX = this.scale.width; spawnY = this.scale.height/2; break;
            case 2: spawnX = this.scale.width/2; spawnY = this.scale.height; break;
            case 3: spawnX = 0; spawnY = this.scale.height/2; break;
        }
        
        // 보스 생성 (웨이브 설정 포함)
        const waveConfig = this.game.waveConfig?.getWaveConfig(this.wave);
        this.boss = new Boss(this, spawnX, spawnY, this.wave, this.scaleManager, waveConfig);
        this.enemies.add(this.boss.sprite);
        this.bossSpawned = true;
        
        // 보스 등장 알림
        const bossAlert = this.add.text(this.scale.width/2, this.scale.height*0.35, 'BOSS APPEARS!', { 
            fontSize: '36px', 
            fill: '#ff00ff',
            fontStyle: 'bold',
            stroke: '#ffffff',
            strokeThickness: 3
        }).setOrigin(0.5);
        
        this.tweens.add({
            targets: bossAlert,
            scale: 1.2,
            alpha: 0,
            duration: 3000,
            ease: 'Power2',
            onComplete: () => {
                bossAlert.destroy();
            }
        });
    }

    fireWeapon(pointer) {
        const weaponSize = this.scaleManager.getWeaponSize();
        const weaponSpeed = this.scaleManager.getWeaponSpeed();
        
        for (let i = 0; i < this.weaponLevel; i++) {
            const weapon = this.add.rectangle(this.player.x, this.player.y, weaponSize.width, weaponSize.height, 0x00ff00);
            this.physics.add.existing(weapon);
            this.weapons.add(weapon);
            const angle = Phaser.Math.Angle.Between(this.player.x, this.player.y, pointer.x, pointer.y) + Phaser.Math.DegToRad(-10 + i * 10);
            this.physics.velocityFromRotation(angle, weaponSpeed, weapon.body.velocity);
        }
    }

    dropItem(enemy) {
        const waveConfig = this.game.waveConfig?.getWaveConfig(this.wave);
        const itemConfig = waveConfig?.items || { dropRate: 0.05 };
        
        const rand = Math.random();
        if (rand < itemConfig.dropRate) {
            // 동적 가중치 계산
            const weights = itemConfig.weights || 
                this.game.waveConfig?.calculateDynamicWeights(
                    this.game.waveConfig.config.waves.default.items.dynamicWeights, 
                    this.wave, 
                    this.hp
                ) || {
                    weapon: 25,
                    hp: 25,
                    bomb: 25,
                    shield: 25
                };
            
            const type = this.weightedRandom(weights);
            let color;
            switch (type) {
                case 'weapon': color = 0x0000ff; break;
                case 'hp': color = 0x00ff00; break;
                case 'bomb': color = 0xffff00; break;
                case 'shield': color = 0xff00ff; break;  // 보라색
            }
            const item = this.add.rectangle(enemy.x, enemy.y, 20, 20, color);
            this.physics.add.existing(item);
            item.setData('type', type);
            this.items.add(item);
            
            // 아이템 반짝임 효과
            this.tweens.add({
                targets: item,
                alpha: 0.5,
                duration: 500,
                yoyo: true,
                repeat: -1
            });
        }
    }
    
    dropBossItem(x, y) {
        // 보스는 아이템 드롭 확정 (100%)
        const bossItemConfig = this.game.waveConfig?.getBossItemConfig();
        const weights = bossItemConfig?.weights || {
            weapon: 35,
            hp: 35,
            bomb: 15,
            shield: 15
        };
        
        const type = this.weightedRandom(weights);
        let color;
        switch (type) {
            case 'weapon': color = 0x0000ff; break;
            case 'hp': color = 0x00ff00; break;
            case 'bomb': color = 0xffff00; break;
            case 'shield': color = 0xff00ff; break;
        }
        
        const offsetX = Phaser.Math.Between(-50, 50);
        const offsetY = Phaser.Math.Between(-50, 50);
        const item = this.add.rectangle(x + offsetX, y + offsetY, 30, 30, color);
        this.physics.add.existing(item);
        item.setData('type', type);
        this.items.add(item);
        
        // 보스 아이템은 더 화려하게
        this.tweens.add({
            targets: item,
            scale: 1.2,
            alpha: 0.5,
            duration: 500,
            yoyo: true,
            repeat: -1
        });
    }
    
    weightedRandom(weights) {
        const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);
        const random = Math.random() * totalWeight;
        
        let accumulator = 0;
        for (const [key, weight] of Object.entries(weights)) {
            accumulator += weight;
            if (random < accumulator) {
                return key;
            }
        }
        return Object.keys(weights)[0];
    }

    endGame() {
        this.gameOver = true;
        this.physics.pause();
        this.player.setFillStyle(0xff0000);
        
        // 방어막 타이머 정리
        this.shieldTimers.forEach(timer => {
            if (timer) timer.remove();
        });
        this.shieldTimers = [];

        // 게임 오버 텍스트
        const gameOverText = this.add.text(this.scale.width/2, this.scale.height/2, 'GAME OVER', { 
            fontSize: '64px', 
            fill: '#ff0000',
            fontStyle: 'bold',
            stroke: '#ffffff',
            strokeThickness: 4
        }).setOrigin(0.5);
        
        // 깜빡임 효과
        this.tweens.add({
            targets: gameOverText,
            alpha: 0.5,
            duration: 500,
            yoyo: true,
            repeat: 2,
            onComplete: () => {
                // 플레이 시간 계산 (초)
                const playTime = (Date.now() - this.startTime) / 1000;
                
                // 랭킹 저장
                this.saveRanking(this.nickname, this.score, playTime);
                
                // 1.5초 후 랭킹 화면으로 이동
                this.time.delayedCall(1500, () => {
                    this.scene.start('RankingScene', {
                        nickname: this.nickname,
                        score: this.score,
                        wave: this.wave,
                        weaponLevel: this.weaponLevel,
                        playTime: playTime
                    });
                });
            }
        });
    }

    async saveRanking(name, score, playTime) {
        // API로 저장 시도
        const rankingData = {
            nickname: name,
            score: score,
            wave: this.wave,
            weapon_level: this.weaponLevel,
            play_time: playTime
        };
        
        const result = await ApiService.saveRanking(rankingData);
        
        // API 실패 시 로컬스토리지에 저장
        if (!result) {
            ApiService.saveLocalRanking(name, score, this.wave, this.weaponLevel, playTime);
        }
    }

    createShield() {
        // 방어막 설정 가져오기
        const shieldConfig = this.game.waveConfig?.getShieldConfig() || {
            count: 3,
            radius: 80,
            width: 30,
            height: 10,
            color: 0xff00ff,
            alpha: 0.8,
            rotationSpeed: 0.5,
            duration: 20000
        };
        
        // 기존 방어막이 없을 때만 생성
        if (this.shields.children.entries.length === 0) {
            for (let i = 0; i < shieldConfig.count; i++) {
                const angle = (360 / shieldConfig.count) * i;
                const shield = this.add.rectangle(0, 0, shieldConfig.width, shieldConfig.height, shieldConfig.color);
                shield.setAlpha(shieldConfig.alpha);
                
                this.physics.add.existing(shield);
                shield.body.setImmovable(true);
                
                // 방어막 데이터 설정
                shield.setData('angle', angle);
                shield.setData('radius', shieldConfig.radius);
                shield.setData('rotationSpeed', shieldConfig.rotationSpeed);
                
                this.shields.add(shield);
                
                // 빛나는 효과
                this.tweens.add({
                    targets: shield,
                    alpha: 0.4,
                    duration: 500,
                    yoyo: true,
                    repeat: -1
                });
            }
        }
        
        // 새로운 타이머 추가 (각 방어막 아이템마다 독립적인 지속시간)
        const timer = this.time.delayedCall(shieldConfig.duration, () => {
            // 이 타이머가 마지막 타이머인 경우에만 방어막 제거
            const index = this.shieldTimers.indexOf(timer);
            if (index > -1) {
                this.shieldTimers.splice(index, 1);
            }
            
            // 더 이상 활성화된 타이머가 없으면 방어막 제거
            if (this.shieldTimers.length === 0) {
                this.shields.clear(true, true);
            }
        });
        
        this.shieldTimers.push(timer);
        
        // 방어막 지속시간 표시 (선택사항)
        this.showShieldDuration(shieldConfig.duration);
    }

    updateShields() {
        this.shields.children.entries.forEach(shield => {
            const angle = shield.getData('angle');
            const radius = shield.getData('radius');
            const rotationSpeed = shield.getData('rotationSpeed');
            
            // 각도 업데이트
            const newAngle = angle + rotationSpeed;
            shield.setData('angle', newAngle);
            
            // 위치 업데이트
            const rad = Phaser.Math.DegToRad(newAngle);
            shield.x = this.player.x + Math.cos(rad) * radius;
            shield.y = this.player.y + Math.sin(rad) * radius;
            
            // 방어막 회전
            shield.rotation = rad + Math.PI / 2;
        });
    }
    
    showShieldDuration(duration) {
        // 방어막 지속시간 메시지 표시
        const message = `Shield +${duration/1000}s`;
        const text = this.add.text(this.player.x, this.player.y + 60, message, { 
            fontSize: '20px', 
            fill: '#ff00ff',
            fontStyle: 'bold',
            stroke: '#ffffff',
            strokeThickness: 2
        }).setOrigin(0.5);
        
        // 텍스트 페이드 아웃
        this.tweens.add({
            targets: text,
            y: text.y - 30,
            alpha: 0,
            duration: 1500,
            ease: 'Power2',
            onComplete: () => {
                text.destroy();
            }
        });
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        
        if (this.isPaused) {
            // 물리 엔진 일시정지
            this.physics.pause();
            
            // BGM 일시정지
            const bgm = this.sound.get('bgm');
            if (bgm && bgm.isPlaying) {
                bgm.pause();
            }
            
            // 일시정지 화면 생성
            this.createPauseScreen();
        } else {
            // 물리 엔진 재개
            this.physics.resume();
            
            // BGM 재개
            const bgm = this.sound.get('bgm');
            if (bgm && bgm.isPaused) {
                bgm.resume();
            }
            
            // 일시정지 화면 제거
            this.removePauseScreen();
        }
    }
    
    createPauseScreen() {
        const centerX = this.scale.width / 2;
        const centerY = this.scale.height / 2;
        
        // 반투명 검은 배경
        this.pauseOverlay = this.add.rectangle(
            centerX, 
            centerY, 
            this.scale.width, 
            this.scale.height, 
            0x000000, 
            0.7
        );
        this.pauseOverlay.setDepth(1000);
        
        // 일시정지 텍스트
        this.pauseText = this.add.text(centerX, centerY - 50, '게임 일시정지', {
            fontSize: this.scaleManager.getFontSize(48),
            fill: '#ffffff',
            fontStyle: 'bold',
            stroke: '#000000',
            strokeThickness: 4
        }).setOrigin(0.5);
        this.pauseText.setDepth(1001);
        
        // 조작 안내 (키보드 매니저에서 가져오기)
        const instructions = [];
        if (this.keyboardManager) {
            const actions = this.keyboardManager.getAllActionsForScene();
            actions.forEach(action => {
                if (action.action === 'togglePause') {
                    instructions.push(`${action.key}: 게임으로 돌아가기`);
                } else if (action.action === 'returnToMainMenu' && action.condition === 'isPaused') {
                    instructions.push(`${action.key}: ${action.description}`);
                } else if (action.action === 'toggleMusic') {
                    instructions.push(`${action.key}: ${action.description}`);
                }
            });
        }
        
        this.pauseInstructions = this.add.text(centerX, centerY + 30, instructions.join('\n'), {
            fontSize: this.scaleManager.getFontSize(24),
            fill: '#ffff00',
            align: 'center',
            lineSpacing: 10
        }).setOrigin(0.5);
        this.pauseInstructions.setDepth(1001);
    }
    
    removePauseScreen() {
        if (this.pauseOverlay) {
            this.pauseOverlay.destroy();
            this.pauseOverlay = null;
        }
        if (this.pauseText) {
            this.pauseText.destroy();
            this.pauseText = null;
        }
        if (this.pauseInstructions) {
            this.pauseInstructions.destroy();
            this.pauseInstructions = null;
        }
    }
    
    returnToMainMenu() {
        // 일시정지 화면 제거
        this.removePauseScreen();
        
        // BGM 정지
        const bgm = this.sound.get('bgm');
        if (bgm) {
            bgm.stop();
        }
        
        // 메인 메뉴로 이동
        this.scene.start('MainMenu');
    }
    
    toggleBGM() {
        const bgm = this.sound.get('bgm');
        if (bgm) {
            if (bgm.isPlaying) {
                bgm.pause();
                this.showMusicStatus('Music OFF');
            } else {
                bgm.resume();
                this.showMusicStatus('Music ON');
            }
        }
    }
    
    showMusicStatus(status) {
        // 음악 상태 메시지 표시
        const text = this.add.text(this.scale.width / 2, 100, status, { 
            fontSize: '24px', 
            fill: '#ffffff',
            fontStyle: 'bold',
            stroke: '#000000',
            strokeThickness: 3
        }).setOrigin(0.5);
        
        // 텍스트 페이드 아웃
        this.tweens.add({
            targets: text,
            alpha: 0,
            duration: 1500,
            ease: 'Power2',
            onComplete: () => {
                text.destroy();
            }
        });
    }

}