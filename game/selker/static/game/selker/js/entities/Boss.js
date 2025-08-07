export default class Boss {
    constructor(scene, x, y, wave, scaleManager, waveConfig) {
        this.scene = scene;
        this.wave = wave;
        this.scaleManager = scaleManager;
        this.waveConfig = waveConfig;
        
        // 보스 크기와 색상
        this.size = scaleManager ? scaleManager.getBossSize() : 80;
        this.color = 0xff00ff;
        
        // 보스 체력 (웨이브 설정에서 가져오기)
        const bossConfig = waveConfig?.boss || { hp: 50 + (wave * 30) };
        this.maxHp = bossConfig.hp;
        this.hp = this.maxHp;
        this.damage = bossConfig.damage || 15;
        this.bulletDamage = bossConfig.bulletDamage || 10;
        this.missileDamage = bossConfig.missileDamage || 15;
        this.bulletSpeed = bossConfig.bulletSpeed || 150;
        this.missileSpeed = bossConfig.missileSpeed || 100;
        this.scoreMultiplier = bossConfig.scoreMultiplier || 500;
        
        // 보스 생성 - 주황색 노란테두리 사각형
        this.sprite = scene.add.rectangle(x, y, this.size, this.size, 0xff8800);
        this.sprite.setStrokeStyle(4, 0xffff00);
        scene.physics.add.existing(this.sprite);
        this.sprite.body.setImmovable(true);
        
        // 보스 데이터 저장
        this.sprite.setData('isBoss', true);
        this.sprite.setData('boss', this);
        
        // "Central Bank" 텍스트를 보스 몸통에 추가
        this.nameText = scene.add.text(x, y, 'Central Bank', {
            fontSize: '14px',
            fill: '#ffffff',
            fontStyle: 'bold',
            stroke: '#000000',
            strokeThickness: 2
        }).setOrigin(0.5);
        
        // 체력바 생성
        this.createHealthBar();
        
        // 보스 패턴 타이머 - 웨이브 설정에서 가져오기
        const attackDelay = bossConfig.attackDelay || (4000 - (wave * 200));
        this.attackTimer = scene.time.addEvent({
            delay: attackDelay,
            callback: this.attackPattern,
            callbackScope: this,
            loop: true
        });
    }
    
    createHealthBar() {
        const barWidth = 100;
        const barHeight = 10;
        const x = this.sprite.x;
        const y = this.sprite.y - this.size/2 - 20;
        
        // 체력바 배경
        this.healthBarBg = this.scene.add.rectangle(x, y, barWidth, barHeight, 0x333333);
        this.healthBarBg.setStrokeStyle(2, 0xffffff);
        
        // 체력바
        this.healthBar = this.scene.add.rectangle(x, y, barWidth, barHeight, 0xff0000);
        
        // 체력 텍스트
        this.healthText = this.scene.add.text(x, y - 15, `Boss HP: ${this.hp}/${this.maxHp}`, {
            fontSize: '16px',
            fill: '#fff'
        }).setOrigin(0.5);
    }
    
    updateHealthBar() {
        const percentage = this.hp / this.maxHp;
        this.healthBar.width = 100 * percentage;
        this.healthText.setText(`Boss HP: ${this.hp}/${this.maxHp}`);
        
        // 체력바 위치 업데이트
        const x = this.sprite.x;
        const y = this.sprite.y - this.size/2 - 20;
        this.healthBarBg.x = x;
        this.healthBarBg.y = y;
        this.healthBar.x = x;
        this.healthBar.y = y;
        this.healthText.x = x;
        this.healthText.y = y - 15;
    }
    
    takeDamage(damage, isRawDamage = false) {
        // isRawDamage가 true면 그대로 적용, false면 1.5배 증가
        this.hp -= isRawDamage ? damage : damage * 1.5;
        this.updateHealthBar();
        
        // 피격 효과
        this.scene.tweens.add({
            targets: this.sprite,
            alpha: 0.5,
            duration: 100,
            yoyo: true,
            onComplete: () => {
                this.sprite.alpha = 1;
            }
        });
        
        if (this.hp <= 0) {
            this.destroy();
            return true;
        }
        return false;
    }
    
    attackPattern() {
        if (!this.sprite || !this.sprite.body) return;
        
        const pattern = Phaser.Math.Between(1, 2);
        
        switch(pattern) {
            case 1:
                // 방사형 탄막
                this.radialShot();
                break;
            case 2:
                // 추적 미사일
                this.homingShot();
                break;
        }
    }
    
    radialShot() {
        const bullets = this.waveConfig?.boss?.radialBullets || Math.min(4 + this.wave, 8);
        for (let i = 0; i < bullets; i++) {
            const angle = (Math.PI * 2 / bullets) * i;
            const bullet = this.scene.add.circle(this.sprite.x, this.sprite.y, 10, 0xff00ff);
            this.scene.physics.add.existing(bullet);
            
            const speed = this.bulletSpeed;
            bullet.body.setVelocity(
                Math.cos(angle) * speed,
                Math.sin(angle) * speed
            );
            
            // enemyWeapons 그룹에 추가
            this.scene.enemyWeapons.add(bullet);
            
            // 충돌 처리
            this.scene.physics.add.overlap(this.scene.player, bullet, () => {
                if (!this.scene.gameOver) {
                    bullet.destroy();
                    this.scene.hp -= this.bulletDamage;
                    this.scene.hpText.setText('HP: ' + this.scene.hp);
                    if (this.scene.hp <= 0) {
                        this.scene.endGame();
                    }
                }
            });
            
            // 화면 밖으로 나가면 제거
            this.scene.time.delayedCall(5000, () => {
                if (bullet && bullet.body) {
                    bullet.destroy();
                }
            });
        }
    }
    
    homingShot() {
        const missile = this.scene.add.circle(this.sprite.x, this.sprite.y, 8, 0xffff00);
        this.scene.physics.add.existing(missile);
        
        // enemyWeapons 그룹에 추가
        this.scene.enemyWeapons.add(missile);
        
        // 추적 미사일
        const updateMissile = () => {
            if (missile && missile.body && this.scene.player) {
                this.scene.physics.moveToObject(missile, this.scene.player, this.missileSpeed);
            }
        };
        
        const missileTimer = this.scene.time.addEvent({
            delay: 50,
            callback: updateMissile,
            loop: true
        });
        
        // 충돌 처리
        this.scene.physics.add.overlap(this.scene.player, missile, () => {
            if (!this.scene.gameOver) {
                missile.destroy();
                missileTimer.remove();
                this.scene.hp -= this.missileDamage;
                this.scene.hpText.setText('HP: ' + this.scene.hp);
                if (this.scene.hp <= 0) {
                    this.scene.endGame();
                }
            }
        });
        
        // 5초 후 제거
        this.scene.time.delayedCall(5000, () => {
            if (missile && missile.body) {
                missile.destroy();
                missileTimer.remove();
            }
        });
    }
    
    update() {
        if (!this.sprite || !this.sprite.body) return;
        
        // "Central Bank" 텍스트 위치 업데이트
        if (this.nameText) {
            this.nameText.x = this.sprite.x;
            this.nameText.y = this.sprite.y;
        }
        
        // 플레이어 추적 (느리게)
        const bossSpeed = this.scaleManager ? this.scaleManager.getBossSpeed() : 20;
        this.scene.physics.moveToObject(this.sprite, this.scene.player, bossSpeed);
        
        // 체력바 위치 업데이트
        this.updateHealthBar();
    }
    
    destroy() {
        // 이미 제거된 경우 중복 실행 방지
        if (!this.sprite || !this.sprite.active) return;
        
        // "Central Bank" 텍스트 제거
        if (this.nameText) {
            this.nameText.destroy();
        }
        
        // 보스 격파 시 대량의 점수와 아이템
        this.scene.score += this.scoreMultiplier;
        this.scene.scoreText.setText('Score: ' + this.scene.score);
        
        // 보스 아이템 드롭 (dropBossItems가 이미 여러 아이템을 드롭함)
        this.scene.dropBossItem(this.sprite.x, this.sprite.y);
        
        // 격파 이펙트
        for (let i = 0; i < 20; i++) {
            const particle = this.scene.add.circle(
                this.sprite.x + Phaser.Math.Between(-40, 40),
                this.sprite.y + Phaser.Math.Between(-40, 40),
                5,
                0xff00ff
            );
            
            this.scene.tweens.add({
                targets: particle,
                scale: 0,
                alpha: 0,
                duration: 1000,
                onComplete: () => particle.destroy()
            });
        }
        
        // 정리
        if (this.attackTimer) {
            this.attackTimer.remove();
        }
        if (this.healthBarBg) {
            this.healthBarBg.destroy();
        }
        if (this.healthBar) {
            this.healthBar.destroy();
        }
        if (this.healthText) {
            this.healthText.destroy();
        }
        if (this.sprite) {
            this.sprite.destroy();
        }
        
        // 보스 참조 제거
        if (this.scene.boss === this) {
            this.scene.boss = null;
        }
    }
}