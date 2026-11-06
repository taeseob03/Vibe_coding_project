import { api } from '/shared/api.js?v=local-web-1';

export const colorNames = { green: '초록', blue: '파랑', yellow: '노랑', pink: '분홍', purple: '보라' };

export function renderCharacter(target, color, nickname = '미리보기') {
  const figure = document.createElement('div');
  figure.className = 'character-figure';
  const avatar = document.createElement('div');
  avatar.className = `campus-avatar color-${Object.hasOwn(colorNames, color) ? color : 'green'}`;
  avatar.setAttribute('role', 'img');
  avatar.setAttribute('aria-label', `${colorNames[color] ?? '초록'}색 임시 캐릭터`);
  const name = document.createElement('p');
  name.textContent = nickname || '미리보기';
  figure.append(avatar, name);
  target.replaceChildren(figure);
}

export async function mountCharacter(nickname) {
  const target = document.querySelector('#character');
  const refresh = document.querySelector('#character-refresh');
  async function load() {
    refresh.disabled = true;
    try {
      const character = await api('/characters/me');
      renderCharacter(target, character.color, nickname);
      const effects = document.createElement('ul');
      effects.className = 'character-effects';
      const names = { book: '책', heart: '하트', dumbbell: '아령', palette: '팔레트', star: '별' };
      for (const effect of character.effects) {
        if (!effect.visible) continue;
        const item = document.createElement('li');
        item.textContent = `${names[effect.effect_id] ?? effect.effect_id} · 레벨 ${effect.level}`;
        effects.append(item);
      }
      if (!effects.children.length) {
        const empty = document.createElement('p');
        empty.textContent = '아직 획득한 효과가 없어요.';
        target.append(empty);
      } else {
        target.append(effects);
      }
    } catch (error) {
      target.textContent = `${error.message} 아래 버튼으로 다시 불러올 수 있어요.`;
    } finally {
      refresh.disabled = false;
    }
  }
  refresh.addEventListener('click', load);
  await load();
}
