import test from 'node:test';
import assert from 'node:assert/strict';
import { initialSocialState, searchUsers, sendInvitation, respondToInvitation } from '../static/social-model.mjs';

const invite = state => sendInvitation(state, { actor:'user-1', recipient:'user-2', roomId:'room-user-1', id:'invite-2' });

test('nickname search excludes self and handles blank or unmatched names',()=>{
  assert.equal(searchUsers(' 민지 ')[0].id,'user-2');
  assert.deepEqual(searchUsers('나'),[]);assert.deepEqual(searchUsers(''),[]);assert.deepEqual(searchUsers('없는이름'),[]);
});
test('sending an invitation does not add a member until recipient accepts',()=>{
  const initial=initialSocialState(), pending=invite(initial);
  assert.deepEqual(pending.rooms[0].member_ids,['user-1']);
  assert.equal(pending.invitations.at(-1).status,'pending');
  const accepted=respondToInvitation(pending,{actor:'user-2',invitationId:'invite-2',accept:true});
  assert.deepEqual(accepted.rooms[0].member_ids,['user-1','user-2']);
  assert.equal(initial.invitations.length,1);
  assert.throws(()=>respondToInvitation(accepted,{actor:'user-2',invitationId:'invite-2',accept:true}));
});
test('declining does not grant membership and allows a fresh invitation',()=>{
  const state=respondToInvitation(invite(initialSocialState()),{actor:'user-2',invitationId:'invite-2',accept:false});
  assert.deepEqual(state.rooms[0].member_ids,['user-1']);
  assert.equal(sendInvitation(state,{actor:'user-1',recipient:'user-2',roomId:'room-user-1',id:'new-id'}).invitations.at(-1).status,'pending');
});
test('rejects self, unknown users, non-owners, duplicates, and another user accepting',()=>{
  const state=invite(initialSocialState());
  assert.throws(()=>invite(state));
  for(const recipient of ['user-1','missing'])assert.throws(()=>sendInvitation(state,{actor:'user-1',recipient,roomId:'room-user-1',id:'x'}));
  assert.throws(()=>sendInvitation(state,{actor:'user-3',recipient:'user-2',roomId:'room-user-1',id:'x'}));
  assert.throws(()=>respondToInvitation(state,{actor:'user-3',invitationId:'invite-2',accept:true}));
  const accepted=respondToInvitation(state,{actor:'user-2',invitationId:'invite-2',accept:true});
  assert.throws(()=>sendInvitation(accepted,{actor:'user-1',recipient:'user-2',roomId:'room-user-1',id:'new'}));
});
