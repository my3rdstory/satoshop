export default class ScaleManager {
    constructor(scene) {
        this.scene = scene;
        this.baseWidth = 800;
        this.baseHeight = 600;
        this.scaleFactor = 1;
        
        this.calculateScale();
        
        // 화면 크기 변경 시 재계산
        this.scene.scale.on('resize', () => {
            this.calculateScale();
        });
    }
    
    calculateScale() {
        const width = this.scene.scale.width;
        const height = this.scene.scale.height;
        
        // 기본 해상도 대비 현재 화면 크기의 비율 계산
        const scaleX = width / this.baseWidth;
        const scaleY = height / this.baseHeight;
        
        // 더 작은 비율을 사용 (화면에 맞추기 위해)
        this.scaleFactor = Math.min(scaleX, scaleY);
        
        // 모바일에서는 추가로 크기 감소
        if (this.isMobile()) {
            this.scaleFactor *= 0.8;
        }
        
        // 최소/최대 크기 제한
        this.scaleFactor = Math.max(0.5, Math.min(1.5, this.scaleFactor));
    }
    
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (window.innerWidth <= 768);
    }
    
    // 크기 변환 메서드들
    getPlayerSize() {
        return 50 * this.scaleFactor;
    }
    
    getEnemySize() {
        return 30 * this.scaleFactor;
    }
    
    getSmallEnemySize() {
        return 24 * this.scaleFactor;
    }
    
    getShooterEnemySize() {
        return 35 * this.scaleFactor;
    }
    
    getBossSize() {
        return 80 * this.scaleFactor;
    }
    
    getWeaponSize() {
        return {
            width: 10 * this.scaleFactor,
            height: 30 * this.scaleFactor
        };
    }
    
    getItemSize() {
        return 20 * this.scaleFactor;
    }
    
    getBossItemSize() {
        return 30 * this.scaleFactor;
    }
    
    getBulletSize() {
        return 5 * this.scaleFactor;
    }
    
    getBossBulletSize() {
        return 10 * this.scaleFactor;
    }
    
    getMissileSize() {
        return 8 * this.scaleFactor;
    }
    
    // 속도 조정 (화면 크기에 따라)
    getPlayerSpeed() {
        return 200 * this.scaleFactor;
    }
    
    getEnemySpeed() {
        return 100 * this.scaleFactor;
    }
    
    getBossSpeed() {
        return 20 * this.scaleFactor;
    }
    
    getWeaponSpeed() {
        return 500 * this.scaleFactor;
    }
    
    getBulletSpeed() {
        return 250 * this.scaleFactor;
    }
    
    // UI 크기 조정
    getFontSize(baseSize) {
        return Math.floor(baseSize * this.scaleFactor) + 'px';
    }
}