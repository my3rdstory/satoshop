export default class Boss {
    constructor(scene, x, y, wave, scaleManager) {
        this.scene = scene;
        this.wave = wave;
        this.scaleManager = scaleManager;
        
        // 보스 크기와 색상
        this.size = scaleManager ? scaleManager.getBossSize() : 80;
        this.color = 0xff00ff;
        
        // 보스 체력 (웨이브에 따라 증가) - 난이도 하향
        this.maxHp = 50 + (wave * 30);  // 100 -> 50, 50 -> 30으로 감소
        this.hp = this.maxHp;
        
        // 보스 생성
        this.sprite = scene.add.rectangle(x, y, this.size, this.size, this.color);
        scene.physics.add.existing(this.sprite);
        this.sprite.body.setImmovable(true);
        
        // 보스 데이터 저장
        this.sprite.setData('isBoss', true);
        this.sprite.setData('boss', this);
        
        // 체력바 생성
        this.createHealthBar();
        
        // 보스 패턴 타이머 - 공격 주기 늘림
        this.attackTimer = scene.time.addEvent({
            delay: 4000 - (wave * 200),  // 첫 웨이브 4초, 점점 빨라짐
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
    
    takeDamage(damage) {
        this.hp -= damage * 1.5;  // 데미지 1.5배 증가 (보스가 더 빨리 죽음)
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
        const bullets = Math.min(4 + this.wave, 8);  // 첫 웨이브는 4발, 최대 8발
        for (let i = 0; i < bullets; i++) {
            const angle = (Math.PI * 2 / bullets) * i;
            const bullet = this.scene.add.circle(this.sprite.x, this.sprite.y, 10, 0xff00ff);
            this.scene.physics.add.existing(bullet);
            
            const speed = 150;  // 200 -> 150으로 감소
            bullet.body.setVelocity(
                Math.cos(angle) * speed,
                Math.sin(angle) * speed
            );
            
            // 충돌 처리
            this.scene.physics.add.overlap(this.scene.player, bullet, () => {
                if (!this.scene.gameOver) {
                    bullet.destroy();
                    this.scene.hp -= 10;  // 15 -> 10으로 감소
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
        
        // 추적 미사일
        const updateMissile = () => {
            if (missile && missile.body && this.scene.player) {
                this.scene.physics.moveToObject(missile, this.scene.player, 100);  // 150 -> 100으로 감소
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
                this.scene.hp -= 15;  // 20 -> 15로 감소
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
        
        // 플레이어 추적 (느리게)
        const bossSpeed = this.scaleManager ? this.scaleManager.getBossSpeed() : 20;
        this.scene.physics.moveToObject(this.sprite, this.scene.player, bossSpeed);
        
        // 체력바 위치 업데이트
        this.updateHealthBar();
    }
    
    destroy() {
        // 이미 제거된 경우 중복 실행 방지
        if (!this.sprite || !this.sprite.active) return;
        
        // 보스 격파 시 대량의 점수와 아이템
        this.scene.score += 500 * this.wave;
        this.scene.scoreText.setText('Score: ' + this.scene.score);
        
        // 보스 아이템 드롭 (확률 높음)
        for (let i = 0; i < 3; i++) {
            this.scene.dropBossItem(this.sprite.x, this.sprite.y);
        }
        
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