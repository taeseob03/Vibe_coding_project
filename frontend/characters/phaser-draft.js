import Phaser from 'phaser';

class MainScene extends Phaser.Scene {
  create() {
    // 임시 캐릭터 몸체 (나중에 이미지로 교체)
    const body = this.add.circle(0, 0, 40, 0xffcc99);
    // 임시 소품: 책
    const book = this.add.rectangle(45, 10, 25, 30, 0x3366cc);
    // 몸체와 소품을 한 묶음으로 → 같이 움직임
    const character = this.add.container(200, 200, [body, book]);

    // 좌우로 왔다갔다
    this.tweens.add({ targets: character, x: 500, duration: 2000, yoyo: true, repeat: -1 });
  }
}

new Phaser.Game({
  type: Phaser.AUTO,
  width: 700,
  height: 400,
  backgroundColor: '#f5f0e6',
  scene: MainScene,
});