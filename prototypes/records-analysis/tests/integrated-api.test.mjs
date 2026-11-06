import test from 'node:test';
import assert from 'node:assert/strict';

test('real local profile scopes example invitations and uses the authenticated account id',async()=>{
  const store=new Map();
  globalThis.CAMPUS_CONFIG={profileMode:'server',socialMode:'demo',demoMe:{id:'real-account-uuid',nickname:'내닉네임',color:'blue',emoji:'🧑'}};
  globalThis.localStorage={getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value)};
  Object.defineProperty(globalThis,'navigator',{value:{},configurable:true});
  globalThis.fetch=async url=>{assert.equal(url,'/api/me');return {ok:true,status:200,json:async()=>globalThis.CAMPUS_CONFIG.demoMe};};
  const {api}=await import('../static/api.mjs');
  assert.equal((await api.me()).id,'real-account-uuid');
  const room=(await api.rooms())[0];assert.equal(room.owner_id,'real-account-uuid');assert.ok(room.name.includes('내닉네임'));
  assert.equal((await api.members(room.id))[0].nickname,'내닉네임');
  await api.invite(room.id,'user-2');
  const invitation=(await api.invitations()).find(item=>item.sender_id==='real-account-uuid');
  assert.equal((await api.members(room.id)).length,1);
  await api.demoRespond('user-2',invitation.id,true);
  assert.deepEqual((await api.members(room.id)).map(user=>user.id),['real-account-uuid','user-2']);
  assert.ok([...store.keys()].every(key=>key.endsWith(':real-account-uuid')));
});
