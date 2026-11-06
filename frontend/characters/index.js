import { composeCharacter } from '/static/assets/character/pixel-character.js';
import { api } from '/static/shared/api.js';

export const colorNames = { green: '초록', blue: '파랑', yellow: '노랑', pink: '분홍', purple: '보라' };

export function renderCharacter(target, color, nickname = '미리보기', appearance = {base:'female',hair_length:'long',hair_color:'black'}, major = 'computer') {
  const figure=document.createElement('div');figure.className='character-figure';
  const canvas=document.createElement('canvas');canvas.width=144;canvas.height=192;canvas.setAttribute('role','img');canvas.setAttribute('aria-label',`${nickname||'내'} 픽셀 캐릭터`);
  canvas.style.borderBottom='3px solid '+({green:'#91cfa0',blue:'#96c5ed',yellow:'#f1d878',pink:'#eeb0c3',purple:'#c4ade5'}[color]||'#91cfa0');
  const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;
  const pixels=composeCharacter(appearance,major);
  pixels.forEach((pixel,index)=>{if(pixel){context.fillStyle=pixel;context.fillRect(index%48*3,Math.floor(index/48)*3,3,3);}});
  const name=document.createElement('p');name.textContent=nickname||'미리보기';figure.append(canvas,name);target.replaceChildren(figure);
}

export async function mountCharacter(nickname) {
  const target = document.querySelector('#character');
  const refresh = document.querySelector('#character-refresh');
  let sequence = 0;
  async function load() {
    const current = ++sequence;
    refresh.disabled = true;
    try {
      const character = await api('/characters/me');
      if (current !== sequence) return;
      renderCharacter(target, character.color, nickname);
      const stats = document.createElement('ul');
      stats.className = 'character-stats';
      for (const stat of character.stats) {
        const item = document.createElement('li');
        const icon = document.createElement('span');
        icon.textContent = stat.icon;
        icon.style.color = stat.color;
        const value = document.createElement('span');
        value.textContent = ` ${stat.category} · ${stat.count}회 · 표시 단계 ${stat.level}`;
        item.append(icon, value);
        stats.append(item);
      }
      target.append(stats);
    } catch (error) {
      if (current !== sequence) return;
      target.textContent = `${error.message} 아래 버튼으로 다시 불러올 수 있어요.`;
    } finally {
      if (current === sequence) refresh.disabled = false;
    }
  }
  refresh.addEventListener('click', load);
  window.addEventListener('character:updated', load);
  await load();
}
