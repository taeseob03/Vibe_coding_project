import { config } from './app-config.mjs';

export async function request(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.error?.message || data?.detail || '요청에 실패했어요.');
  return data;
}
const json = value => ({ headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) });

export const api = {
  me() { return request('/api/me'); },
  progress() { return request('/api/progress'); },
  async post(body) {
    body.set('request_id', body.get('record_id'));
    body.delete('record_id');
    if (config.demoAnalysis) body.set('category', document.querySelector('#sample-category').value);
    const response = await fetch(config.demoAnalysis ? '/api/records/demo' : '/api/records', {
      method: 'POST', credentials: 'same-origin', body,
    });
    let record = await response.json();
    if (!response.ok) throw new Error(record.error?.message || '기록을 저장하지 못했어요.');
    let firstApplication = response.status === 201;
    if (record.status === 'failed' || (record.status === 'completed' && record.stat_status === 'failed')) {
      record = await request(`/api/records/${record.id}/retry`, { method: 'POST' });
      firstApplication = true;
    }
    const deadline = Date.now() + 90000;
    while (record.status === 'pending' || record.status === 'processing' ||
          (record.status === 'completed' && record.stat_status === 'pending')) {
      if (Date.now() > deadline) throw new Error('아직 처리 중이에요. 기록 목록에서 상태를 확인할 수 있어요.');
      if (document.hidden) await new Promise(resolve => setTimeout(resolve, 1500));
      else await new Promise(resolve => setTimeout(resolve, 700));
      record = await request(`/api/records/${record.id}`);
    }
    if (record.status === 'failed' || record.stat_status === 'failed') {
      throw new Error(record.analysis_error?.message || record.state_error?.message || '처리에 실패했어요.');
    }
    const data = await request('/api/progress');
    window.dispatchEvent(new Event('campus:state-updated'));
    return { ...record.analysis, record_id: record.id, progress: data.progress, state: data.state,
      character_effect: data.progress.find(item => item.category === record.analysis.category) ?? null,
      awarded: record.stat_status === 'applied' && firstApplication,
      stack_changes: firstApplication ? record.stack_changes ?? {} : {}, source: record.source };
  },
  rooms() { return request('/api/lounges'); },
  members(id) { return request(`/api/lounges/${encodeURIComponent(id)}/members`); },
  search(query) { return request(`/api/users?nickname=${encodeURIComponent(query)}`); },
  invitations() { return request('/api/lounge-invitations'); },
  invite(id, recipient) { return request(`/api/lounges/${id}/invitations`, { method: 'POST', ...json({ recipient_id: recipient }) }); },
  respond(id, accept) { return request(`/api/lounge-invitations/${id}/response`, { method: 'POST', ...json({ accept }) }); },
  demoUsers: [],
  async demoInbox() { throw new Error('실제 계정의 받은 초대를 이용해 주세요.'); },
  async demoRespond() { throw new Error('실제 계정으로 접속해 수락해 주세요.'); },
};
