export default class MobileControls {
    constructor(scene) {
        this.scene = scene;
        this.isMobile = this.checkMobile();
        this.joystick = null;
        this.joystickBase = null;
        this.joystickThumb = null;
        this.isDragging = false;
        this.joystickRadius = 50;
        this.thumbRadius = 25;
        
        if (this.isMobile) {
            this.createVirtualJoystick();
            // FIRE 버튼 제거 - 자동 발사만 사용
        }
    }

    checkMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (window.innerWidth <= 768);
    }

    createVirtualJoystick() {
        const x = this.scene.scale.width - 120;  // 오른쪽으로 이동
        const y = this.scene.scale.height - 120;
        
        // 조이스틱 베이스
        this.joystickBase = this.scene.add.circle(x, y, this.joystickRadius, 0x333333, 0.3);
        this.joystickBase.setScrollFactor(0);
        this.joystickBase.setDepth(1000);
        
        // 조이스틱 썸
        this.joystickThumb = this.scene.add.circle(x, y, this.thumbRadius, 0x666666, 0.5);
        this.joystickThumb.setScrollFactor(0);
        this.joystickThumb.setDepth(1001);
        
        // 조이스틱 안내 텍스트
        const moveText = this.scene.add.text(x, y - this.joystickRadius - 20, 'MOVE', { 
            fontSize: '16px', 
            fill: '#999' 
        }).setOrigin(0.5);
        moveText.setScrollFactor(0);
        moveText.setDepth(1000);
        
        // 조이스틱 터치 영역
        const touchArea = this.scene.add.circle(x, y, this.joystickRadius * 2, 0x000000, 0.01);
        touchArea.setInteractive();
        touchArea.setScrollFactor(0);
        touchArea.setDepth(999);
        
        // 조이스틱 드래그 이벤트
        touchArea.on('pointerdown', (pointer) => {
            this.isDragging = true;
        });
        
        this.scene.input.on('pointermove', (pointer) => {
            if (this.isDragging) {
                const dx = pointer.x - this.joystickBase.x;
                const dy = pointer.y - this.joystickBase.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance <= this.joystickRadius) {
                    this.joystickThumb.x = pointer.x;
                    this.joystickThumb.y = pointer.y;
                } else {
                    const angle = Math.atan2(dy, dx);
                    this.joystickThumb.x = this.joystickBase.x + Math.cos(angle) * this.joystickRadius;
                    this.joystickThumb.y = this.joystickBase.y + Math.sin(angle) * this.joystickRadius;
                }
            }
        });
        
        this.scene.input.on('pointerup', () => {
            this.isDragging = false;
            this.joystickThumb.x = this.joystickBase.x;
            this.joystickThumb.y = this.joystickBase.y;
        });
        
        // 화면 크기 변경 시 위치 조정
        this.scene.scale.on('resize', () => {
            const newX = this.scene.scale.width - 120;
            const newY = this.scene.scale.height - 120;
            this.joystickBase.x = newX;
            this.joystickBase.y = newY;
            this.joystickThumb.x = newX;
            this.joystickThumb.y = newY;
            touchArea.x = newX;
            touchArea.y = newY;
            moveText.x = newX;
            moveText.y = newY - this.joystickRadius - 20;
        });
    }
    
    
    getJoystickDirection() {
        if (!this.isMobile || !this.isDragging) {
            return { x: 0, y: 0 };
        }
        
        const dx = this.joystickThumb.x - this.joystickBase.x;
        const dy = this.joystickThumb.y - this.joystickBase.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
            return {
                x: dx / this.joystickRadius,
                y: dy / this.joystickRadius
            };
        }
        
        return { x: 0, y: 0 };
    }
}