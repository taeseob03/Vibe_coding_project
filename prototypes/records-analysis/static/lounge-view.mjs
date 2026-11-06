import { WIDTH, HEIGHT, destination, step, levelFor } from './lounge-engine.mjs';
import { avatarFrames, drawLoungeBackground, walkingPose } from './lounge-art.mjs';

export function createLounge(canvas, { loadCharacter = () => import('/assets/character/pixel-character.js') } = {}) {
  const ctx = canvas.getContext('2d');
  let users = [], last, time = 0, handle, artwork, background, destroyed = false;
  const sprites = new Map();
  Promise.resolve().then(loadCharacter).then(module => {
    if (!destroyed) { artwork = module; sprites.clear(); }
  }).catch(() => { /* Keep pixel placeholders when shared artwork cannot be loaded. */ });
  const appearanceOf = user => user.appearance || { base: 'female', hair_length: 'long', hair_color: 'black' };
  const spriteKey = user => JSON.stringify([appearanceOf(user), user.major]);
  function setPeople(people) {
    users = people.map((person, index) => {
      const previous = users.find(user => user.id === person.id);
      return { ...destination(), target: destination(), speed: 45 + index * 7, wait: 0, moving: false, direction: 1, ...previous, ...person };
    });
    const activeKeys = new Set(users.map(spriteKey));
    for (const key of sprites.keys()) if (!activeKeys.has(key)) sprites.delete(key);
    canvas.setAttribute('aria-label', users.length ? `${users.map(u => u.nickname).join(', ')}의 픽셀 캐릭터가 라운지를 자동으로 걸어 다닙니다.` : '라운지 멤버를 불러오는 중입니다.');
  }
  function framesFor(user) {
    const key = spriteKey(user);
    if (!sprites.has(key)) sprites.set(key, avatarFrames(artwork?.composeCharacter, appearanceOf(user), user.major));
    return sprites.get(key);
  }
  function draw() {
    if (!canvas.clientWidth) return;
    if (canvas.width !== WIDTH || canvas.height !== HEIGHT) { canvas.width = WIDTH; canvas.height = HEIGHT; }
    ctx.imageSmoothingEnabled = false;
    if (!background) {
      background = document.createElement('canvas'); background.width = WIDTH; background.height = HEIGHT;
      drawLoungeBackground(background.getContext('2d'));
    }
    ctx.drawImage(background, 0, 0);
    for (const [index, user] of [...users].sort((a, b) => a.y - b.y).entries()) {
      const x = Math.round(user.x), y = Math.round(user.y);
      ctx.fillStyle = '#756b5055'; ctx.fillRect(x - 19, y + 4, 38, 6);
      const pose = walkingPose(user.moving, time, index);
      const bob = user.moving && pose ? -2 : 0;
      ctx.save(); ctx.translate(x, y + bob); ctx.scale(user.direction, 1);
      ctx.drawImage(framesFor(user)[pose], -34, -85, 68, 96);
      ctx.restore();
      if (artwork?.drawSprite) {
        const keys = { '술': 'drink', '공부': 'study', '운동': 'exercise', '연애': 'love' };
        const slots = { '술': [-43, -23], '공부': [28, -23], '운동': [-44, -62], '연애': [24, -90] };
        for (const [category, count] of Object.entries(user.counts || {})) {
          const level = levelFor(count); if (!level || !keys[category]) continue;
          const [dx, dy] = slots[category];
          artwork.drawSprite(ctx, keys[category], x + dx, y + dy + bob, 1 + level * .3,
            category === '연애' ? { R: ['#aaa', '#f9a8d4', '#ec4899', '#be123c'][level] } : undefined);
        }
      }
      ctx.font = '14px "Campus Pixel", monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      const width = ctx.measureText(user.nickname).width + 16;
      ctx.fillStyle = '#fff5dfed'; ctx.fillRect(x - width / 2, y + 15, width, 22);
      ctx.fillStyle = '#d1b991'; ctx.fillRect(x - width / 2, y + 35, width, 2);
      ctx.fillStyle = '#493c30'; ctx.fillText(user.nickname, x, y + 26);
    }
  }
  function frame(now) {
    const elapsed = last === undefined ? 0 : (now - last) / 1000; last = now;
    if (!document.hidden && canvas.getClientRects().length && !canvas.closest('[inert]')) {
      time += Math.min(elapsed, .05); users.forEach(user => step(user, elapsed)); draw();
    }
    handle = requestAnimationFrame(frame);
  }
  const resetClock = () => { last = undefined; };
  document.addEventListener('visibilitychange', resetClock); handle = requestAnimationFrame(frame);
  return { setPeople, destroy() { destroyed = true; cancelAnimationFrame(handle); sprites.clear(); background = null; document.removeEventListener('visibilitychange', resetClock); } };
}
