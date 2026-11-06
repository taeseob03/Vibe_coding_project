import { avatar } from './avatar.mjs';
export const assets = { body: '●', icons: { '술': '잔', '공부': '책', '연애': '♥', '운동': '아령' }, heartColors: ['#aaa','#f9a8d4','#ec4899','#be123c'] };
export const countsFromProgress = progress => Object.fromEntries(progress.map(item => [item.category,item.count]));
const instances = new WeakMap();
let myProfile = {};
window.addEventListener('campus:profile', event => { myProfile = event.detail; });

export function renderCharacter(container, progress) {
  const previous = instances.get(container);
  if (previous) previous.destroy(true);
  container.replaceChildren();
  const person = { ...myProfile };
  class MainScene extends Phaser.Scene {
    create() {
      this.add.ellipse(165, 208, 230, 40, 0xd8dfca);
      this.add.text(35, 33, '✦', { color: '#94ad90', fontSize: '22px' });
      this.add.text(277, 78, '✧', { color: '#b4b28a', fontSize: '26px' });
      const actor = avatar(this, person, progress, 165, 133, 1.12);
      this.tweens.add({ targets: actor, x: 174, duration: 2100, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
    }
  }
  const game = new Phaser.Game({ type: Phaser.CANVAS, width: 330, height: 270, parent: container,
    transparent: true, audio: { noAudio: true }, fps: { target: 30 }, scene: MainScene,
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }, banner: false });
  instances.set(container, game);
  container.setAttribute('aria-label', `${person.nickname || '내'} 캐릭터 · ${progress.map(item => `${item.category} ${item.count}`).join(', ')}`);
}
