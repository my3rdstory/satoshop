export default class ShooterEnemy {
    constructor(scene, x, y, scaleManager) {
        this.scene = scene;
        this.scaleManager = scaleManager;
        
        // 총 쏘는 적은 다른 색상과 모양
        this.size = scaleManager ? scaleManager.getShooterEnemySize() : 35;
        this.color = 0xff6600; // 주황색
        
        // 적 생성
        this.sprite = scene.add.rectangle(x, y, this.size, this.size, this.color);
        this.sprite.setStrokeStyle(2, 0xffff00); // 노란 테두리
        scene.physics.add.existing(this.sprite);
        
        // 총 쏘는 적 표시
        this.sprite.setData('isShooter', true);
        this.sprite.setData('shooter', this);
        
        // 발사 타이머
        this.shootTimer = scene.time.addEvent({
            delay: 2000 + Math.random() * 1000, // 2-3초마다
            callback: this.shoot,
            callbackScope: this,
            loop: true
        });
        
        // 체력 (일반 적보다 높음)
        this.hp = 3;
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
        
        const speed = this.scaleManager ? this.scaleManager.getBulletSpeed() : 250;
        this.scene.physics.velocityFromRotation(angle, speed, bullet.body.velocity);
        
        // 플레이어와 충돌 처리
        this.scene.physics.add.overlap(this.scene.player, bullet, () => {
            if (!this.scene.gameOver) {
                bullet.destroy();
                this.scene.hp -= 5;
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
    
    destroy() {
        if (this.shootTimer) {
            this.shootTimer.remove();
        }
        if (this.sprite) {
            // 점수 추가 (일반 적보다 높음)
            this.scene.score += 30;
            this.scene.scoreText.setText('Score: ' + this.scene.score);
            
            // 아이템 드롭률도 약간 높음
            const rand = Math.random();
            if (rand < 0.1) { // 10% 확률
                this.scene.dropItem(this.sprite);
            }
            
            this.sprite.destroy();
        }
    }
}