export default class KeyboardManager {
    constructor(scene) {
        this.scene = scene;
        this.config = null;
        this.keys = {};
        this.actions = {};
    }
    
    async load() {
        try {
            const response = await fetch('/static/game/selker/data/keyboard-config.json');
            this.config = await response.json();
            return true;
        } catch (error) {
            console.error('Failed to load keyboard config:', error);
            return false;
        }
    }
    
    setupKeys() {
        if (!this.config) return;
        
        const sceneName = this.scene.scene.key;
        const sceneKeys = this.config.scenes[sceneName] || {};
        const globalKeys = this.config.globalKeys || {};
        
        // Scene별 키 설정
        Object.entries(sceneKeys).forEach(([key, config]) => {
            const keyCode = this.getKeyCode(key);
            if (keyCode) {
                this.keys[key] = this.scene.input.keyboard.addKey(keyCode);
                this.actions[config.action] = {
                    key: key,
                    keyObject: this.keys[key],
                    config: config
                };
            }
        });
        
        // 글로벌 키 설정
        Object.entries(globalKeys).forEach(([key, config]) => {
            const keyCode = this.getKeyCode(key);
            if (keyCode) {
                this.keys[key] = this.scene.input.keyboard.addKey(keyCode);
                this.actions[config.action] = {
                    key: key,
                    keyObject: this.keys[key],
                    config: config
                };
                
                // preventDefault 설정
                if (config.preventDefault) {
                    this.scene.input.keyboard.on(`keydown-${key}`, (event) => {
                        event.preventDefault();
                    });
                }
            }
        });
    }
    
    getKeyCode(key) {
        // 특수 키 매핑
        const specialKeys = {
            'ESC': Phaser.Input.Keyboard.KeyCodes.ESC,
            'F11': Phaser.Input.Keyboard.KeyCodes.F11,
            'SPACE': Phaser.Input.Keyboard.KeyCodes.SPACE,
            'ENTER': Phaser.Input.Keyboard.KeyCodes.ENTER,
            'UP': Phaser.Input.Keyboard.KeyCodes.UP,
            'DOWN': Phaser.Input.Keyboard.KeyCodes.DOWN,
            'LEFT': Phaser.Input.Keyboard.KeyCodes.LEFT,
            'RIGHT': Phaser.Input.Keyboard.KeyCodes.RIGHT
        };
        
        if (specialKeys[key]) {
            return specialKeys[key];
        }
        
        // 일반 문자 키
        if (key.length === 1) {
            return Phaser.Input.Keyboard.KeyCodes[key.toUpperCase()];
        }
        
        return null;
    }
    
    isActionPressed(actionName) {
        const action = this.actions[actionName];
        if (!action) return false;
        
        // 조건 체크
        if (action.config.condition) {
            if (!this.checkCondition(action.config.condition)) {
                return false;
            }
        }
        
        return Phaser.Input.Keyboard.JustDown(action.keyObject);
    }
    
    checkCondition(condition) {
        // Scene의 속성을 체크
        switch (condition) {
            case 'isPaused':
                return this.scene.isPaused === true;
            case 'isGameOver':
                return this.scene.gameOver === true;
            default:
                return true;
        }
    }
    
    getActionKey(actionName) {
        const action = this.actions[actionName];
        return action ? action.key : null;
    }
    
    getSceneKeys() {
        const sceneName = this.scene.scene.key;
        return this.config?.scenes[sceneName] || {};
    }
    
    getKeyDescription(key) {
        const sceneKeys = this.getSceneKeys();
        return sceneKeys[key]?.description || '';
    }
    
    getAllActionsForScene() {
        const sceneName = this.scene.scene.key;
        const sceneKeys = this.config?.scenes[sceneName] || {};
        
        return Object.entries(sceneKeys).map(([key, config]) => ({
            key: key,
            action: config.action,
            description: config.description,
            condition: config.condition
        }));
    }
}