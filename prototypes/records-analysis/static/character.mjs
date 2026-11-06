// Final artwork can replace this catalog and renderer without changing posting or invitation flows.
export const assets = {
  body: '🧑',
  icons: { '술': '🍺', '공부': '📚', '연애': '♥', '운동': '🏋️' },
  heartColors: ['#aaa', '#f9a8d4', '#ec4899', '#be123c'],
};

// Keep existing stored category keys while presenting the current product terminology.
export const categoryLabel = category => category === '운동' ? '건강' : category;

export function countsFromProgress(progress) {
  return Object.fromEntries(progress.map(item => [item.category, item.count]));
}

const stages = new WeakMap();
const versions = new WeakMap();

export function renderCharacter(container, progress, emoji = assets.body, color, profile = {}) {
  stages.get(container)?.stop();
  const version = (versions.get(container) || 0) + 1;
  versions.set(container, version);
  container.replaceChildren();
  const body = document.createElement('span'); body.className = 'character-body'; body.textContent = emoji; container.append(body);
  const colors = {green:'#e0edcf',blue:'#dce8fa',yellow:'#fff0b9',pink:'#f9dce9',purple:'#e8dcfa'};
  if (colors[color]) { body.style.background = colors[color]; body.style.borderRadius = '50%'; }
  for (const item of progress) {
    if (!item.level) continue;
    const effect = document.createElement('span');
    effect.className = `character-effect effect-${item.category}`;
    effect.textContent = assets.icons[item.category] || item.icon;
    effect.style.fontSize = `${24 + item.level * 8}px`;
    effect.style.color = item.color;
    effect.setAttribute('role', 'img'); effect.setAttribute('aria-label', `${categoryLabel(item.category)} 효과 ${item.level}단계`);
    container.append(effect);
  }
  // The integrated server supplies C's pixel artwork; standalone tests keep the emoji fallback.
  if (typeof window.CanvasRenderingContext2D !== 'function') return;
  import('/assets/character/pixel-character.js').then(({ createStage }) => {
    if (versions.get(container) !== version || !container.isConnected) return;
    const canvas = document.createElement('canvas');
    canvas.width = 560; canvas.height = 450;
    canvas.style.cssText = 'width:100%;height:auto;image-rendering:pixelated';
    canvas.setAttribute('aria-label', '누적 활동 소품이 반영된 도트 캐릭터');
    const keys = { '술': 'drink', '공부': 'study', '운동': 'exercise', '연애': 'love' };
    const state = {
      profile: { nickname: profile.nickname || document.querySelector('#profile-name')?.textContent || '내 캐릭터', grade: profile.grade, major: profile.major },
      appearance: profile.appearance || { base: 'female', hair_length: 'long', hair_color: 'black' },
      // Keep the approved 1/5/10-count display stages while adapting C's five-unit renderer.
      levels: Object.fromEntries(progress.map(item => [keys[item.category], item.level * 5])),
      colors: Object.fromEntries(progress.map(item => [keys[item.category], item.color])),
      titleLevels: Object.fromEntries(progress.map(item => [keys[item.category], item.count])),
    };
    const stage = createStage(canvas, () => state);
    stages.set(container, stage);
    container.replaceChildren(canvas);
    container.classList.add('has-pixel-character');
    stage.start();
  }).catch(() => { /* Keep the working emoji renderer if artwork is unavailable. */ });
}
