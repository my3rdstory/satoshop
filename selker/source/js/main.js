import { gameConfig } from './config.js';
import BootScene from './scenes/BootScene.js';
import MainMenuScene from './scenes/MainMenuScene.js';
import SettingsScene from './scenes/SettingsScene.js';
import GameScene from './scenes/GameScene.js';
import RankingScene from './scenes/RankingScene.js';

// 모든 씬을 config에 추가
gameConfig.scene = [BootScene, MainMenuScene, SettingsScene, GameScene, RankingScene];

// 게임 시작
const game = new Phaser.Game(gameConfig);