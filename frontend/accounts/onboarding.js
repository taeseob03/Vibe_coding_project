import { api } from '/static/shared/api.js';
import { renderCharacter } from '/static/characters/index.js';

export async function mountOnboarding() {
  const section = document.querySelector('#setup-section');
  const status = document.querySelector('#setup-status');
  const form = document.querySelector('#setup-form');
  const nickname = document.querySelector('#nickname');
  const nameStep = document.querySelector('#nickname-step');
  const colorStep = document.querySelector('#color-step');
  const preview = document.querySelector('#setup-preview');
  const retry = document.querySelector('#setup-retry');
  let queue = Promise.resolve();
  let busy = false;

  function setBusy(value) {
    busy = value;
    for (const control of form.querySelectorAll('input, select, button')) control.disabled = value;
  }
  function selectedColor() {
    return form.querySelector('input[name="color"]:checked')?.value ?? null;
  }
  function showStep(step) {
    nameStep.hidden = step !== 'nickname';
    colorStep.hidden = step !== 'color';
    form.dataset.step = step;
  }
  function profileFields() {
    return { grade:Number(document.querySelector('#grade').value), major:document.querySelector('#major').value,
      appearance:{base:document.querySelector('#base').value,hair_length:document.querySelector('#hair-length').value,hair_color:document.querySelector('#hair-color').value} };
  }
  function updatePreview() {
    const fields=profileFields();
    renderCharacter(preview, selectedColor() ?? 'green', nickname.value.trim(), fields.appearance, fields.major);
  }
  function saveDraft(step = form.dataset.step) {
    // 저장 요청을 순서대로 처리해 앞선 입력이 나중 입력을 덮어쓰지 않게 합니다.
    const body = { nickname: nickname.value, color: selectedColor(), step, ...profileFields() };
    queue = queue.catch(() => {}).then(async () => {
      status.textContent = '임시 저장 중…';
      await api('/profile/me/draft', { method: 'PUT', body: JSON.stringify(body) });
      status.textContent = '임시 저장됨 · 다시 접속하면 여기서 이어갈 수 있어요.';
    });
    return queue;
  }
  async function load() {
    retry.hidden = true;
    status.textContent = '저장된 설정을 불러오는 중…';
    try {
      const profile = await api('/profile/me');
      if (profile.onboarding_completed) return profile;
      section.hidden = false;
      nickname.value = profile.nickname ?? '';
      document.querySelector('#grade').value=profile.grade||1;document.querySelector('#major').value=profile.major||'computer';
      document.querySelector('#base').value=profile.appearance?.base||'female';document.querySelector('#hair-length').value=profile.appearance?.hair_length||'long';document.querySelector('#hair-color').value=profile.appearance?.hair_color||'black';
      for (const input of form.querySelectorAll('input[name="color"]')) {
        input.checked = input.value === profile.color;
      }
      showStep(profile.step);
      form.hidden = false;
      updatePreview();
      status.textContent = '닉네임과 색상을 선택해 나만의 캐릭터를 만들어 보세요.';
      return null;
    } catch (error) {
      section.hidden = false;
      form.hidden = true;
      status.textContent = error.message;
      retry.hidden = false;
      return null;
    }
  }
  retry.addEventListener('click', async () => {
    const profile = await load();
    if (profile) window.location.reload();
  });
  for(const select of form.querySelectorAll('select')) select.addEventListener('change',()=>{updatePreview();if(!busy)saveDraft().catch(error=>{status.textContent=error.message;});});
  nickname.addEventListener('change', () => {
    if (!busy) saveDraft('nickname').catch(error => { status.textContent = `저장 실패: ${error.message}`; });
    updatePreview();
  });
  for (const input of form.querySelectorAll('input[name="color"]')) {
    input.addEventListener('change', () => {
      updatePreview();
      if (!busy) saveDraft('color').catch(error => { status.textContent = `저장 실패: ${error.message}`; });
    });
  }
  document.querySelector('#setup-next').addEventListener('click', async () => {
    if (busy) return;
    nickname.value = nickname.value.trim();
    if (nickname.value.length < 2 || nickname.value.length > 12) {
      status.textContent = '닉네임은 앞뒤 공백을 제외하고 2~12자로 입력해 주세요.';
      nickname.focus();
      return;
    }
    setBusy(true);
    try {
      await saveDraft('color');
      showStep('color');
    } catch (error) {
      status.textContent = `저장 실패: ${error.message} 다시 눌러 주세요.`;
    } finally { setBusy(false); }
  });
  document.querySelector('#setup-back').addEventListener('click', async () => {
    if (busy) return;
    setBusy(true);
    try {
      await saveDraft('nickname');
      showStep('nickname');
    } catch (error) { status.textContent = error.message; }
    finally { setBusy(false); }
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy) return;
    if (form.dataset.step !== 'color') {
      document.querySelector('#setup-next').click();
      return;
    }
    if (!selectedColor()) {
      status.textContent = '캐릭터 색상을 하나 선택해 주세요.';
      return;
    }
    setBusy(true);
    const button = document.querySelector('#setup-complete');
    button.disabled = true;
    try {
      await queue.catch(() => {});
      status.textContent = '캐릭터를 저장하는 중…';
      await api('/profile/me/complete', {
        method: 'POST', body: JSON.stringify({ nickname: nickname.value, color: selectedColor(), ...profileFields() }),
      });
      window.location.reload();
    } catch (error) {
      status.textContent = `완료 실패: ${error.message} 입력은 유지됩니다. 다시 시도해 주세요.`;
      button.disabled = false;
      setBusy(false);
    }
  });
  return load();
}
