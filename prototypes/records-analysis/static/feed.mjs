export function createFeed({ api, config }) {
  const $ = selector => document.querySelector(selector);
  let nextCursor, loading = false, revision = 0, searchRevision = 0;
  let contacts = { friends: [], incoming: [], outgoing: [] }, results = [];
  const enabled = config.feedMode === 'server';
  const message = (selector, text, error = false) => { $(selector).textContent = text; $(selector).classList.toggle('error', error); };

  function row(person, caption = '') {
    const item = document.createElement('div'); item.className = 'person-row';
    const text = document.createElement('div'); text.className = 'person-text';
    const name = document.createElement('strong'); name.textContent = person.nickname;
    const note = document.createElement('small'); note.textContent = caption;
    text.append(name, note); item.append(text); return item;
  }
  function button(label, handler, secondary = false) {
    const element = document.createElement('button'); element.type = 'button'; element.textContent = label;
    if (secondary) element.className = 'secondary';
    element.onclick = async () => { element.disabled = true; try { await handler(); } finally { if (element.isConnected) element.disabled = false; } };
    return element;
  }
  function placeholder(container, text) {
    const p = document.createElement('p'); p.className = 'empty'; p.textContent = text; container.append(p);
  }
  function postCard(post) {
    const article = document.createElement('article'); article.className = 'feed-card'; article.dataset.postId = post.id;
    const header = document.createElement('header'); header.className = 'feed-card-header';
    const name = document.createElement('strong'); name.textContent = post.author.nickname;
    const date = document.createElement('time'); date.dateTime = post.created_at;
    date.textContent = new Date(post.created_at).toLocaleString('ko-KR', { month:'long', day:'numeric', hour:'2-digit', minute:'2-digit' });
    header.append(name, date); article.append(header);
    if (post.image_url) {
      const image = document.createElement('img'); image.src = post.image_url; image.alt = post.author.nickname + '님의 게시 사진';
      image.loading = 'lazy'; image.className = 'feed-photo';
      image.onerror = () => { const notice=document.createElement('p'); notice.className='empty'; notice.textContent='사진을 불러오지 못했어요. 피드를 새로고침해 주세요.'; image.replaceWith(notice); };
      article.append(image);
    }
    if (post.text) { const text = document.createElement('p'); text.className='feed-caption'; text.textContent=post.text; article.append(text); }
    const tags=document.createElement('div'); tags.className='tags feed-tags';
    for (const keyword of post.keywords || []) { const tag=document.createElement('span'); tag.className='tag'; tag.textContent='#'+keyword; tags.append(tag); }
    article.append(tags);
    if(post.analysis_status !== 'completed') {
      const status=document.createElement('p');status.className='muted feed-analysis-status';
      status.textContent=post.analysis_status==='failed'?'게시물은 저장됐어요. 활동 분석은 완료되지 않았어요.':'게시물의 활동을 분석하고 있어요.';article.append(status);
    }
    return article;
  }
  async function load(reset = true) {
    if (!enabled) { message('#feed-status','로그인한 통합 앱에서 게시물 피드를 이용할 수 있어요.'); return; }
    if (!reset && (loading || !nextCursor)) return;
    const requestId=++revision, cursor=reset?null:nextCursor;
    loading=true;$('#refresh-feed').disabled=true;$('#more-feed').disabled=true;$('#feed-list').setAttribute('aria-busy','true');
    if(reset){$('#feed-list').replaceChildren();nextCursor=null;$('#more-feed').hidden=true;}
    message('#feed-status','게시물을 불러오고 있어요…');
    try {
      const data=await api.feed($('#feed-scope').value,cursor);
      if(requestId!==revision)return;
      const known=new Set([...$('#feed-list').querySelectorAll('[data-post-id]')].map(item=>item.dataset.postId));
      for(const post of data.posts){if(!known.has(post.id)){$('#feed-list').append(postCard(post));known.add(post.id);}}
      nextCursor=data.next_cursor;$('#more-feed').hidden=!nextCursor;
      if(!known.size)placeholder($('#feed-list'),$('#feed-scope').value==='friends'?'친구의 게시물이 아직 없어요. 친구를 등록하고 서로의 기록을 만나보세요.':'아직 게시물이 없어요. 메인에서 첫 사진이나 글을 올려보세요.');
      message('#feed-status',known.size?known.size+'개의 게시물 · 최신 업로드순':'');
    }catch(error){if(requestId===revision)message('#feed-status',error.message,true);}
    finally{if(requestId===revision){loading=false;$('#refresh-feed').disabled=false;$('#more-feed').disabled=false;$('#feed-list').setAttribute('aria-busy','false');}}
  }
  function renderSearch() {
    $('#contact-results').replaceChildren();
    for(const person of results){
      const friend=contacts.friends.some(item=>item.id===person.id);
      const outgoing=contacts.outgoing.some(item=>item.person.id===person.id);
      const incoming=contacts.incoming.some(item=>item.person.id===person.id);
      const item=row(person,'사용자 '+person.id.slice(0,8));
      const control=button(friend?'친구':outgoing?'요청 보냄':incoming?'받은 요청':'친구 요청',async()=>{
        try{await api.requestFriend(person.id);await loadContacts();message('#contact-status',person.nickname+'님에게 친구 요청을 보냈어요.');}
        catch(error){message('#contact-status',error.message,true);}
      });
      control.disabled=friend||outgoing||incoming;item.append(control);$('#contact-results').append(item);
    }
  }
  async function loadContacts() {
    contacts=await api.contacts();
    for(const name of ['incoming','outgoing','friends'])$('#contact-'+name).replaceChildren();
    if(!contacts.friends.length)placeholder($('#contact-friends'),'아직 등록된 친구가 없어요.');
    contacts.friends.forEach(person=>$('#contact-friends').append(row(person,'서로의 게시물을 볼 수 있어요.')));
    if(!contacts.outgoing.length)placeholder($('#contact-outgoing'),'보낸 친구 요청이 없어요.');
    contacts.outgoing.forEach(item=>$('#contact-outgoing').append(row(item.person,'수락 대기 중')));
    if(!contacts.incoming.length)placeholder($('#contact-incoming'),'받은 친구 요청이 없어요.');
    for(const item of contacts.incoming){
      const element=row(item.person,'친구 요청을 보냈어요.');
      const respond=async accept=>{
        try{await api.respondFriend(item.id,accept);await loadContacts();await load();message('#contact-status',accept?'친구가 되었어요. 이제 서로의 게시물이 피드에 보여요.':'친구 요청을 거절했어요.');}
        catch(error){message('#contact-status',error.message,true);}
      };
      element.append(button('수락',()=>respond(true)),button('거절',()=>respond(false),true));$('#contact-incoming').append(element);
    }
    renderSearch();
  }
  $('#feed-scope').onchange=()=>load();$('#refresh-feed').onclick=()=>load();$('#more-feed').onclick=()=>load(false);
  $('#open-contacts').disabled=!enabled;
  $('#open-contacts').onclick=async()=>{$('#contacts-dialog').showModal();message('#contact-status','친구 목록을 불러오고 있어요…');try{await loadContacts();message('#contact-status','');}catch(error){message('#contact-status',error.message,true);}};
  $('#close-contacts').onclick=()=>$('#contacts-dialog').close();
  $('#refresh-contacts').onclick=async()=>{try{await loadContacts();message('#contact-status','목록을 갱신했어요.');}catch(error){message('#contact-status',error.message,true);}};
  $('#contact-search').onsubmit=async event=>{
    event.preventDefault();const query=$('#contact-query').value.trim();if(!query){message('#contact-status','닉네임을 입력해 주세요.');return;}
    const id=++searchRevision;$('#contact-search button').disabled=true;message('#contact-status','친구를 찾고 있어요…');
    try{const people=await api.findContacts(query);if(id!==searchRevision)return;results=people;await loadContacts();message('#contact-status',people.length?people.length+'명의 사용자를 찾았어요.':'닉네임을 설정한 가입자가 없어요. 친구가 먼저 계정을 만들어야 해요.');}
    catch(error){if(id===searchRevision)message('#contact-status',error.message,true);}
    finally{if(id===searchRevision)$('#contact-search button').disabled=false;}
  };
  return { load };
}
