export default class ShooterEnemy {
    constructor(scene, x, y, scaleManager) {
        this.scene = scene;
        this.scaleManager = scaleManager;
        
        // 적 설정 가져오기
        const enemyConfig = scene.game.waveConfig?.getEnemyStats('shooter') || {
            hp: 3,
            collisionDamage: 8,
            bulletDamage: 5,
            score: 30,
            color: 0xff6600,
            shootDelay: { min: 2000, max: 3000 },
            dropRate: 0.1
        };
        
        // 총 쏘는 적은 다른 색상과 모양
        this.size = scaleManager ? scaleManager.getShooterEnemySize() : 35;
        this.color = parseInt(enemyConfig.color) || 0xff6600;
        
        // 적 생성
        this.sprite = scene.add.rectangle(x, y, this.size, this.size, this.color);
        this.sprite.setStrokeStyle(2, 0xffff00); // 노란 테두리
        scene.physics.add.existing(this.sprite);
        
        // "Big Blocker" 텍스트 추가
        this.nameText = scene.add.text(x, y, 'Big Blocker', {
            fontSize: '10px',
            fill: '#ffffff',
            fontStyle: 'bold',
            stroke: '#000000',
            strokeThickness: 1
        }).setOrigin(0.5);
        
        // 총 쏘는 적 표시
        this.sprite.setData('isShooter', true);
        this.sprite.setData('shooter', this);
        
        // 발사 타이머
        const shootDelay = enemyConfig.shootDelay;
        this.shootTimer = scene.time.addEvent({
            delay: shootDelay.min + Math.random() * (shootDelay.max - shootDelay.min),
            callback: this.shoot,
            callbackScope: this,
            loop: true
        });
        
        // 체력과 기타 스텟
        this.hp = enemyConfig.hp;
        this.bulletDamage = enemyConfig.bulletDamage;
        this.score = enemyConfig.score;
        this.dropRate = enemyConfig.dropRate;
    }
    
    shoot() {
        if (!this.sprite || !this.sprite.active || this.scene.gameOver) return;
        
        // 플레이어 방향으로 탄환 발사
        const bulletSize = this.scaleManager ? this.scaleManager.getBulletSize() : 5;
        const bullet = this.scene.add.circle(this.sprite.x, this.sprite.y, bulletSize, 0xffff00);
        this.scene.physics.add.existing(bullet);
        
        // 플레이어 방향 계산
        const angle = Phaser.Math.Angle.Between(
            this.sprite.x, this.sprite.y,
            this.scene.player.x, this.scene.player.y
        );
        
        // 총알 속도를 적절한 고정값으로 설정 (화면 크기에 관계없이)
        const speed = 150;
        this.scene.physics.velocityFromRotation(angle, speed, bullet.body.velocity);
        
        // enemyWeapons 그룹에 추가
        this.scene.enemyWeapons.add(bullet);
        
        // 플레이어와 충돌 처리
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
        
        // 3초 후 탄환 제거
        this.scene.time.delayedCall(3000, () => {
            if (bullet && bullet.active) {
                bullet.destroy();
            }
        });
    }
    
    takeDamage() {
        this.hp--;
        
        // 피격 효과
        this.scene.tweens.add({
            targets: this.sprite,
            alpha: 0.5,
            duration: 100,
            yoyo: true,
            onComplete: () => {
                if (this.sprite && this.sprite.active) {
                    this.sprite.alpha = 1;
                }
            }
        });
        
        if (this.hp <= 0) {
            this.destroy();
            return true;
        }
        return false;
    }
    
    update() {
        // 텍스트 위치 업데이트
        if (this.nameText && this.sprite && this.sprite.active) {
            this.nameText.x = this.sprite.x;
            this.nameText.y = this.sprite.y;
        }
    }
    
    destroy() {
        if (this.shootTimer) {
            this.shootTimer.remove();
        }
        if (this.nameText) {
            this.nameText.destroy();
        }
        if (this.sprite) {
            // 점수 추가
            this.scene.score += this.score;
            this.scene.scoreText.setText('Score: ' + this.scene.score);
            
            // 아이템 드롭
            const rand = Math.random();
            if (rand < this.dropRate) {
                this.scene.dropItem(this.sprite);
            }
            
            this.sprite.destroy();
        }
    }
}