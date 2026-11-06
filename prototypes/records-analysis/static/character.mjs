// Final artwork can replace this catalog and renderer without changing posting or invitation flows.
export const assets = {
  body: '🧑',
  icons: { '술': '🍺', '공부': '📚', '연애': '♥', '운동': '🏋️' },
  heartColors: ['#aaa', '#f9a8d4', '#ec4899', '#be123c'],
};

export function countsFromProgress(progress) {
  return Object.fromEntries(progress.map(item => [item.category, item.count]));
}

export function renderCharacter(container, progress, emoji = assets.body) {
  container.replaceChildren();
  const body = document.createElement('span'); body.className = 'character-body'; body.textContent = emoji; container.append(body);
  for (const item of progress) {
    if (!item.level) continue;
    const effect = document.createElement('span');
    effect.className = `character-effect effect-${item.category}`;
    effect.textContent = assets.icons[item.category] || item.icon;
    effect.style.fontSize = `${24 + item.level * 8}px`;
    effect.style.color = item.color;
    effect.setAttribute('role', 'img'); effect.setAttribute('aria-label', `${item.category} 효과 ${item.level}단계`);
    container.append(effect);
  }
}
