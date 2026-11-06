import { api } from './api.mjs';
import { config } from './app-config.mjs';
import { assets, renderCharacter, countsFromProgress, categoryLabel } from './character.mjs';
import { createLounge } from './lounge-view.mjs';
import { createFeed } from './feed.mjs';

const $ = selector => document.querySelector(selector);
const lounge = createLounge($('#lounge'));
let me, progress = [], rooms = [], invitations = [], members = [], currentRoom, searchResults = [];
const views = ['lounge', 'home', 'feed'];
const requestedView = new URLSearchParams(location.search).get('view');
let view = views.includes(requestedView) ? requestedView : 'home';
let feedController;
let socialRevision = 0, searching = 0, recordId = crypto.randomUUID(), previewUrl, busy = false, posted = false;
const status = (selector, message, error = false) => { $(selector).textContent = message; $(selector).classList.toggle('error', error); };

function showView(next) {
  view = next;
  $('#screen').dataset.view = next;
  for (const name of views) {
    const active = name === next;
    $('#' + name + '-panel').inert = !active;
    $('#' + name + '-panel').setAttribute('aria-hidden', String(!active));
    if (active) $('#' + name + '-tab').setAttribute('aria-current', 'page');
    else $('#' + name + '-tab').removeAttribute('aria-current');
  }
  if(next==='feed' && me)feedController?.load();
}
$('#home-tab').onclick = () => showView('home');
$('#lounge-tab').onclick = () => showView('lounge');
$('#feed-tab').onclick = () => showView('feed');
function swipe(dx, origin) {
  const index=views.indexOf(origin)+(dx>0?-1:1);
  showView(views[Math.max(0,Math.min(views.length-1,index))]);
}
showView(view);
let touch;
$('#screen').addEventListener('pointerdown', event => {
  if (event.pointerType !== 'touch' || event.target.closest('button,input,textarea,select,a,summary,details')) return;
  touch = { x: event.clientX, y: event.clientY, view };
});
window.addEventListener('pointerup', event => {
  if (!touch) return;
  const dx = event.clientX - touch.x, dy = event.clientY - touch.y, origin=touch.view; touch = undefined;
  if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
  swipe(dx,origin);
});
window.addEventListener('pointercancel', () => { touch = undefined; });
// Vertical browser scrolling can cancel a pointer gesture; touch endpoints retain the swipe direction.
let startTouch;
$('#screen').addEventListener('touchstart', event => {
  if (event.touches.length !== 1 || event.target.closest('button,input,textarea,select,a,summary,details')) { startTouch = undefined; return; }
  startTouch = { x: event.touches[0].clientX, y: event.touches[0].clientY, view };
}, { passive: true });
$('#screen').addEventListener('touchend', event => {
  if (!startTouch || !event.changedTouches.length) return;
  const dx = event.changedTouches[0].clientX-startTouch.x, dy = event.changedTouches[0].clientY-startTouch.y, origin=startTouch.view; startTouch=undefined; touch=undefined;
  if (Math.abs(dx)>65 && Math.abs(dx)>Math.abs(dy)*1.5) swipe(dx,origin);
}, { passive: true });
$('#screen').addEventListener('touchcancel', () => { startTouch=undefined; });

function renderMe() {
  if (!me) return;
  renderCharacter($('#main-character'), progress, me.emoji, me.color, me);
  $('#activity-counts').replaceChildren(...progress.map(item => {
    const card = document.createElement('div'); card.className = 'activity-card';
    const category = document.createElement('span'); category.textContent = assets.icons[item.category] + ' ' + categoryLabel(item.category);
    const count = document.createElement('strong'); count.textContent = item.count + '회';
    const level = document.createElement('span'); level.textContent = 'Lv.' + item.level;
    card.append(category,count,level);return card;
  }));
  const total = progress.reduce((sum,item)=>sum+item.count,0);
  $('#character-description').textContent = total ? '지금까지 쌓인 활동: ' + total + '회' : '첫 기록을 올려 캐릭터를 꾸며보세요.';
  updateLounge();
}
function updateLounge() {
  lounge.setPeople(members.map(user => user.id === me?.id ? { ...user, ...me, counts: countsFromProgress(progress) } : user));
}
async function loadProfile() {
  try {
    const [profile, data] = await Promise.all([api.me(), api.progress()]);
    me=profile;progress=data.progress;
    $('#profile-name').textContent=profile.nickname;
    $('#open-post').disabled=false;renderMe();
    status('#global-status','');$('#reload').hidden=true;
    await loadSocial();
    if(view==='feed')feedController.load();
  } catch (error) {
    status('#global-status',error.message,true);$('#reload').hidden=false;
  }
}
$('#reload').onclick=loadProfile;

function nameOf(id) { return (config.socialMode === 'demo' ? api.demoUsers.find(user=>user.id===id)?.nickname : undefined) || members.find(user=>user.id===id)?.nickname || '친구'; }
function rowFor(emoji, title, subtitle = '') {
  const row = document.createElement('div');row.className='person-row';
  const avatar=document.createElement('span');avatar.className='person-avatar';avatar.textContent=emoji;
  const text=document.createElement('div');text.className='person-text';
  const heading=document.createElement('strong');heading.textContent=title;text.append(heading);
  if(subtitle){const sub=document.createElement('small');sub.textContent=subtitle;text.append(sub);}
  row.append(avatar,text);return row;
}
function empty(container,message) {
  const p=document.createElement('p');p.className='empty';p.textContent=message;container.replaceChildren(p);
}
function action(label, fn, secondary = false) {
  const button=document.createElement('button');button.type='button';button.textContent=label;if(secondary)button.className='secondary';
  button.onclick=async()=>{button.disabled=true;try {await fn();} finally {if(button.isConnected)button.disabled=false;}};
  return button;
}
function renderInvitations() {
  const incoming=invitations.filter(item=>item.recipient_id===me?.id && item.status==='pending');
  $('#inbox-count').textContent=String(incoming.length);$('#invite-badge').textContent=String(incoming.length);$('#invite-badge').hidden=!incoming.length;
  const inbox=$('#received-invitations');inbox.replaceChildren();
  if(!incoming.length)empty(inbox,'아직 받은 초대가 없어요.');
  for(const item of incoming) {
    const sender=item.sender?.nickname || nameOf(item.sender_id);
    const row=rowFor('✉️',sender+'님의 라운지 초대','수락하면 이 친구의 라운지에 참여해요.');
    const actions=document.createElement('div');actions.className='person-actions';
    const respond=async accept=>{
      try{await api.respond(item.id,accept);if(accept)currentRoom=item.room_id;await loadSocial();status('#inbox-status',accept?'초대를 수락했어요. 라운지에서 만나요!':'초대를 거절했어요.');if(accept){$('#inbox-dialog').close();showView('lounge');}}
      catch(error){status('#inbox-status',error.message,true);}
    };
    actions.append(action('수락',()=>respond(true)),action('거절',()=>respond(false),true));row.append(actions);inbox.append(row);
  }
  const sent=$('#sent-invitations');sent.replaceChildren();
  const outgoing=invitations.filter(item=>item.sender_id===me?.id && item.room_id===currentRoom);
  if(!outgoing.length)empty(sent,'아직 보낸 초대가 없어요.');
  for(const item of outgoing) {
    const labels={pending:'수락 대기 중',accepted:'수락 완료',declined:'거절됨'};
    sent.append(rowFor('✉️',item.recipient?.nickname || nameOf(item.recipient_id),labels[item.status] || item.status));
  }
  renderSearchResults();
}
function renderSearchResults() {
  const container=$('#search-results');container.replaceChildren();
  for(const user of searchResults) {
    const row=rowFor(user.emoji || '🧑',user.nickname);
    const joined=members.some(member=>member.id===user.id);
    const pending=invitations.some(item=>item.room_id===currentRoom && item.recipient_id===user.id && item.status==='pending');
    const button=action(joined?'참여 중':pending?'초대 보냄':'초대',async()=>{
      try{await api.invite(currentRoom,user.id);await loadSocial();status('#friend-status',user.nickname+'님에게 초대를 보냈어요.');}
      catch(error){status('#friend-status',error.message,true);}
    });
    button.disabled=joined||pending||!currentRoom||rooms.find(room=>room.id===currentRoom)?.owner_id!==me?.id;
    row.append(button);container.append(row);
  }
}
async function loadSocial() {
  const revision=++socialRevision;
  try {
    const [nextRooms,nextInvites]=await Promise.all([api.rooms(),api.invitations()]);
    if(revision!==socialRevision)return;
    rooms=nextRooms;invitations=nextInvites;
    if(!rooms.some(room=>room.id===currentRoom))currentRoom=rooms[0]?.id;
    const nextMembers=currentRoom?await api.members(currentRoom):[];
    if(revision!==socialRevision)return;
    members=nextMembers;
    const select=$('#room-select');select.replaceChildren();
    for(const room of rooms){const option=document.createElement('option');option.value=room.id;option.textContent=room.name;select.append(option);}
    if(currentRoom)select.value=currentRoom;
    select.disabled=!rooms.length;
    $('#open-friends').disabled=!currentRoom||rooms.find(room=>room.id===currentRoom)?.owner_id!==me?.id;
    status('#room-status',members.length+'명이 함께 있어요 · 수락한 친구가 표시됩니다.');
    $('#room-members').replaceChildren(...members.map(user=>{const chip=document.createElement('span');chip.className='member-chip';chip.textContent=user.nickname+(user.id===me?.id?' (나)':'');return chip;}));
    updateLounge();renderInvitations();
  } catch(error){status('#room-status',error.message,true);$('#open-friends').disabled=true;throw error;}
}
$('#room-select').onchange=async event=>{
  currentRoom=event.target.value;members=[];updateLounge();$('#room-members').replaceChildren();$('#open-friends').disabled=true;
  status('#room-status','라운지를 불러오고 있어요…');
  try{await loadSocial();}catch(error){status('#global-status',error.message,true);}
};
$('#friend-search').onsubmit=async event=>{
  event.preventDefault();const revision=++searching;const query=$('#friend-query').value.trim();
  if(!query){status('#friend-status','닉네임을 입력해 주세요.');return;}
  status('#friend-status','친구를 찾고 있어요…');$('#friend-search button').disabled=true;
  try{const results=await api.search(query);if(revision!==searching)return;searchResults=results;renderSearchResults();status('#friend-status',results.length?results.length+'명의 친구를 찾았어요.':'검색한 닉네임의 친구가 없어요.');}
  catch(error){status('#friend-status',error.message,true);}
  finally{if(revision===searching)$('#friend-search button').disabled=false;}
};

for(const name of ['friends','inbox','demo']) {
  $('#close-'+name).onclick=()=>$('#'+name+'-dialog').close();
}
$('#open-friends').onclick=()=>{$('#friends-dialog').showModal();$('#friend-query').focus();};
$('#open-inbox').onclick=async()=>{$('#inbox-dialog').showModal();try{await loadSocial();}catch(error){status('#inbox-status',error.message,true);}};
async function renderDemoInbox() {
  const userId=$('#demo-user').value;
  try {
    const items=await api.demoInbox(userId), container=$('#demo-invitations');container.replaceChildren();
    status('#demo-status',nameOf(userId)+'님이 받은 초대입니다.');
    if(!items.length)empty(container,'아직 받은 초대가 없어요. 내 라운지에서 이 친구에게 먼저 초대해 보세요.');
    for(const item of items) {
      const row=rowFor('✉️',nameOf(item.sender_id)+'님의 초대');
      const respond=async accept=>{
        try{await api.demoRespond(userId,item.id,accept);await loadSocial();await renderDemoInbox();status('#demo-status',accept?nameOf(userId)+'님이 수락했어요. 라운지에 나타납니다.':nameOf(userId)+'님이 초대를 거절했어요.');}
        catch(error){status('#demo-status',error.message,true);}
      };
      row.append(action('수락',()=>respond(true)),action('거절',()=>respond(false),true));container.append(row);
    }
  }catch(error){status('#demo-status',error.message,true);}
}
$('#open-demo').onclick=()=>{$('#demo-dialog').showModal();renderDemoInbox();};
$('#demo-user').onchange=renderDemoInbox;
$('#demo-tools').hidden=config.socialMode!=='demo';$('#demo-notice').hidden=config.socialMode!=='demo';
window.addEventListener('storage',event=>{if(event.key?.startsWith('campus-social-demo-v1') && me)loadSocial().catch(error=>status('#global-status',error.message,true));});
$('#logout-app').hidden=config.profileMode!=='server';
$('#logout-app').onclick=async()=>{
  if(busy){status('#global-status','게시 처리가 끝난 후 로그아웃해 주세요.');return;}
  $('#logout-app').disabled=true;
  try{await api.logout();location.assign(config.loginUrl || '/');}
  catch(error){status('#global-status',error.message,true);$('#logout-app').disabled=false;}
};

function clearPreview() {
  if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=undefined;
  $('#post-preview').removeAttribute('src');$('#preview-box').hidden=true;
}
function resetPost() {
  $('#post-form').reset();clearPreview();recordId=crypto.randomUUID();posted=false;
  $('#post-form').hidden=false;$('#post-result').hidden=true;status('#post-status','');
}
$('#open-post').disabled=true;
$('#open-post').onclick=()=>{if(posted)resetPost();$('#post-dialog').showModal();$('#post-text').focus();};
$('#close-post').onclick=()=>{if(!busy)$('#post-dialog').close();};
$('#post-dialog').addEventListener('cancel',event=>{if(busy)event.preventDefault();});
$('#show-character').onclick=()=>{$('#post-dialog').close();showView('home');};
$('#show-feed').hidden=config.feedMode!=='server';
$('#show-feed').onclick=()=>{$('#post-dialog').close();showView('feed');};
$('#post-form').addEventListener('input',()=>{recordId=crypto.randomUUID();});
$('#post-image').onchange=()=>{
  clearPreview();const image=$('#post-image').files[0];if(!image)return;
  recordId=crypto.randomUUID();
  if(image.size>10*1024*1024 || !['image/jpeg','image/png','image/webp'].includes(image.type)) {
    status('#post-status','10MB 이하의 JPG, PNG, WEBP 사진을 선택해 주세요.',true);$('#post-image').value='';return;
  }
  status('#post-status','');previewUrl=URL.createObjectURL(image);$('#post-preview').src=previewUrl;$('#preview-box').hidden=false;
};
$('#remove-image').onclick=()=>{$('#post-image').value='';recordId=crypto.randomUUID();clearPreview();};
$('#post-form').onsubmit=async event=>{
  event.preventDefault();if(busy)return;
  const text=$('#post-text').value.trim(), image=$('#post-image').files[0];
  if(!text&&!image){status('#post-status','글 또는 사진을 하나 이상 올려 주세요.',true);return;}
  busy=true;$('#post-fields').disabled=true;$('#close-post').disabled=true;
  $('#post-form').setAttribute('aria-busy','true');status('#post-status','기록에서 키워드를 찾고 캐릭터에 반영하고 있어요…');
  const body=new FormData();body.append('record_id',recordId);body.append('text',text);if(image)body.append('image',image);
  try {
    const result=await api.post(body);progress=result.progress;renderMe();posted=true;
    const tags=result.keywords.map(keyword=>{const tag=document.createElement('span');tag.className='tag';tag.textContent='#'+keyword;return tag;});
    $('#result-keywords').replaceChildren(...tags);
    $('#result-category').textContent=result.category ? '분류: '+categoryLabel(result.category)+' · '+result.category_keywords.join(', ') : '관련 활동 키워드를 찾지 못했어요.';
    const exerciseLoss=result.stack_changes?.['운동'] === -1;
    const awardMessage=categoryLabel(result.category)+' 활동이 1회 쌓였어요.'+(exerciseLoss?' 건강 횟수는 1회 줄었어요.':result.category==='술'?' 건강 횟수가 0회라 더 줄어들지 않았어요.':'');
    $('#result-effect').textContent=result.needs_review?'분류가 불명확해 활동 누적을 보류했어요.':result.awarded?awardMessage: '이미 반영한 기록이라 중복 누적하지 않았어요.';
    $('#post-result h3').textContent='게시완료!';
    $('#post-form').hidden=true;$('#post-result').hidden=false;status('#post-status','분석 완료');
    status('#global-status',result.awarded?categoryLabel(result.category)+' +1'+(exerciseLoss?' · 건강 −1':'')+' · 캐릭터가 갱신됐어요.':'게시완료!');
  }catch(error){status('#post-status',error.message+' 입력은 유지되어 있어요.',true);}
  finally{busy=false;$('#post-fields').disabled=false;$('#close-post').disabled=false;$('#post-form').setAttribute('aria-busy','false');}
};
feedController=createFeed({api,config});
loadProfile();

