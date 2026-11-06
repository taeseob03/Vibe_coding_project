import { mountAccount } from '/static/accounts/index.js';
import { mountOnboarding } from '/static/accounts/onboarding.js';
import { api } from '/static/shared/api.js';

const guest = document.querySelector('#guest-demo');
guest.addEventListener('click', async () => {
  guest.disabled = true;
  try {
    const username = 'guest_' + crypto.randomUUID().slice(0,8);
    await api('/auth/login', { method:'POST',body:JSON.stringify({username}) });
    await api('/profile/me/complete',{method:'POST',body:JSON.stringify({nickname:'체험 캐릭터',color:'green'})});
    location.href='/?mode=demo';
  } catch(error) {document.querySelector('#account').textContent=error.message;guest.disabled=false;}
});
const runtime = await api('/api/runtime');
if (!runtime.demo_available) guest.hidden=true;
const user = await mountAccount();
if (user) {
  guest.hidden = true;
  document.querySelector('main').classList.add('connected');
  const profile = await mountOnboarding();
  if (profile) {
    const demo = runtime.demo_available && (new URLSearchParams(location.search).get('mode') === 'demo' || !runtime.gemini_available);
    document.querySelector('#game-section').hidden=false;
    document.querySelector('#runtime-status').textContent=demo?'샘플 체험 모드 · AI 분석 아님':'Gemini 연결 모드';
    const link=document.querySelector('#mode-switch');
    link.textContent=demo&&runtime.gemini_available?'실제 Gemini 모드':'샘플 체험';
    link.href=demo&&runtime.gemini_available?'/?mode=gemini':'/?mode=demo';
    link.hidden=!runtime.demo_available;
    const frame=document.querySelector('#game-frame');
    frame.src='/static/game/index.html'+(demo?'?mode=demo':'');frame.hidden=false;
  }
}
