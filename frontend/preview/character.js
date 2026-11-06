// 캐릭터 미리보기 화면 (디자인 확인용 · 서버 없이 동작)
import { HAIR, CATS, DEPTS, tierOf, countOf, scaleOf, createStage } from '/assets/character/pixel-character.js';

// 실제 앱에서는 AI가 분류합니다. 여기서는 키워드로 흉내만 냅니다.
const KEYWORDS = {
  drink: ['술', '맥주', '소주', '막걸리', '회식', '뒤풀이', '술자리', '칵테일', '와인', '하이볼', '취했', '건배', '포차'],
  study: ['공부', '도서관', '시험', '과제', '강의', '수업', '레포트', '중간고사', '기말', '스터디', '복습', '예습', '발표'],
  exercise: ['운동', '헬스', '러닝', '달리기', '축구', '농구', '수영', '요가', '필라테스', '등산', '자전거', '배드민턴', '풋살', '스쿼트'],
  love: ['데이트', '연애', '소개팅', '고백', '썸', '여자친구', '남자친구', '여친', '남친', '애인', '기념일', '커플'],
};
const SAMPLES = [
  '도서관에서 중간고사 공부를 했다.', '동기들이랑 학교 앞에서 술자리!', '헬스장에서 하체 운동 완료',
  '소개팅 상대랑 두 번째 데이트했다', '팀플 과제 발표 준비', '동아리 풋살 경기 뛰었다', '오늘은 그냥 집에서 쉬었다',
];


function classify(text) {
  let best = 'none', bestN = 0;
  for (const [k, words] of Object.entries(KEYWORDS)) {
    const n = words.reduce((s, w) => s + (text.includes(w) ? 1 : 0), 0);
    if (n > bestN) { best = k; bestN = n; }
  }
  return best;
}

const state = {
  profile: { nickname: '', grade: 1, major: '' },
  appearance: { base: 'female', hair_length: 'long', hair_color: 'black' },
  levels: { drink: 0, study: 0, exercise: 0, love: 0 },
};

const stage = createStage(document.getElementById('stage'), () => state);

// ───────────────────────── UI ─────────────────────────
const $ = (s) => document.querySelector(s);
function goto(step) {
  document.querySelectorAll('.tabs button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.step == step)));
  document.querySelectorAll('section.step').forEach((s) => s.classList.toggle('active', s.dataset.step == step));
}
document.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => goto(b.dataset.step)));
document.querySelectorAll('[data-goto]').forEach((b) => b.addEventListener('click', () => goto(b.dataset.goto)));

function syncProfile() {
  state.profile.nickname = $('#nickname').value.trim();
  state.profile.grade = +$('#grade').value;
  renderInfo();
}
['#nickname', '#grade'].forEach((id) => $(id).addEventListener('input', syncProfile));
const majorBtns = document.querySelectorAll('#major-seg button');
function paintMajor() { majorBtns.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === state.profile.major))); }
majorBtns.forEach((b) => b.addEventListener('click', () => { state.profile.major = b.dataset.v; paintMajor(); redrawCharacter(); $('#profile-err').textContent = ''; }));
paintMajor();
$('#profile-form').addEventListener('submit', (e) => {
  e.preventDefault(); syncProfile();
  const { nickname, major } = state.profile;
  const err = nickname.length < 2 ? '닉네임은 2~12자로 입력해 주세요.' : !major ? '학과를 선택해 주세요.' : '';
  $('#profile-err').textContent = err;
  if (!err) goto(2);
});

function bindSeg(sel, field) {
  const btns = document.querySelectorAll(`${sel} button`);
  const paint = () => btns.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === state.appearance[field])));
  btns.forEach((b) => b.addEventListener('click', () => { state.appearance[field] = b.dataset.v; paint(); redrawCharacter(); }));
  paint();
}
bindSeg('#base-seg', 'base');
bindSeg('#length-seg', 'hair_length');

const sw = $('#swatches');
for (const [k, P] of Object.entries(HAIR)) {
  const b = document.createElement('button');
  b.type = 'button'; b.style.background = `linear-gradient(135deg, ${P.hi}, ${P.base} 55%, ${P.sh})`;
  b.setAttribute('aria-label', P.name); b.title = P.name; b.dataset.v = k;
  b.addEventListener('click', () => { state.appearance.hair_color = k; paintSwatches(); redrawCharacter(); });
  sw.append(b);
}
function paintSwatches() {
  sw.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === state.appearance.hair_color)));
  $('#swatch-name').textContent = `선택: ${HAIR[state.appearance.hair_color].name}`;
}
paintSwatches();

function redrawCharacter() { stage.redraw(); renderInfo(); }

function renderInfo() {
  const a = state.appearance;
  const lenName = { short: '짧은', medium: '중간', long: '긴' }[a.hair_length];
  const parts = [
    `<span class="pill"><b>${a.base === 'male' ? '기본 남성' : '기본 여성'}</b></span>`,
    `<span class="pill">${DEPTS[state.profile.major]?.name ?? '학과 선택 전'}</span>`,
    `<span class="pill">${lenName} 머리 · ${HAIR[a.hair_color].name}</span>`,
    ...CATS.map((c) => `<span class="pill">${c.name} <b>Lv.${state.levels[c.key]}</b></span>`),
  ];
  $('#stage-info').innerHTML = parts.join('');
}

function itemText(c) {
  const tier = tierOf(state.levels[c.key]);
  if (!tier) return `<span style="color:var(--muted)">Lv.5에 ${c.item} 등장</span>`;
  return `${c.item} ${countOf(tier)}${c.unit} · ${scaleOf(tier).toFixed(2).replace(/0$/, '')}배`;
}
function renderLevels() {
  $('#levels').innerHTML = CATS.map((c) => {
    const lv = state.levels[c.key];
    return `<tr>
      <td>${c.name}</td>
      <td class="lv">Lv.${lv}<div class="bar"><i style="width:${(lv % 5) * 20}%"></i></div></td>
      <td>${itemText(c)}</td>
      <td><div class="row">
        <button class="btn ghost small" data-k="${c.key}" data-d="-1" aria-label="${c.name} 레벨 내리기">−1</button>
        <button class="btn ghost small" data-k="${c.key}" data-d="1" aria-label="${c.name} 레벨 올리기">+1</button>
        <button class="btn ghost small" data-k="${c.key}" data-d="5" aria-label="${c.name} 5레벨 올리기">+5</button>
      </div></td></tr>`;
  }).join('');
  $('#levels').querySelectorAll('button').forEach((b) => b.addEventListener('click', () => addLevel(b.dataset.k, +b.dataset.d)));
  renderInfo();
}

let toastTimer;
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
}

function addLevel(key, d) {
  const before = tierOf(state.levels[key]);
  state.levels[key] = Math.max(0, state.levels[key] + d);
  const after = tierOf(state.levels[key]);
  const c = CATS.find((x) => x.key === key);
  if (after > before) {
    stage.pop(key);
    toast(`${c.name} Lv.${state.levels[key]}! ${c.item}이(가) ${after === 1 ? '생겼어요' : '더 커졌어요'} ✨`);
  }
  renderLevels();
}

let sampleIdx = 0;
$('#sample').addEventListener('click', () => { $('#record').value = SAMPLES[sampleIdx++ % SAMPLES.length]; $('#record').focus(); });
$('#submit-record').addEventListener('click', () => {
  const text = $('#record').value.trim();
  if (!text) { $('#result').textContent = '기록할 내용을 입력해 주세요.'; return; }
  const cat = classify(text);
  const c = CATS.find((x) => x.key === cat);
  if (c) {
    addLevel(cat, 1);
    $('#result').innerHTML = `분류: <b>${c.name}</b> → ${c.name} 레벨 +1 (현재 Lv.${state.levels[cat]})`;
  } else {
    $('#result').innerHTML = '분류: <b>해당 없음</b> → 레벨 변화 없음';
  }
  const li = document.createElement('li');
  li.textContent = `${c ? c.name : '해당 없음'} · ${text}`;
  $('#log').prepend(li);
  $('#record').value = '';
});
$('#reset').addEventListener('click', () => { for (const k in state.levels) state.levels[k] = 0; renderLevels(); });

renderLevels();
stage.start();
