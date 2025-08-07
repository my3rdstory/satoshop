export default class EnemyManager {
    constructor(scene) {
        this.scene = scene;
        this.config = null;
        this.enemies = {};
    }
    
    async load() {
        try {
            const response = await fetch('/static/game/selker/data/enemy-config.json');
            this.config = await response.json();
            return true;
        } catch (error) {
            console.error('Failed to load enemy config:', error);
            return false;
        }
    }
    
    preloadEnemies() {
        if (!this.config) return;
        
        // 모든 적 이미지 로드
        Object.entries(this.config.enemies).forEach(([key, enemy]) => {
            if (enemy.sprite && !this.scene.textures.exists(key)) {
                this.scene.load.svg(key, enemy.sprite, { 
                    width: enemy.size, 
                    height: enemy.size 
                });
            }
        });
    }
    
    getEnemyTypesForWave(wave) {
        // 웨이브에 맞는 적 타입 찾기
        for (const [range, types] of Object.entries(this.config.waveEnemyTypes)) {
            if (this.isWaveInRange(wave, range)) {
                return types;
            }
        }
        // 기본값
        return ['whale'];
    }
    
    getSpawnWeightsForWave(wave) {
        // 웨이브에 맞는 스폰 가중치 찾기
        for (const [range, weights] of Object.entries(this.config.spawnWeights)) {
            if (this.isWaveInRange(wave, range)) {
                return weights;
            }
        }
        // 기본값
        return { whale: 1.0 };
    }
    
    isWaveInRange(wave, range) {
        if (range.includes('+')) {
            const min = parseInt(range.replace('+', ''));
            return wave >= min;
        } else if (range.includes('-')) {
            const [min, max] = range.split('-').map(n => parseInt(n));
            return wave >= min && wave <= max;
        } else {
            return wave === parseInt(range);
        }
    }
    
    selectEnemyType(wave) {
        const weights = this.getSpawnWeightsForWave(wave);
        const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0);
        let random = Math.random() * totalWeight;
        
        for (const [type, weight] of Object.entries(weights)) {
            random -= weight;
            if (random <= 0) {
                return type;
            }
        }
        
        // 기본값
        return 'whale';
    }
    
    createEnemy(x, y, wave, gameScene = null) {
        // GameScene를 사용하도록 수정
        const scene = gameScene || this.scene;
        
        const enemyType = this.selectEnemyType(wave);
        const enemyConfig = this.config.enemies[enemyType];
        
        if (!enemyConfig) {
            console.error(`Enemy type ${enemyType} not found in config`);
            return null;
        }
        
        // 적 스프라이트 생성
        let enemy;
        if (scene.textures.exists(enemyType)) {
            enemy = scene.add.image(x, y, enemyType);
        } else {
            // 이미지가 없으면 색상으로 대체
            const color = enemyConfig.color || 0xff0000;
            enemy = scene.add.rectangle(x, y, enemyConfig.size, enemyConfig.size, color);
        }
        
        // 크기 설정
        if (enemy.setDisplaySize) {
            const size = scene.scaleManager ? 
                scene.scaleManager.getEnemySize() : 
                enemyConfig.size;
            enemy.setDisplaySize(size, size);
        }
        
        // 물리 속성 추가
        if (scene && scene.physics && scene.physics.add) {
            scene.physics.add.existing(enemy);
        } else {
            console.warn('Physics system not available for enemy creation');
        }
        
        // 적 데이터 저장
        enemy.setData('enemyType', enemyType);
        enemy.setData('hp', enemyConfig.hp);
        enemy.setData('damage', enemyConfig.damage);
        enemy.setData('speed', enemyConfig.speed);
        enemy.setData('score', enemyConfig.score);
        enemy.setData('name', enemyConfig.name);
        
        // 랜덤 회전 속도 설정 (초당 30~120도)
        const rotationSpeed = Phaser.Math.Between(30, 120);
        enemy.setData('rotationSpeed', rotationSpeed);
        
        // 회전 방향 랜덤 설정 (50% 확률로 시계/반시계)
        const rotationDirection = Math.random() < 0.5 ? 1 : -1;
        enemy.setData('rotationDirection', rotationDirection);
        
        return enemy;
    }
    
    getEnemyConfig(enemyType) {
        return this.config.enemies[enemyType];
    }
    
    getAllEnemyTypes() {
        return Object.keys(this.config.enemies);
    }
}