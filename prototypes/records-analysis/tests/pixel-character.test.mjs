import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('merged pixel stage renders account nickname without missing profile fields and stops cleanly', async () => {
  const source = await readFile(new URL('../../../frontend/assets/character/pixel-character.js', import.meta.url), 'utf8');
  const { createStage, composeCharacter } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  const callbacks = new Map(); let next = 0;
  const previousRequest = globalThis.requestAnimationFrame;
  const previousCancel = globalThis.cancelAnimationFrame;
  globalThis.requestAnimationFrame = callback => { callbacks.set(++next, callback); return next; };
  globalThis.cancelAnimationFrame = id => callbacks.delete(id);
  try {
    const labels = [];
    const context = {
      createLinearGradient: () => ({ addColorStop() {} }),
      fillRect() {}, measureText: text => ({ width: text.length * 8 }),
      fillText: text => labels.push(text),
    };
    const appearance = { base: 'female', hair_length: 'long', hair_color: 'black' };
    assert.equal(composeCharacter(appearance).length, 48 * 64);
    const stage = createStage({ width: 560, height: 390, getContext: () => context }, () => ({
      appearance, profile: { nickname: 'student' },
      levels: { drink: 5, study: 10, exercise: 0, love: 15 }, colors: { love: '#be123c' },
    }));
    stage.start(); stage.start();
    assert.equal(callbacks.size, 1);
    const [id, frame] = callbacks.entries().next().value;
    callbacks.delete(id); frame(1000);
    assert.ok(labels.includes('student'));
    assert.ok(labels.every(label => !label.includes('undefined')));
    stage.redraw(); stage.stop();
    assert.equal(callbacks.size, 0);
  } finally {
    globalThis.requestAnimationFrame = previousRequest;
    globalThis.cancelAnimationFrame = previousCancel;
  }
});
