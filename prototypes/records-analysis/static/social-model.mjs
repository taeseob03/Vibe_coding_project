// Pure demo-domain rules. The production server must enforce the same rules per authenticated user.
export const DEMO_ME = 'user-1';
export const DEMO_USERS = [
  { id: DEMO_ME, nickname: '나', emoji: '🧑', counts: { '술': 0, '공부': 0, '연애': 0, '운동': 0 } },
  { id: 'user-2', nickname: '민지', emoji: '👩', major: 'embedded', appearance: { base: 'female', hair_length: 'long', hair_color: 'brown' }, counts: { '술': 2, '공부': 7, '연애': 5, '운동': 0 } },
  { id: 'user-3', nickname: '준호', emoji: '👨', major: 'computer', appearance: { base: 'male', hair_length: 'short', hair_color: 'black' }, counts: { '술': 0, '공부': 3, '연애': 1, '운동': 10 } },
  { id: 'user-4', nickname: '서연', emoji: '👩‍🎓', major: 'ict', appearance: { base: 'female', hair_length: 'medium', hair_color: 'pink' }, counts: { '술': 1, '공부': 10, '연애': 0, '운동': 4 } },
];

export function initialSocialState() {
  return {
    version: 1,
    rooms: DEMO_USERS.map(user => ({ id: `room-${user.id}`, owner_id: user.id, name: `${user.nickname}의 라운지`, member_ids: [user.id] })),
    invitations: [{ id: 'welcome-invitation', room_id: 'room-user-2', sender_id: 'user-2', recipient_id: DEMO_ME, status: 'pending' }],
  };
}

export function searchUsers(query, currentUser = DEMO_ME) {
  const normalized = query.trim().toLocaleLowerCase('ko');
  return normalized ? DEMO_USERS.filter(user => user.id !== currentUser && user.nickname.toLocaleLowerCase('ko').includes(normalized)) : [];
}

export function sendInvitation(state, { actor, recipient, roomId, id }) {
  const room = state.rooms.find(item => item.id === roomId);
  if (!room || room.owner_id !== actor) throw new Error('라운지 주인만 친구를 초대할 수 있어요.');
  if (!DEMO_USERS.some(user => user.id === recipient) || actor === recipient) throw new Error('초대할 친구를 확인해 주세요.');
  if (room.member_ids.includes(recipient)) throw new Error('이미 이 라운지에 참여한 친구예요.');
  if (state.invitations.some(item => item.room_id === roomId && item.recipient_id === recipient && item.status === 'pending')) throw new Error('이미 초대를 보냈어요. 수락을 기다려 주세요.');
  if (state.invitations.some(item => item.id === id)) throw new Error('이미 처리된 초대입니다.');
  const invitation = { id, room_id: roomId, sender_id: actor, recipient_id: recipient, status: 'pending' };
  return { ...state, invitations: [...state.invitations, invitation] };
}

export function respondToInvitation(state, { actor, invitationId, accept }) {
  const invitation = state.invitations.find(item => item.id === invitationId);
  if (!invitation || invitation.recipient_id !== actor) throw new Error('받은 초대만 응답할 수 있어요.');
  if (invitation.status !== 'pending') throw new Error('이미 처리한 초대예요.');
  if (!state.rooms.some(room => room.id === invitation.room_id)) throw new Error('라운지를 찾을 수 없어요.');
  return {
    ...state,
    invitations: state.invitations.map(item => item.id === invitationId ? { ...item, status: accept ? 'accepted' : 'declined' } : item),
    rooms: state.rooms.map(room => room.id === invitation.room_id && accept ? { ...room, member_ids: [...new Set([...room.member_ids, actor])] } : room),
  };
}
