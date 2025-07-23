export default class WaveConfig {
    constructor() {
        this.config = null;
        this.loaded = false;
    }
    
    async load() {
        try {
            const response = await fetch('/static/game/selker/data/wave-config.json');
            this.config = await response.json();
            this.loaded = true;
            return true;
        } catch (error) {
            console.error('Failed to load wave config:', error);
            return false;
        }
    }
    
    getWaveConfig(wave) {
        if (!this.loaded || !this.config) return null;
        
        // 특정 웨이브 설정이 있으면 사용
        if (this.config.waves[wave.toString()]) {
            return this.config.waves[wave.toString()];
        }
        
        // 없으면 기본 설정 사용
        return this.generateDefaultConfig(wave);
    }
    
    generateDefaultConfig(wave) {
        const defaults = this.config.waves.default;
        const config = {
            spawnCount: Math.min(eval(defaults.spawnCountFormula.replace(/wave/g, wave)), defaults.maxSpawnCount),
            enemyTypes: defaults.enemyTypes,
            boss: {
                hp: eval(defaults.boss.hpFormula.replace('wave', wave)),
                damage: defaults.boss.damage,
                attackDelay: eval(defaults.boss.attackDelayFormula.replace('wave', wave)),
                radialBullets: eval(defaults.boss.radialBulletsFormula.replace('wave', wave)),
                bulletSpeed: defaults.boss.bulletSpeed,
                bulletDamage: defaults.boss.bulletDamage,
                missileDamage: defaults.boss.missileDamage,
                missileSpeed: defaults.boss.missileSpeed,
                scoreMultiplier: eval(defaults.boss.scoreMultiplierFormula.replace('wave', wave))
            },
            items: {
                dropRate: defaults.items.dropRate,
                weights: this.calculateDynamicWeights(defaults.items.dynamicWeights, wave)
            }
        };
        
        return config;
    }
    
    calculateDynamicWeights(dynamicWeights, wave, hp = 100) {
        const weights = {};
        
        for (const [key, config] of Object.entries(dynamicWeights)) {
            // 조건식 평가
            const condition = config.condition
                .replace('wave', wave)
                .replace('hp', hp);
            
            weights[key] = eval(condition) ? config.trueValue : config.falseValue;
        }
        
        return weights;
    }
    
    getEnemyStats(type) {
        return this.config?.enemyStats[type] || null;
    }
    
    getPlayerConfig() {
        return this.config?.player || { maxHp: 100, speed: 200 };
    }
    
    getShieldConfig() {
        return this.config?.shield || {
            count: 3,
            radius: 80,
            rotationSpeed: 0.5,
            duration: 20000,
            width: 30,
            height: 10,
            color: 0xff00ff,
            alpha: 0.8
        };
    }
    
    getWaveTimer() {
        return this.config?.waveTimer || 15;
    }
    
    getAutoFireDelay() {
        return this.config?.autoFireDelay || 500;
    }
    
    getBossItemConfig() {
        return this.config?.waves.default.bossItems || {
            dropCount: 3,
            weights: {
                weapon: 35,
                hp: 35,
                bomb: 15,
                shield: 15
            }
        };
    }
    
    getWeaponLevelBonus(weaponLevel) {
        const bonus = this.config?.waves.default.weaponLevelBonus;
        if (!bonus || weaponLevel < bonus.startLevel) return 0;
        
        return eval(bonus.bonusFormula.replace('weaponLevel', weaponLevel));
    }
    
    shouldReduceEnemySize(wave) {
        const reduction = this.config?.waves.default.enemySizeReduction;
        return reduction && wave >= reduction.startWave;
    }
    
    getEnemySizeReduction() {
        return this.config?.waves.default.enemySizeReduction?.reductionPercent || 0.2;
    }
    
    getBombConfig() {
        return this.config?.bomb || {
            bossDamagePercent: 0.5,
            explosionColor: 0xffff00,
            explosionRadius: 100,
            explosionDuration: 500
        };
    }
}