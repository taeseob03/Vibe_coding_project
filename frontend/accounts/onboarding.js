import { api } from '/shared/api.js?v=local-web-1';
import { HAIR, createStage } from '/assets/character/pixel-character.js';

export async function mountOnboarding() {
  const section = document.querySelector('#setup-section');
  const status = document.querySelector('#setup-status');
  const form = document.querySelector('#setup-form');
  const nickname = document.querySelector('#nickname');
  const nameStep = document.querySelector('#nickname-step');
  const colorStep = document.querySelector('#color-step');
  const retry = document.querySelector('#setup-retry');
  let queue = Promise.resolve();
  let busy = false;
  let editing = false;
  const grade = document.querySelector('#setup-grade');
  const swatches = document.querySelector('#setup-hair-colors');
  for (const [key, palette] of Object.entries(HAIR)) {
    const label = document.createElement('label');
    const radio = document.createElement('input');
    radio.type = 'radio'; radio.name = 'hair_color'; radio.value = key;
    radio.checked = key === 'black';
    const dot = document.createElement('span'); dot.className = 'hair-swatch';
    dot.style.background = palette.base; dot.setAttribute('aria-hidden', 'true');
    label.append(radio, dot, document.createTextNode(palette.name)); swatches.append(label);
  }
  const selected = name => form.querySelector(`input[name="${name}"]:checked`)?.value;
  function customization() {
    return {
      grade: Number(grade.value), major: selected('major') || null,
      appearance: { base: selected('base'), hair_length: selected('hair_length'), hair_color: selected('hair_color') },
    };
  }
  const stage = typeof window.CanvasRenderingContext2D === 'function'
    ? createStage(document.querySelector('#setup-canvas'), () => ({
      profile: { nickname: nickname.value.trim(), grade: Number(grade.value), major: selected('major') },
      appearance: customization().appearance, levels: { drink: 0, study: 0, exercise: 0, love: 0 },
    })) : null;
  window.addEventListener('pagehide', () => stage?.stop());
  window.addEventListener('pageshow', () => { if (!form.hidden) stage?.start(); });

  function setBusy(value) {
    busy = value;
    for (const control of form.querySelectorAll('input, select, button')) control.disabled = value;
  }
  function selectedColor() {
    return selected('color') ?? 'green';
  }
  function showStep(step) {
    nameStep.hidden = step !== 'nickname';
    colorStep.hidden = step !== 'color';
    form.dataset.step = step;
  }
  function updatePreview() {
    stage?.redraw();
  }
  function saveDraft(step = form.dataset.step) {
    // 저장 요청을 순서대로 처리해 앞선 입력이 나중 입력을 덮어쓰지 않게 합니다.
    if (editing) return Promise.resolve();
    const body = { nickname: nickname.value, color: selectedColor(), step, ...customization() };
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
      editing = profile.onboarding_completed;
      if (editing && new URLSearchParams(location.search).get('customize') !== '1') return profile;
      section.hidden = false;
      nickname.value = profile.nickname ?? '';
      nickname.readOnly = editing;
      grade.value = String(profile.grade || 1);
      const values = { major: profile.major, ...(profile.appearance || {}) };
      for (const input of form.querySelectorAll('.setup-options input')) {
        if (values[input.name] != null) input.checked = input.value === values[input.name];
      }
      for (const input of form.querySelectorAll('input[name="color"]')) {
        input.checked = input.value === profile.color;
      }
      showStep(profile.major ? profile.step : 'nickname');
      form.hidden = false;
      updatePreview();
      stage?.start();
      document.querySelector('#setup-complete').textContent = editing ? '저장하고 돌아가기' : '완료하고 시작하기';
      status.textContent = '학과와 성별, 머리 모양을 선택해 나만의 캐릭터를 만들어 보세요.';
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
  nickname.addEventListener('change', () => {
    if (!busy) saveDraft('nickname').catch(error => { status.textContent = `저장 실패: ${error.message}`; });
    updatePreview();
  });
  nickname.addEventListener('input', updatePreview);
  for (const input of form.querySelectorAll('.setup-options input, #setup-grade')) {
    input.addEventListener('change', () => {
      updatePreview();
      if (!busy) saveDraft().catch(error => { status.textContent = `저장 실패: ${error.message}`; });
    });
  }
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
    if (!selected('major')) { status.textContent = '학과를 선택해 주세요.'; return; }
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
    if (!selected('major')) {
      status.textContent = '학과를 선택해 주세요.';
      return;
    }
    setBusy(true);
    const button = document.querySelector('#setup-complete');
    button.disabled = true;
    try {
      await queue.catch(() => {});
      status.textContent = '캐릭터를 저장하는 중…';
      await api(editing ? '/profile/me/appearance' : '/profile/me/complete', {
        method: editing ? 'PUT' : 'POST', body: JSON.stringify(editing ? customization() : {
          nickname: nickname.value, color: selectedColor(), ...customization(),
        }),
      });
      window.location.replace('/');
    } catch (error) {
      status.textContent = `완료 실패: ${error.message} 입력은 유지됩니다. 다시 시도해 주세요.`;
      button.disabled = false;
      setBusy(false);
    }
  });
  return load();
}
