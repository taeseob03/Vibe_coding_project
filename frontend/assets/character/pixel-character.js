// 픽셀 캐릭터 렌더러 (개발 계획 7.2 · 7.4)
// 레이어: 뒷머리 → 몸·과잠 → 얼굴 → 앞머리 → 카테고리 소품
// 최종 이미지가 준비되면 composeCharacter / SPRITES 부분만 이미지 로딩으로 교체합니다.

export const HAIR = {
  black:  { name: '검정',   hi: '#5d5262', base: '#3b3340', sh: '#28212c', deep: '#1a141d', out: '#0e0a10' },
  brown:  { name: '갈색',   hi: '#b07a4c', base: '#7d4f2e', sh: '#5a361e', deep: '#3e2313', out: '#24130a' },
  blonde: { name: '금발',   hi: '#fbe6a0', base: '#ecc464', sh: '#c99a3c', deep: '#9a7024', out: '#5a3e0e' },
  red:    { name: '빨강',   hi: '#ec8670', base: '#c4452f', sh: '#922f20', deep: '#6a1e14', out: '#3e0e08' },
  blue:   { name: '파랑',   hi: '#93b0f4', base: '#5172d4', sh: '#3a539e', deep: '#283a74', out: '#121c44' },
  pink:   { name: '분홍',   hi: '#ffc9da', base: '#f295b4', sh: '#d4678c', deep: '#a8466a', out: '#5c1e3a' },
  silver: { name: '은발',   hi: '#ececf4', base: '#c2c2ce', sh: '#94949f', deep: '#6c6c78', out: '#34343e' },
};
export const CATS = [
  { key: 'drink',    name: '술',   item: '술병', unit: '병' },
  { key: 'study',    name: '공부', item: '책',   unit: '권' },
  { key: 'exercise', name: '운동', item: '덤벨', unit: '개' },
  { key: 'love',     name: '연애', item: '하트', unit: '개' },
];

// 소품 규칙: 단계 = floor(레벨 / 5), 개수 최대 3, 크기 1.0배부터 단계마다 +0.15 (최대 1.6배)
export const tierOf = (lv) => Math.floor(lv / 5);
export const countOf = (tier) => Math.min(tier, 3);
export const scaleOf = (tier) => tier <= 0 ? 0 : Math.min(1 + 0.15 * (tier - 1), 1.6);

// 칭호 규칙: 5레벨 "xx입문자", 10레벨 "xx의 중수", 15레벨 "xx의 고수", 20레벨 이상 "xx짱"
export function titleOf(name, level) {
  const tier = tierOf(level);
  if (tier <= 0) return null;
  return [`${name}입문자`, `${name}의 중수`, `${name}의 고수`][tier - 1] ?? `${name}짱`;
}
const TITLE_COLORS = { drink: '#2e7c48', study: '#2a4c9c', exercise: '#3a3a44', love: '#c22f52' };

// ───────────────────────── 픽셀 캐릭터 ─────────────────────────
const W = 48, H = 64;
const SKIN = { b: '#ffe2c8', s: '#f3c19f', o: '#5c3626' };
const OUT = '#2b1d1a';
const newL = () => new Array(W * H).fill(null);
const put = (l, x, y, c) => { if (x >= 0 && x < W && y >= 0 && y < H) l[y * W + x] = c; };
const at = (l, x, y) => (x >= 0 && x < W && y >= 0 && y < H) ? l[y * W + x] : null;
const inE = (x, y, cx, cy, rx, ry) => { const dx = (x + .5 - cx) / rx, dy = (y + .5 - cy) / ry; return dx * dx + dy * dy <= 1; };

function outlined(l, col) {
  const o = l.slice();
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (l[y * W + x]) continue;
    if (at(l, x - 1, y) || at(l, x + 1, y) || at(l, x, y - 1) || at(l, x, y + 1)) o[y * W + x] = col;
  }
  return o;
}
function mirror(map) { const r = {}; for (const [x, v] of Object.entries(map)) r[47 - x] = v; return r; }

function backHair(len, P) {
  const l = newL();
  const bottom = { short: 29, medium: 41, long: 55 }[len];
  for (let y = 3; y <= bottom; y++) for (let x = 0; x < W; x++) {
    let inside;
    if (y <= 21 || len === 'short') inside = inE(x, y, 24, 21, 16.5, 16.5);
    else {
      const hw = len === 'long' ? 16.5 + Math.max(0, y - 30) * 0.17 : 16.5 - (y - 21) * 0.06;
      inside = Math.abs(x + .5 - 24) <= hw;
    }
    if (len !== 'short' && y > bottom - [0, 1, 2, 1][x % 4]) inside = false;
    if (!inside) continue;
    const strand = (x * 3 + Math.floor(y / 4)) % 5 === 0;
    put(l, x, y, strand ? P.deep : P.sh);
  }
  return outlined(l, P.out);
}

// 학과별 과잠 색 (컴퓨터공학과 = 임베디드 디자인의 검정 버전)
export const DEPTS = {
  embedded: { name: '임베디드시스템공학과', letter: 'E',
    J: { hi: '#b4def7', b: '#8ccbf0', s: '#62a5d1', sl: '#f6f8fb', sls: '#c9d3de', rib: '#1f3a66', st: '#f6f8fb', mark: '#1f3a66' } },
  computer: { name: '컴퓨터공학과', letter: 'C',
    J: { hi: '#3e3e48', b: '#2a2a31', s: '#1a1a1f', sl: '#f6f8fb', sls: '#c9d3de', rib: '#1a1a1f', st: '#f6f8fb', mark: '#f6f8fb' } },
  ict: { name: '정보통신공학과', letter: 'I',
    J: { hi: '#babcc4', b: '#9b9ea8', s: '#767983', sl: '#9b9ea8', sls: '#767983', rib: '#4a4c56', st: '#dcdde2', mark: '#ffffff' } },
};
const PLAIN = { hi: '#ffffff', b: '#f4f2ee', s: '#d6d2ca', sl: '#f4f2ee', sls: '#d6d2ca', rib: '#d6d2ca', st: '#f4f2ee', mark: null };
const LETTERS = { E: ['###', '#..', '##.', '#..', '###'], C: ['.##', '#..', '#..', '#..', '.##'], I: ['###', '.#.', '.#.', '.#.', '###'] };

function body(base, dept) {
  const l = newL();
  const rect = (x0, y0, x1, y1, fn) => { for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) put(l, x, y, typeof fn === 'function' ? fn(x, y) : fn); };
  const D = DEPTS[dept], J = D ? D.J : PLAIN;
  const hem = base === 'male' ? 50 : 48;
  rect(21, 36, 26, 39, (x) => x >= 25 ? SKIN.s : SKIN.b); // 목

  // ── 과잠 몸통
  const jacket = (x) => x >= 29 ? J.s : x <= 17 ? J.hi : J.b;
  rect(18, 39, 29, 39, jacket);
  rect(16, 40, 31, hem, jacket);
  rect(22, 39, 25, 40, '#ffffff'); rect(23, 41, 24, 41, '#ffffff'); // 안에 입은 흰 티
  for (const [x, y] of [[20, 39], [21, 39], [26, 39], [27, 39], [21, 40], [26, 40], [22, 41], [25, 41]]) put(l, x, y, J.rib); // V 카라
  rect(24, 42, 24, hem - 2, J.s); // 여밈선
  rect(16, hem - 1, 31, hem - 1, J.st); rect(16, hem, 31, hem, J.rib); // 밑단 시보리
  if (D) LETTERS[D.letter].forEach((row, ry) => [...row].forEach((ch, rx) => { if (ch === '#') put(l, 18 + rx, 42 + ry, J.mark); })); // 가슴 이니셜

  // ── 소매 (+ 시보리) 와 손
  const cuff = 47;
  rect(12, 40, 15, cuff - 2, (x) => x === 15 ? J.sls : J.sl);
  rect(32, 40, 35, cuff - 2, (x) => x === 35 ? J.sls : J.sl);
  rect(12, cuff - 1, 15, cuff - 1, J.st); rect(32, cuff - 1, 35, cuff - 1, J.st);
  rect(12, cuff, 15, cuff, J.rib); rect(32, cuff, 35, cuff, J.rib);
  rect(12, 48, 15, 50, (x) => x === 15 ? SKIN.s : SKIN.b); rect(32, 48, 35, 50, (x) => x === 35 ? SKIN.s : SKIN.b);
  put(l, 12, 50, null); put(l, 15, 50, null); put(l, 32, 50, null); put(l, 35, 50, null);

  if (base === 'male') {
    const pants = (x) => x >= 29 || x === 22 ? '#3c4660' : '#56637f'; // 청바지
    rect(16, 51, 31, 56, pants);
    rect(23, 53, 24, 56, null);
    rect(15, 57, 22, 58, '#2c2c34'); rect(25, 57, 32, 58, '#2c2c34');
    rect(15, 59, 22, 59, '#e9e9ee'); rect(25, 59, 32, 59, '#e9e9ee');
    put(l, 15, 57, null); put(l, 32, 57, null);
    rect(17, 57, 18, 57, '#55555f'); rect(27, 57, 28, 57, '#55555f');
  } else {
    const skirtW = { 49: [16, 31], 50: [16, 31], 51: [15, 32], 52: [15, 32], 53: [14, 33] };
    for (const [y, [a, b]] of Object.entries(skirtW)) rect(a, +y, b, +y, (x) => (x % 3 === 0 ? '#2b2c48' : '#3d3f63'));
    rect(18, 54, 21, 55, (x) => x === 21 ? SKIN.s : SKIN.b); rect(26, 54, 29, 55, (x) => x === 29 ? SKIN.s : SKIN.b);
    rect(18, 56, 21, 57, '#fbfbff'); rect(26, 56, 29, 57, '#fbfbff');
    rect(17, 58, 22, 59, '#4d2f2a'); rect(25, 58, 30, 59, '#4d2f2a');
    put(l, 17, 58, null); put(l, 30, 58, null);
    put(l, 19, 58, '#6e4640'); put(l, 27, 58, '#6e4640');
  }
  return outlined(l, OUT);
}

function head(base, P) {
  const l = newL();
  const face = (x, y) => inE(x, y, 24, 26, 12.5, 13);
  if (base === 'male') { // 귀
    for (const ex of [10.5, 37.5]) for (let y = 26; y <= 32; y++) for (let x = 8; x <= 40; x++)
      if (inE(x, y, ex, 29.5, 2.2, 3.2)) put(l, x, y, SKIN.b);
    put(l, 10, 29, SKIN.s); put(l, 10, 30, SKIN.s); put(l, 37, 29, SKIN.s); put(l, 37, 30, SKIN.s);
  }
  for (let y = 12; y <= 39; y++) for (let x = 0; x < W; x++) {
    if (!face(x, y)) continue;
    put(l, x, y, (!face(x + 2, y) || !face(x, y + 2)) ? SKIN.s : SKIN.b);
  }
  // 눈 (O 외곽선, I 진한 홍채, M 중간, L 밝은, W 하이라이트)
  const EYE = ['OOOOO', 'IIIWW', 'IIIWW', 'IMIII', 'MLLMI', '.OOO.'];
  const iris = base === 'male' ? { I: '#3e2a22', M: '#6e4a38', L: '#a77c5a' } : { I: '#4a2a2e', M: '#80505a', L: '#c48a92' };
  const C = { O: '#24160f', W: '#ffffff', ...iris };
  const drawEye = (x0, flip) => EYE.forEach((row, ry) => [...row].forEach((ch, rx) => {
    if (ch !== '.') put(l, flip ? x0 + 4 - rx : x0 + rx, 26 + ry, C[ch]);
  }));
  drawEye(15, false); drawEye(28, true);
  if (base === 'female') { // 속눈썹
    put(l, 14, 26, C.O); put(l, 13, 25, C.O); put(l, 33, 26, C.O); put(l, 34, 25, C.O);
  }
  // 눈썹
  if (base === 'male') { for (let x = 15; x <= 19; x++) { put(l, x, 23, P.out); put(l, 47 - x, 23, P.out); } put(l, 15, 24, P.out); put(l, 32, 24, P.out); }
  else { for (let x = 16; x <= 19; x++) { put(l, x, 23, P.deep); put(l, 47 - x, 23, P.deep); } }
  // 볼터치·코·입
  for (const x of [14, 15, 16, 31, 32, 33]) put(l, x, 32, '#f7aeb0');
  put(l, 24, 31, SKIN.s);
  put(l, 23, 34, base === 'male' ? '#a8503f' : '#d45f68'); put(l, 24, 34, base === 'male' ? '#a8503f' : '#d45f68');
  return outlined(l, OUT);
}

const BANGS = {
  male:   [28, 28, 27, 25, 22, 21, 22, 23, 21, 20, 21, 22, 20, 19, 20, 21, 22, 20, 19, 20, 21, 22, 21, 20, 21, 23, 25, 27, 28, 28],
  female: [31, 31, 30, 27, 24, 22, 23, 22, 21, 22, 23, 22, 21, 22, 23, 23, 22, 21, 22, 23, 22, 21, 22, 23, 22, 23, 27, 30, 31, 31],
};
const SIDE_LOCKS = {
  short: {},
  medium: { 9: 34, 10: 37, 11: 38, 12: 35 },
  long: { 8: 40, 9: 44, 10: 47, 11: 46, 12: 42 },
};
const SPIKES = [[11, 6, 3], [15, 2, 3.2], [20, 1, 3], [26, 1, 3], [31, 2, 3.2], [36, 5, 3]];

function frontHair(base, len, P) {
  const m = newL();
  const bangs = BANGS[base];
  for (let x = 9; x <= 38; x++) {
    const bb = bangs[x - 9];
    for (let y = 4; y <= bb; y++) if (y >= 20 || inE(x, y, 24, 20, 15.5, 15.5)) put(m, x, y, 1);
  }
  if (base === 'male') {
    for (const [ax, ay, hw] of SPIKES) for (let y = ay; y <= 10; y++) {
      const w = (y - ay) / (10 - ay) * hw;
      for (let x = Math.floor(ax - w); x <= Math.ceil(ax + w); x++) if (Math.abs(x - ax) <= w + .01) put(m, x, y, 1);
    }
  }
  const locks = SIDE_LOCKS[len];
  const short = len === 'short' && base === 'female' ? { 9: 32, 10: 33, 11: 33 } : {};
  for (const map of [locks, mirror(locks), short, mirror(short)])
    for (const [x, b] of Object.entries(map)) for (let y = 18; y <= b; y++) put(m, +x, y, 1);
  // 색칠
  const l = newL();
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (!at(m, x, y)) continue;
    let c = P.base;
    if (!at(m, x, y + 1) || !at(m, x, y + 2)) c = P.sh; // 끝부분 그림자
    else if (y > 12 && (x + Math.floor(y / 3)) % 6 === 0) c = P.sh; // 결
    if (x >= 34 && y > 9) c = c === P.base ? P.sh : P.deep; // 오른쪽 그늘
    const hiY = base === 'male' ? [10, 11] : [9, 10];
    if (hiY.includes(y) && ((x >= 14 && x <= 19) || (x >= 27 && x <= 31))) c = P.hi;
    if (y === hiY[1] + 1 && (x === 16 || x === 29)) c = P.hi;
    l[y * W + x] = c;
  }
  if (base === 'female') { put(l, 22, 7, P.deep); put(l, 21, 8, P.deep); put(l, 21, 9, P.deep); }
  return outlined(l, P.out);
}

export function composeCharacter(a, dept) {
  const P = HAIR[a.hair_color];
  const layers = [backHair(a.hair_length, P), body(a.base, dept), head(a.base, P), frontHair(a.base, a.hair_length, P)];
  const out = newL();
  for (const l of layers) for (let i = 0; i < l.length; i++) if (l[i]) out[i] = l[i];
  return out;
}

// ───────────────────────── 소품 스프라이트 ─────────────────────────
const SPRITES = {
  drink: { rows: ['..OOO..', '..OCO..', '..OOO..', '..OGO..', '..OGO..', '.OGGGO.', 'OhGGGgO', 'OhLLLgO', 'OhLLLgO', 'OhGGGgO', 'OhGGGgO', 'OGGGGgO', '.OOOOO.'],
    pal: { O: '#1d3a25', G: '#4cae6b', g: '#2e7c48', h: '#aeeabe', C: '#e4e4ea', L: '#f6f4e6' } },
  study: { rows: ['OOOOOOOOOO', 'OBBBBBBBBO', 'OBYYYBBBBO', 'OBBBBBBBsO', 'OPPPPPPPPO', 'OPpPpPpPPO', 'OOOOOOOOOO'],
    pal: { O: '#1e2236', B: '#3c6ad2', s: '#2a4c9c', Y: '#f2d064', P: '#faf6ea', p: '#dbd2bf' } },
  exercise: { rows: ['.OOO.....OOO.', 'OWWWO...OWWWO', 'OWDWOOOOOWDWO', 'OWDWHHHHHWDWO', 'OWDWOOOOOWDWO', 'OWWWO...OWWWO', '.OOO.....OOO.'],
    pal: { O: '#17171d', W: '#5c5c6a', D: '#393944', H: '#cfcfd8' } },
  love: { rows: ['.OOO.OOO.', 'OhRRORRRO', 'OhRRRRRRO', 'ORRRRRRdO', '.ORRRRdO.', '..ORRdO..', '...OdO...', '....O....'],
    pal: { O: '#5a1428', R: '#f05a7c', h: '#ffc2d2', d: '#c22f52' } },
};
const BOOK_COLORS = [['#3c6ad2', '#2a4c9c'], ['#d2483c', '#9c2f26'], ['#3caa6a', '#277a4a']];

function drawSprite(ctx, key, x, y, p, override) {
  const s = SPRITES[key], pal = { ...s.pal, ...override };
  s.rows.forEach((row, ry) => [...row].forEach((ch, rx) => {
    if (ch === '.') return;
    ctx.fillStyle = pal[ch]; ctx.fillRect(Math.round(x + rx * p), Math.round(y + ry * p), p, p);
  }));
}

/**
 * 캔버스(560×450)에 캐릭터 무대를 그립니다.
 * getState()는 { profile: {nickname, grade, major}, appearance: {base, hair_length, hair_color}, levels: {drink, study, exercise, love} }를 반환해야 합니다.
 */
export function createStage(canvas, getState) {
  const S = 5, ctx = canvas.getContext('2d');
  const pops = {};
  let state = getState();
  let charPixels = composeCharacter(state.appearance, state.profile.major);

// ───────────────────────── 무대 렌더링 ─────────────────────────
const GROUND = 340, CX = 280, TOP = 60; // TOP: 머리 위 칭호 자리

function drawBackground() {
  const floor = GROUND + TOP;
  const g = ctx.createLinearGradient(0, 0, 0, floor);
  g.addColorStop(0, '#ffe9cc'); g.addColorStop(1, '#fcd9b6');
  ctx.fillStyle = g; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#e8c79c'; ctx.fillRect(0, floor, canvas.width, canvas.height - floor);
  ctx.fillStyle = '#d9b382';
  for (let x = 0; x < canvas.width; x += 20) ctx.fillRect(x + ((x / 20) % 2) * 10, floor + 15, 10, 5);
  ctx.fillStyle = '#cfa877'; ctx.fillRect(0, floor, canvas.width, 5);
}

function drawTitles(t) {
  const earned = CATS.map((c, i) => ({ ...c, i, level: state.levels[c.key] }))
    .filter((c) => tierOf(c.level) > 0)
    .sort((a, b) => b.level - a.level || a.i - b.i);
  if (!earned.length) return;
  ctx.font = 'bold 14px -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';
  const pills = earned.map((c, idx) => {
    const text = (idx === 0 ? '★ ' : '') + titleOf(c.name, c.level);
    return { ...c, text, w: ctx.measureText(text).width + 22 };
  });
  const gap = 8, total = pills.reduce((s, p) => s + p.w, 0) + gap * (pills.length - 1);
  let x = CX - total / 2;
  for (const [idx, p] of pills.entries()) {
    const since = pops[p.key] != null ? t - pops[p.key] : Infinity;
    const lift = since < 500 ? Math.round(6 * Math.sin((since / 500) * Math.PI)) : 0;
    const y = 18 - lift, h = 28;
    ctx.fillStyle = idx === 0 ? '#f2c94c' : 'rgba(255,255,255,.9)'; // 테두리 (대표 칭호는 금색)
    ctx.fillRect(x - 3, y - 3, p.w + 6, h + 6);
    ctx.fillStyle = TITLE_COLORS[p.key];
    ctx.fillRect(x, y, p.w, h);
    ctx.fillStyle = 'rgba(255,255,255,.18)'; ctx.fillRect(x, y, p.w, 4); // 픽셀 하이라이트
    ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(p.text, x + p.w / 2, y + h / 2 + 1);
    ctx.textBaseline = 'alphabetic';
    x += p.w + gap;
  }
}

function drawCharacter(oy) {
  const ox = CX / S - 24;
  ctx.fillStyle = 'rgba(90,50,20,.18)'; // 그림자
  ctx.fillRect(CX - 70, GROUND - 2, 140, 6);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const c = charPixels[y * W + x];
    if (c) { ctx.fillStyle = c; ctx.fillRect((ox + x) * S, (oy + y) * S, S, S); }
  }
}

function drawNameplate() {
  const name = state.profile.nickname || '닉네임';
  const sub = `${state.profile.grade}학년 · ${DEPTS[state.profile.major]?.name || '학과'}`;
  ctx.font = 'bold 15px -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';
  const w = Math.max(ctx.measureText(name).width, (ctx.font = '12px sans-serif', ctx.measureText(sub).width)) + 24;
  ctx.fillStyle = 'rgba(40,28,22,.82)';
  ctx.fillRect(CX - w / 2, GROUND + 8, w, 38);
  ctx.textAlign = 'center'; ctx.fillStyle = '#fff';
  ctx.font = 'bold 15px -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';
  ctx.fillText(name, CX, GROUND + 25);
  ctx.font = '12px -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';
  ctx.fillStyle = '#f3dcc4'; ctx.fillText(sub, CX, GROUND + 40);
}

function drawItems(t) {
  for (const { key } of CATS) {
    const tier = tierOf(state.levels[key]);
    const n = countOf(tier);
    if (!n) continue;
    let p = Math.round(S * scaleOf(tier));
    const since = pops[key] != null ? t - pops[key] : Infinity;
    if (since < 700) p += since < 350 ? 3 : 1;
    for (let i = 0; i < n; i++) {
      if (key === 'drink') drawSprite(ctx, 'drink', CX - 22 * S - (i + 1) * 8 * p, GROUND - 13 * p, p);
      if (key === 'study') {
        const [b, s] = BOOK_COLORS[i % 3];
        drawSprite(ctx, 'study', CX + 15 * S + (i % 2) * p, GROUND - (i + 1) * 7 * p, p, { B: b, s });
      }
      if (key === 'exercise') drawSprite(ctx, 'exercise', CX - 18 * S - 13 * p - (i % 2) * p * 2, 40 + i * 9 * p, p);
      if (key === 'love') {
        const off = [[0, 0], [11, -6], [4, 10]][i];
        const bob = Math.round(Math.sin(t / 500 + i * 1.7) * 2) * 2;
        drawSprite(ctx, 'love', CX + 18 * S + off[0] * p, 60 + off[1] * p + bob, p);
      }
    }
    if (since < 700) { // 반짝임
      ctx.fillStyle = '#fff6a8';
      const sx = { drink: CX - 150, study: CX + 110, exercise: CX - 170, love: CX + 140 }[key];
      const sy = { drink: GROUND - 90, study: GROUND - 70, exercise: 70, love: 70 }[key];
      const r = 10 + since / 30;
      for (const [dx, dy] of [[0, -r], [r, 0], [0, r], [-r, 0]]) ctx.fillRect(sx + dx, sy + dy, 5, 5);
    }
  }
}

function frame(t) {
  drawBackground();
  const oy = 8 - (Math.floor(t / 520) % 2); // 숨쉬기 2프레임
  ctx.save(); ctx.translate(0, TOP);
  drawItems(t);
  drawCharacter(oy);
  drawNameplate();
  ctx.restore();
  drawTitles(t);
  requestAnimationFrame(loop);
}

  function loop(t) { state = getState(); frame(t); }
  // frame() 안의 requestAnimationFrame(frame)을 loop로 돌립니다.
  return {
    start() { requestAnimationFrame(loop); },
    redraw() { state = getState(); charPixels = composeCharacter(state.appearance, state.profile.major); },
    pop(key) { pops[key] = performance.now(); },
  };
}
