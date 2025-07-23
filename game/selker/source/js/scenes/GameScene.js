import MobileControls from '../utils/MobileControls.js';
import ScaleManager from '../utils/ScaleManager.js';
import Boss from '../entities/Boss.js';
import ShooterEnemy from '../entities/ShooterEnemy.js';
import ApiService from '../services/api.js';

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
        this.waveTimer = 15;
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
    }

    preload() {
        this.load.html('nameform', 'nameform.html');
    }

    create() {
        const centerX = this.scale.width/2;
        const centerY = this.scale.height/2;
        
        // 스케일 매니저 생성
        this.scaleManager = new ScaleManager(this);
        
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
            delay: 15000,  // 15초마다 웨이브 증가
            callback: this.increaseWave,
            callbackScope: this,
            loop: true
        });
        
        // 1초마다 웨이브 타이머 업데이트
        this.time.addEvent({
            delay: 1000,
            callback: () => {
                if (!this.gameOver) {
                    this.waveTimer--;
                    if (this.waveTimer <= 0) {
                        this.waveTimer = 15;
                    }
                    this.waveTimerText.setText(`Next wave: ${this.waveTimer}s`);
                }
            },
            callbackScope: this,
            loop: true
        });

        this.input.on('pointerdown', (pointer) => {
            if (!this.gameOver) {
                this.fireWeapon(pointer);
            }
        });
        
        // 자동 발사 추가
        this.time.addEvent({
            delay: 500,
            callback: () => {
                if (!this.gameOver && this.enemies.children.entries.length > 0) {
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
                this.score += 10;
                this.scoreText.setText('Score: ' + this.score);
                
                // 일반 적만 아이템 드롭
                this.dropItem(enemy);
            }
        });

        this.physics.add.collider(this.player, this.enemies, (player, enemy) => {
            if (!this.gameOver) {
                let damage = 10;
                
                // 보스인 경우
                if (enemy.getData('isBoss')) {
                    damage = 15;
                }
                // 총 쏘는 적인 경우
                else if (enemy.getData('isShooter')) {
                    damage = 8;
                    const shooter = enemy.getData('shooter');
                    if (shooter) {
                        shooter.destroy();
                    }
                }
                // 일반 적
                else {
                    enemy.destroy();
                }
                
                this.hp -= damage;
                this.hpText.setText('HP: ' + this.hp);
                if (this.hp <= 0) {
                    this.endGame();
                }
            }
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
                    // 보스가 있으면 destroy 메서드 호출
                    this.enemies.children.each(enemy => {
                        if (enemy.getData('isBoss')) {
                            const boss = enemy.getData('boss');
                            if (boss) {
                                boss.destroy();
                            }
                        }
                    });
                    this.enemies.clear(true, true);
                    message = 'BOOM!';
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
        if (this.gameOver) {
            return;
        }

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
        if (this.gameOver) return;
        
        // 기본 스폰 수: 웨이브 수
        let spawnCount = this.wave;
        
        // 무기 레벨에 따른 추가 스폰 (무기 레벨 3 이상부터)
        if (this.weaponLevel > 2) {
            spawnCount += Math.floor((this.weaponLevel - 2) * 0.5);
        }
        
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

        // 웨이브 5 이상에서 30% 확률로 총 쏘는 적 생성
        if (this.wave >= 5 && Math.random() < 0.3) {
            const shooter = new ShooterEnemy(this, spawnX, spawnY, this.scaleManager);
            this.enemies.add(shooter.sprite);
        } else {
            // 일반 적
            let enemySize = this.scaleManager.getEnemySize();
            
            // 웨이브 10 이상에서 크기 20% 감소
            if (this.wave >= 10) {
                enemySize = this.scaleManager.getSmallEnemySize();
            }
            
            const enemy = this.add.rectangle(spawnX, spawnY, enemySize, enemySize, 0xff0000);
            this.physics.add.existing(enemy);
            this.enemies.add(enemy);
        }
    }

    increaseWave() {
        if (this.gameOver) return;
        
        // 보스 스폰 (웨이브가 끝날 때)
        this.spawnBoss();
        
        // 보스와 함께 추가 적들 스폰 (무기 레벨도 고려)
        let bossWaveSpawn = this.wave * 2;
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
        
        // 보스 생성
        this.boss = new Boss(this, spawnX, spawnY, this.wave, this.scaleManager);
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
        const rand = Math.random();
        // 아이템 드롭률 조정 (3% -> 5%)
        if (rand < 0.05) {
            // 웨이브에 따른 가중치 아이템 드롭
            const weights = {
                weapon: this.wave <= 3 ? 40 : 30,  // 초반엔 무기 드롭률 높음
                hp: this.hp < 50 ? 40 : 30,        // 체력 낮으면 회복 드롭률 높음
                bomb: this.wave >= 5 ? 30 : 20     // 후반엔 폭탄 드롭률 높음
            };
            
            const type = this.weightedRandom(weights);
            let color;
            switch (type) {
                case 'weapon': color = 0x0000ff; break;
                case 'hp': color = 0x00ff00; break;
                case 'bomb': color = 0xffff00; break;
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
        const weights = {
            weapon: 40,
            hp: 40,
            bomb: 20
        };
        
        const type = this.weightedRandom(weights);
        let color;
        switch (type) {
            case 'weapon': color = 0x0000ff; break;
            case 'hp': color = 0x00ff00; break;
            case 'bomb': color = 0xffff00; break;
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

}