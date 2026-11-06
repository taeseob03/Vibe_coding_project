import { config } from './app-config.mjs';
import { DEMO_ME, DEMO_USERS, initialSocialState, searchUsers, sendInvitation, respondToInvitation } from './social-model.mjs';

const DEMO_PROFILE = config.demoMe || DEMO_USERS[0];
const CURRENT_ID = DEMO_PROFILE.id;
const PEOPLE = DEMO_USERS.map(user => user.id === DEMO_ME ? { ...user, ...DEMO_PROFILE } : user);
const STORE = 'campus-social-demo-v1' + (config.demoMe ? ':' + CURRENT_ID : '');

function initialDemo() {
  const state = initialSocialState();
  for (const room of state.rooms) {
    if (room.owner_id === DEMO_ME) { room.owner_id = CURRENT_ID; room.name = DEMO_PROFILE.nickname + '의 라운지'; }
    room.member_ids = room.member_ids.map(id => id === DEMO_ME ? CURRENT_ID : id);
  }
  for (const invitation of state.invitations) {
    if (invitation.recipient_id === DEMO_ME) invitation.recipient_id = CURRENT_ID;
    if (invitation.sender_id === DEMO_ME) invitation.sender_id = CURRENT_ID;
  }
  return state;
}

export async function request(path, options = {}) {
  let response;
  try { response = await fetch(path, { credentials: 'same-origin', ...options }); }
  catch (error) { throw new Error(error.name === 'TimeoutError' ? '응답 시간이 초과되었어요. 다시 시도해 주세요.' : '서버에 연결하지 못했어요. 다시 시도해 주세요.'); }
  if (response.status === 204) return null;
  let data;
  try { data = await response.json(); }
  catch { throw new Error('서버 응답을 읽지 못했어요. 다시 시도해 주세요.'); }
  if (!response.ok) throw new Error(data.error?.message || (typeof data.detail === 'string' ? data.detail : '요청을 처리하지 못했어요.'));
  return data;
}

function loadDemo() {
  const raw = localStorage.getItem(STORE);
  if (!raw) return initialDemo();
  let data;
  try { data = JSON.parse(raw); } catch { throw new Error('초대 테스트 데이터를 읽지 못했어요. 브라우저 저장 공간을 확인해 주세요.'); }
  if (data.version !== 1 || !Array.isArray(data.rooms) || !Array.isArray(data.invitations)) throw new Error('지원하지 않는 초대 테스트 데이터입니다.');
  return data;
}

async function changeDemo(action) {
  const run = () => { const next = action(loadDemo()); localStorage.setItem(STORE, JSON.stringify(next)); return next; };
  // Serializes demo updates between tabs on the same origin.
  return navigator.locks ? navigator.locks.request(STORE, run) : run();
}

export const api = {
  async me() { return config.profileMode === 'server' || config.socialMode === 'server' ? request(config.profileUrl) : structuredClone(DEMO_PROFILE); },
  logout() { return request('/auth/logout', { method: 'POST' }); },
  progress() { return request(config.progressUrl); },
  post(body) { return request(config.postUrl, { method: 'POST', body, signal: AbortSignal.timeout(90000) }); },
  async rooms() {
    if (config.socialMode === 'server') return request(`${config.socialBase}/lounges`);
    return loadDemo().rooms.filter(room => room.member_ids.includes(CURRENT_ID));
  },
  async members(roomId) {
    if (config.socialMode === 'server') return request(`${config.socialBase}/lounges/${encodeURIComponent(roomId)}/members`);
    const room = loadDemo().rooms.find(item => item.id === roomId && item.member_ids.includes(CURRENT_ID));
    if (!room) throw new Error('참여 중인 라운지를 찾을 수 없어요.');
    return PEOPLE.filter(user => room.member_ids.includes(user.id)).map(user => structuredClone(user));
  },
  async search(query) {
    return config.socialMode === 'demo' ? searchUsers(query) : request(`${config.socialBase}/users?nickname=${encodeURIComponent(query)}`);
  },
  async invitations() {
    if (config.socialMode === 'server') return request(`${config.socialBase}/lounge-invitations`);
    return loadDemo().invitations.filter(item => item.sender_id === CURRENT_ID || item.recipient_id === CURRENT_ID);
  },
  async invite(roomId, recipient) {
    if (config.socialMode === 'server') return request(`${config.socialBase}/lounges/${encodeURIComponent(roomId)}/invitations`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipient_id: recipient }) });
    await changeDemo(state => sendInvitation(state, { actor: CURRENT_ID, recipient, roomId, id: crypto.randomUUID() }));
  },
  async respond(invitationId, accept) {
    if (config.socialMode === 'server') return request(`${config.socialBase}/lounge-invitations/${encodeURIComponent(invitationId)}/response`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ accept }) });
    await changeDemo(state => respondToInvitation(state, { actor: CURRENT_ID, invitationId, accept }));
  },
  demoUsers: PEOPLE,
  async demoInbox(userId) {
    if (config.socialMode !== 'demo') throw new Error('예제 모드에서만 사용할 수 있어요.');
    return loadDemo().invitations.filter(item => item.recipient_id === userId && item.status === 'pending');
  },
  async demoRespond(userId, invitationId, accept) {
    if (config.socialMode !== 'demo') throw new Error('예제 모드에서만 사용할 수 있어요.');
    await changeDemo(state => respondToInvitation(state, { actor: userId, invitationId, accept }));
  },
};
