export default class ItemManager {
    constructor(scene) {
        this.scene = scene;
        this.config = null;
        this.itemGroups = {};
    }
    
    async load() {
        try {
            const response = await fetch('/static/game/selker/data/item-config.json');
            this.config = await response.json();
            return true;
        } catch (error) {
            console.error('Failed to load item config:', error);
            return false;
        }
    }
    
    getDropRate(wave) {
        const rates = this.config.dropRates.byWave;
        for (const [range, rate] of Object.entries(rates)) {
            if (this.isWaveInRange(wave, range)) {
                return rate;
            }
        }
        return this.config.dropRates.default;
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
    
    calculateItemWeights(wave, playerHp, weaponLevel) {
        const weights = {};
        const dynamicWeights = this.config.dynamicWeights;
        
        for (const [itemType, weightConfig] of Object.entries(dynamicWeights)) {
            let weight = weightConfig.base;
            
            // 웨이브에 따른 가중치 조정
            if (weightConfig.waveBonus) {
                weight += wave * weightConfig.waveBonus;
            }
            if (weightConfig.perWave) {
                weight += wave * weightConfig.perWave;
            }
            
            // HP에 따른 조정 (HP 아이템)
            if (weightConfig.lowHpBonus && playerHp < weightConfig.hpThreshold) {
                weight += weightConfig.lowHpBonus;
            }
            
            // 무기 레벨에 따른 조정
            if (weightConfig.weaponLevelBonus) {
                weight += weaponLevel * weightConfig.weaponLevelBonus;
            }
            
            // 최소/최대 가중치 제한
            if (weightConfig.minWeight) {
                weight = Math.max(weight, weightConfig.minWeight);
            }
            if (weightConfig.maxWeight) {
                weight = Math.min(weight, weightConfig.maxWeight);
            }
            
            // 상수 가중치
            if (weightConfig.constant) {
                weight = weightConfig.base;
            }
            
            weights[itemType] = Math.max(0, weight);
        }
        
        return weights;
    }
    
    selectRandomItem(wave, playerHp, weaponLevel) {
        const weights = this.calculateItemWeights(wave, playerHp, weaponLevel);
        const totalWeight = Object.values(weights).reduce((sum, w) => sum + w, 0);
        
        if (totalWeight === 0) return 'hp'; // 기본값
        
        let random = Math.random() * totalWeight;
        for (const [itemType, weight] of Object.entries(weights)) {
            random -= weight;
            if (random <= 0) {
                return itemType;
            }
        }
        
        return 'hp'; // 기본값
    }
    
    createItem(x, y, itemType = null, wave = 1, playerHp = 100, weaponLevel = 1, gameScene = null) {
        // GameScene를 사용하도록 수정
        const scene = gameScene || this.scene;
        
        // scene.physics가 없거나 null인 경우 체크
        if (!scene || !scene.physics || !scene.physics.add) {
            console.error('Scene or physics system not properly initialized');
            return null;
        }
        // 아이템 타입이 지정되지 않으면 랜덤 선택
        if (!itemType) {
            itemType = this.selectRandomItem(wave, playerHp, weaponLevel);
        }
        
        const itemConfig = this.config.items[itemType];
        if (!itemConfig) {
            console.error(`Item type ${itemType} not found in config`);
            return null;
        }
        
        // 아이템 그룹 생성 (아이템 본체 + 텍스트)
        const itemGroup = scene.add.container(x, y);
        
        // 아이템 모양 생성
        let itemShape;
        const color = parseInt(itemConfig.color);
        const size = itemConfig.size;
        
        switch (itemConfig.shape) {
            case 'circle':
                itemShape = scene.add.circle(0, 0, size/2, color);
                break;
            case 'star':
                itemShape = this.createStar(0, 0, size/2, color, scene);
                break;
            case 'hexagon':
                itemShape = this.createHexagon(0, 0, size/2, color, scene);
                break;
            case 'triangle':
                itemShape = this.createTriangle(0, 0, size, color, scene);
                break;
            case 'diamond':
                itemShape = this.createDiamond(0, 0, size, color, scene);
                break;
            case 'heart':
                itemShape = this.createHeart(0, 0, size, color, scene);
                break;
            default:
                itemShape = scene.add.rectangle(0, 0, size, size, color);
        }
        
        // 아이템 텍스트 추가
        if (itemConfig.text) {
            const itemText = scene.add.text(0, 0, itemConfig.text, {
                fontSize: itemConfig.textSize || '14px',
                fill: itemConfig.textColor || '#ffffff',
                fontStyle: 'bold',
                stroke: '#000000',
                strokeThickness: 1
            }).setOrigin(0.5);
            
            itemGroup.add([itemShape, itemText]);
        } else {
            itemGroup.add(itemShape);
        }
        
        // 물리 속성 추가
        scene.physics.add.existing(itemGroup);
        itemGroup.body.setSize(size, size);
        
        // 아이템 데이터 저장
        itemGroup.setData('itemType', itemType);
        itemGroup.setData('itemConfig', itemConfig);
        
        // 회전 애니메이션
        if (itemConfig.rotationSpeed) {
            scene.tweens.add({
                targets: itemGroup,
                rotation: Math.PI * 2,
                duration: 60000 / itemConfig.rotationSpeed,
                repeat: -1
            });
        }
        
        // 부유 애니메이션
        if (this.config.visualEffects?.floatAnimation && itemConfig.floatSpeed) {
            scene.tweens.add({
                targets: itemGroup,
                y: y - 10,
                duration: 2000 / (itemConfig.floatSpeed / 20),
                yoyo: true,
                repeat: -1,
                ease: 'Sine.easeInOut'
            });
        }
        
        // 발광 효과
        if (this.config.visualEffects?.glowEffect && itemShape.setStrokeStyle) {
            itemShape.setStrokeStyle(2, 0xffffff, 0.5);
        }
        
        return itemGroup;
    }
    
    createStar(x, y, radius, color, scene) {
        const points = [];
        const numPoints = 5;
        const angleStep = (Math.PI * 2) / numPoints;
        
        for (let i = 0; i < numPoints * 2; i++) {
            const angle = i * angleStep / 2 - Math.PI / 2;
            const r = i % 2 === 0 ? radius : radius * 0.5;
            points.push(x + Math.cos(angle) * r);
            points.push(y + Math.sin(angle) * r);
        }
        
        return scene.add.polygon(x, y, points, color);
    }
    
    createHexagon(x, y, radius, color, scene) {
        const points = [];
        for (let i = 0; i < 6; i++) {
            const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
            points.push(x + Math.cos(angle) * radius);
            points.push(y + Math.sin(angle) * radius);
        }
        return scene.add.polygon(x, y, points, color);
    }
    
    createTriangle(x, y, size, color, scene) {
        const points = [
            x, y - size/2,
            x - size/2, y + size/2,
            x + size/2, y + size/2
        ];
        return scene.add.polygon(x, y, points, color);
    }
    
    createDiamond(x, y, size, color, scene) {
        const points = [
            x, y - size/2,
            x + size/2, y,
            x, y + size/2,
            x - size/2, y
        ];
        return scene.add.polygon(x, y, points, color);
    }
    
    createHeart(x, y, size, color, scene) {
        // 간단한 하트 모양 (원 2개 + 삼각형)
        const group = scene.add.group();
        const circle1 = scene.add.circle(x - size/4, y - size/4, size/3, color);
        const circle2 = scene.add.circle(x + size/4, y - size/4, size/3, color);
        const triangle = this.createTriangle(x, y + size/4, size * 0.7, color, scene);
        group.addMultiple([circle1, circle2, triangle]);
        return group;
    }
    
    applyItemEffect(itemType, player, scene) {
        const itemConfig = this.config.items[itemType];
        if (!itemConfig) return;
        
        switch (itemConfig.effect) {
            case 'weaponLevelUp':
                if (scene.weaponLevel < 10) {
                    scene.weaponLevel++;
                    scene.weaponLevelText.setText('Weapon Lv: ' + scene.weaponLevel);
                }
                break;
                
            case 'heal':
                scene.hp = Math.min(100, scene.hp + itemConfig.healAmount);
                scene.hpText.setText('HP: ' + scene.hp);
                break;
                
            case 'screenClear':
                scene.screenBomb(itemConfig.damage);
                break;
                
            case 'shield':
                scene.activateShield(itemConfig);
                break;
                
            case 'speedBoost':
                scene.applySpeedBoost(itemConfig.speedMultiplier, itemConfig.duration);
                break;
                
            case 'multishot':
                scene.activateMultishot(itemConfig.duration);
                break;
                
            case 'bonusScore':
                scene.score += itemConfig.scoreAmount;
                scene.scoreText.setText('Score: ' + scene.score);
                break;
                
            case 'maxHpIncrease':
                scene.maxHp = (scene.maxHp || 100) + itemConfig.hpIncrease;
                scene.hp += itemConfig.hpIncrease;
                scene.hpText.setText('HP: ' + scene.hp);
                break;
        }
        
        // 아이템 획득 효과음 또는 시각 효과
        this.showPickupEffect(player.x, player.y, itemConfig, scene);
    }
    
    showPickupEffect(x, y, itemConfig, scene) {
        // 아이템 획득 시 파티클 효과
        const color = parseInt(itemConfig.color);
        for (let i = 0; i < 8; i++) {
            const particle = scene.add.circle(x, y, 3, color);
            const angle = (Math.PI * 2 * i) / 8;
            
            scene.tweens.add({
                targets: particle,
                x: x + Math.cos(angle) * 50,
                y: y + Math.sin(angle) * 50,
                alpha: 0,
                duration: 500,
                onComplete: () => particle.destroy()
            });
        }
        
        // 텍스트 표시
        const pickupText = scene.add.text(x, y - 30, itemConfig.name, {
            fontSize: '16px',
            fill: itemConfig.textColor || '#ffffff',
            stroke: '#000000',
            strokeThickness: 2
        }).setOrigin(0.5);
        
        scene.tweens.add({
            targets: pickupText,
            y: y - 60,
            alpha: 0,
            duration: 1000,
            onComplete: () => pickupText.destroy()
        });
    }
    
    shouldDropItem(wave) {
        const dropRate = this.getDropRate(wave);
        return Math.random() < dropRate;
    }
    
    dropBossItems(x, y, wave, playerHp, weaponLevel, gameScene) {
        const itemCount = this.config.dropRates.bossItemCount || 3;
        const items = [];
        
        for (let i = 0; i < itemCount; i++) {
            const angle = (Math.PI * 2 * i) / itemCount;
            const distance = 50;
            const itemX = x + Math.cos(angle) * distance;
            const itemY = y + Math.sin(angle) * distance;
            
            const item = this.createItem(itemX, itemY, null, wave, playerHp, weaponLevel, gameScene);
            if (item) {
                items.push(item);
            }
        }
        
        return items;
    }
}