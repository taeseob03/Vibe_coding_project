import { WIDTH, HEIGHT, destination, step, levelFor } from './lounge-engine.mjs';
import { assets } from './character.mjs';

export function createLounge(canvas) {
  const ctx = canvas.getContext('2d');
  let users = [], last, time = 0, handle;
  function setPeople(people) {
    users = people.map((person, index) => {
      const previous = users.find(user => user.id === person.id);
      return { ...destination(), target: destination(), speed: 45 + index * 7, wait: 0, moving: false, direction: 1, ...previous, ...person };
    });
    canvas.setAttribute('aria-label', users.length ? `${users.map(u => u.nickname).join(', ')}의 캐릭터가 라운지를 자동으로 돌아다닙니다.` : '라운지 멤버를 불러오는 중입니다.');
  }
  function emoji(text, x, y, size) {
    ctx.font = `${size}px "Segoe UI Emoji", "Apple Color Emoji", sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, x, y);
  }
  function draw() {
    const w = Math.round(canvas.clientWidth * Math.min(devicePixelRatio || 1, 2));
    if (!w) return;
    const h = Math.round(w * HEIGHT / WIDTH);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    ctx.setTransform(w / WIDTH, 0, 0, h / HEIGHT, 0, 0);
    ctx.fillStyle = '#e6efdf'; ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.fillStyle = '#d6cab6'; ctx.fillRect(0, 240, WIDTH, 95); ctx.fillRect(405, 120, 90, 400);
    for (const [icon,x,y,size] of [['🏫',450,65,85],['🌳',70,75,65],['🌳',830,75,65],['🪑',220,100,42],['🪑',680,100,42],['🌷',100,445,30],['🌼',800,445,30]]) emoji(icon,x,y,size);
    for (const [index,user] of [...users].sort((a,b)=>a.y-b.y).entries()) {
      ctx.save(); ctx.translate(user.x,user.y);
      ctx.fillStyle = 'rgba(30,50,30,.15)'; ctx.beginPath(); ctx.ellipse(0,18,23,7,0,0,Math.PI*2); ctx.fill();
      ctx.translate(0,user.moving ? Math.sin(time*12+index)*3 : 0);
      ctx.save(); ctx.scale(user.direction,1); emoji(user.emoji || assets.body,0,-10,44); ctx.restore();
      const slots = { '술': [-33,6], '공부': [33,6], '연애': [0,-55], '운동': [0,31] };
      for (const [category,count] of Object.entries(user.counts || {})) {
        const level = levelFor(count); if (!level || !slots[category]) continue;
        const [x,y] = slots[category]; ctx.fillStyle = category === '연애' ? assets.heartColors[level] : '#27364b';
        emoji(assets.icons[category],x,y,category === '연애' ? 17+level*6 : 16+level*4);
      }
      ctx.fillStyle='#243047';ctx.font='bold 16px sans-serif';ctx.textAlign='center';ctx.fillText(user.nickname,0,67);ctx.restore();
    }
  }
  function frame(now) {
    const elapsed = last === undefined ? 0 : (now-last)/1000; last=now;
    if (!document.hidden && canvas.getClientRects().length && !canvas.closest('[inert]')) {
      time+=Math.min(elapsed,.05); users.forEach(user=>step(user,elapsed)); draw();
    }
    handle=requestAnimationFrame(frame);
  }
  const resetClock=()=>{last=undefined;};
  document.addEventListener('visibilitychange',resetClock);handle=requestAnimationFrame(frame);
  return { setPeople, destroy() {cancelAnimationFrame(handle);document.removeEventListener('visibilitychange',resetClock);} };
}
