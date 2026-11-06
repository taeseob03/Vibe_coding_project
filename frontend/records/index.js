import { api } from '/shared/api.js';

export function mountRecords() {
  const form = document.querySelector('#record-form');
  const message = document.querySelector('#message');
  const list = document.querySelector('#record-list');
  const button = form.querySelector('button');
  let refreshing = false;

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      const records = await api('/records');
      list.replaceChildren();
      for (const record of records) {
        const item = document.createElement('li');
        item.textContent = `${record.text} · ${record.status} · ${record.analysis?.summary ?? '분석 대기'} · 효과: ${record.effect_status}`;
        list.append(item);
      }
      if (!records.length) list.textContent = '아직 기록이 없습니다.';
    } catch (error) {
      message.textContent = error.message;
    } finally {
      refreshing = false;
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    message.textContent = '저장 중…';
    try {
      await api('/records', {
        method: 'POST', body: JSON.stringify({ text: form.querySelector('textarea').value }),
      });
      form.reset();
      message.textContent = '저장되었습니다. 임시 분석 결과이며 효과는 지급되지 않습니다.';
      await refresh();
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
  document.querySelector('#refresh').addEventListener('click', refresh);
  refresh();
}
