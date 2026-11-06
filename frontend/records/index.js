import { api } from '/static/shared/api.js';

export function mountRecords() {
  const form = document.querySelector('#record-form');
  const message = document.querySelector('#message');
  const list = document.querySelector('#record-list');
  const button = form.querySelector('button[type="submit"]');
  const file = document.querySelector('#record-image');
  const preview = document.querySelector('#record-preview');
  let requestId = crypto.randomUUID();
  let previewUrl;
  let timer;
  let refreshing = false;
  let refreshAgain = false;
  let closed = false;
  let lastState = '';
  const names = { pending: '대기', processing: '분석 중', completed: '분석 완료', failed: '분석 실패' };
  form.addEventListener('input', () => { requestId = crypto.randomUUID(); });

  function clearPreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = undefined;
    preview.removeAttribute('src');
    preview.hidden = true;
  }
  file.addEventListener('change', () => {
    clearPreview();
    if (!file.files[0]) return;
    if (file.files[0].size > 10 * 1024 * 1024) {
      message.textContent = '사진은 10MB 이하로 선택해 주세요.';
      file.value = '';
      return;
    }
    previewUrl = URL.createObjectURL(file.files[0]);
    preview.src = previewUrl;
    preview.hidden = false;
  });

  async function refresh() {
    clearTimeout(timer);
    if (closed || document.hidden) return;
    if (refreshing) { refreshAgain = true; return; }
    refreshing = true;
    try {
      const records = await api('/api/records');
      list.replaceChildren();
      let pending = false;
      for (const record of records) {
        pending ||= ['pending', 'processing'].includes(record.status);
        const item = document.createElement('li');
        const title = document.createElement('p');
        title.textContent = `${record.text || '사진 기록'} · ${names[record.status]}`;
        item.append(title);
        if (record.has_image) {
          const image = document.createElement('img');
          image.src = `/api/records/${record.id}/image`;
          image.alt = '내 기록 사진';
          image.loading = 'lazy';
          image.className = 'record-thumbnail';
          item.append(image);
        }
        if (record.analysis) {
          const result = document.createElement('p');
          result.textContent = `${record.analysis.keywords.map(k => '#' + k).join(' ')} · ${record.analysis.summary}`;
          item.append(result);
          const state = document.createElement('p');
          state.textContent = record.stat_status === 'applied' ? `${record.analysis.category} 활동이 반영됐어요.`
            : record.stat_status === 'skipped' ? '분류 근거가 부족하거나 판단이 애매해 스탯 반영을 보류했어요.'
            : record.stat_status === 'failed' ? '분석은 완료됐지만 캐릭터 상태를 저장하지 못했어요.'
            : '캐릭터 상태를 저장하고 있어요.';
          item.append(state);
          pending ||= record.stat_status === 'pending';
        }
        const error = record.analysis_error ?? record.state_error;
        if (error) {
          const notice = document.createElement('p');
          notice.textContent = error.message;
          item.append(notice);
        }
        if (record.status === 'failed' || (record.status === 'completed' && record.stat_status === 'failed')) {
          const retry = document.createElement('button');
          retry.type = 'button';
          retry.textContent = record.status === 'failed' ? '분석 다시 시도' : '캐릭터 상태 저장 다시 시도';
          retry.addEventListener('click', async () => {
            retry.disabled = true;
            try {
              await api(`/api/records/${record.id}/retry`, { method: 'POST' });
              await refresh();
            } catch (error) {
              message.textContent = error.message;
              retry.disabled = false;
            }
          });
          item.append(retry);
        }
        list.append(item);
      }
      if (!records.length) list.textContent = '아직 기록이 없습니다.';
      const state = records.map(record => `${record.id}:${record.stat_status}`).join('|');
      if (state !== lastState) {
        lastState = state;
        window.dispatchEvent(new Event('character:updated'));
      }
      if (pending) timer = setTimeout(refresh, 1500);
    } catch (error) {
      message.textContent = error.message;
    } finally {
      refreshing = false;
      if (refreshAgain) {
        refreshAgain = false;
        clearTimeout(timer);
        timer = setTimeout(refresh, 0);
      }
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = form.querySelector('textarea').value.trim();
    if (!text && !file.files[0]) {
      message.textContent = '글 또는 사진을 입력해 주세요.';
      return;
    }
    button.disabled = true;
    message.textContent = '기록 저장 중…';
    const body = new FormData();
    body.append('request_id', requestId);
    body.append('text', text);
    if (file.files[0]) body.append('image', file.files[0]);
    try {
      await api('/api/records', { method: 'POST', body });
      form.reset();
      clearPreview();
      requestId = crypto.randomUUID();
      message.textContent = '기록을 저장했어요. 분석 상태를 확인하고 있어요.';
      await refresh();
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
  document.querySelector('#refresh').addEventListener('click', refresh);
  document.addEventListener('visibilitychange', () => {
    clearTimeout(timer);
    if (!document.hidden) refresh();
  });
  window.addEventListener('pagehide', () => {
    closed = true;
    clearTimeout(timer);
    clearPreview();
  });
  window.addEventListener('pageshow', () => {
    if (closed) { closed = false; refresh(); }
  });
  refresh();
}
