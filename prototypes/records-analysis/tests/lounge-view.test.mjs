import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { createLounge } from '../static/lounge-view.mjs';
import { avatarFrames, walkingPose } from '../static/lounge-art.mjs';

test('pixel avatars use saved appearance and alternate legs, including idle pose', () => {
  const makeCanvas = () => {
    const pixels = [];
    return { pixels, getContext: () => ({ fillRect: (...args) => pixels.push(args) }) };
  };
  const compose = () => {
    const pixels = new Array(48 * 64).fill(null);
    pixels[58 * 48 + 18] = '#111'; pixels[58 * 48 + 28] = '#222';
    return pixels;
  };
  const frames = avatarFrames(compose, {}, 'computer', makeCanvas);
  assert.equal(frames.length, 3);
  assert.deepEqual(frames[0].pixels, [[18, 60, 1, 1], [28, 60, 1, 1]]);
  assert.deepEqual(frames[1].pixels, [[18, 61, 1, 1], [28, 59, 1, 1]]);
  assert.deepEqual(frames[2].pixels, [[18, 59, 1, 1], [28, 61, 1, 1]]);
  assert.equal(walkingPose(false, 12), 0);
  assert.deepEqual([0, .125, .25, .375].map(time => walkingPose(true, time)), [0, 1, 0, 2]);
});

test('lounge draws pixel scenery and characters, caches artwork, preserves movement and cleans up', async () => {
  const source = await readFile(new URL('../../../frontend/assets/character/pixel-character.js', import.meta.url), 'utf8');
  const renderer = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  const dom = new JSDOM('<canvas id="room"></canvas>', { pretendToBeVisual: true });
  globalThis.document = dom.window.document;
  const images = [], texts = [], requests = new Map(), appearances = [];
  let next = 0;
  globalThis.requestAnimationFrame = callback => { requests.set(++next, callback); return next; };
  globalThis.cancelAnimationFrame = id => requests.delete(id);
  dom.window.HTMLCanvasElement.prototype.getContext = function () {
    return {
      fillRect() {}, save() {}, restore() {}, translate() {}, scale() {},
      measureText: text => ({ width: text.length * 8 }),
      fillText: text => texts.push(text), drawImage: (...args) => images.push(args),
    };
  };
  const canvas = document.querySelector('canvas');
  Object.defineProperty(canvas, 'clientWidth', { value: 600 });
  canvas.getClientRects = () => [{}];
  const own = { id: 'me', nickname: 'student', major: 'computer',
    appearance: { base: 'male', hair_length: 'short', hair_color: 'blue' }, counts: { '연애': 5 } };
  const lounge = createLounge(canvas, { loadCharacter: async () => ({
    ...renderer, composeCharacter: (appearance, major) => {
      appearances.push({ appearance, major }); return renderer.composeCharacter(appearance, major);
    },
  }) });
  try {
    lounge.setPeople([own]);
    await new Promise(resolve => setTimeout(resolve, 0));
    for (let time = 0; time < 1600; time += 50) {
      const [id, frame] = requests.entries().next().value;
      requests.delete(id); frame(time);
    }
    assert.deepEqual(appearances, [{ appearance: own.appearance, major: 'computer' }]);
    assert.ok(texts.includes('INU CAMPUS') && texts.includes('student'));
    assert.ok(!texts.some(text => /\p{Extended_Pictographic}/u.test(text)));
    assert.ok(new Set(images.filter(args => args.length === 5).map(args => args[0])).size > 1);
    assert.ok(canvas.getAttribute('aria-label').includes('픽셀 캐릭터'));
    lounge.setPeople([{ ...own, appearance: { ...own.appearance, hair_color: 'pink' } }]);
    const [id, frame] = requests.entries().next().value;
    requests.delete(id); frame(1650);
    assert.equal(appearances.at(-1).appearance.hair_color, 'pink');
  } finally {
    lounge.destroy(); assert.equal(requests.size, 0); dom.window.close();
  }
});
