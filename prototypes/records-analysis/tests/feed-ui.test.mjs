import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { createFeed } from '../static/feed.mjs';

test('photo feed renders newest first, pages, registers friends, accepts requests and handles errors',async()=>{
  const html=await readFile(new URL('../static/index.html',import.meta.url),'utf8');
  const dom=new JSDOM(html,{url:'http://localhost/app'}),win=dom.window;
  globalThis.document=win.document;
  win.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  win.HTMLDialogElement.prototype.close=function(){this.open=false;};
  const $=selector=>document.querySelector(selector);
  const until=async predicate=>{for(let i=0;i<100;i++){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,5));}throw new Error('Feed did not reach expected state');};
  const entry=(id,author='나')=>({id,author:{id:author,nickname:author},text:'직접 쓴 <b>기록</b>',image_url:'/api/posts/'+id+'/image',keywords:['운동'],created_at:'2026-11-06T10:00:00Z',analysis_status:'completed',summary:'이 AI 이미지 설명은 보이면 안 됩니다.'});
  let requests=[],broken=false, friendState={friends:[],incoming:[{id:'received',person:{id:'peer',nickname:'준호'}}],outgoing:[]};
  const api={
    async feed(scope,before){requests.push([scope,before]);if(broken)throw new Error('다시 시도해 주세요.');if(scope==='mine')return {posts:[],next_cursor:null};return before?{posts:[entry('older')],next_cursor:null}:{posts:[entry('newest')],next_cursor:'page-two'};},
    async contacts(){return structuredClone(friendState);},
    async findContacts(query){assert.equal(query,'민지');return [{id:'target',nickname:'민지'}];},
    async requestFriend(id){assert.equal(id,'target');friendState.outgoing.push({id:'sent',person:{id:'target',nickname:'민지'}});},
    async respondFriend(id,accept){assert.equal(id,'received');assert.equal(accept,true);friendState.incoming=[];friendState.friends.push({id:'peer',nickname:'준호'});},
  };
  const feed=createFeed({api,config:{feedMode:'server'}});
  await feed.load();assert.equal($('#feed-list article').dataset.postId,'newest');
  assert.ok($('#feed-list img').src.endsWith('/api/posts/newest/image'));
  assert.ok($('#feed-list').textContent.includes('#운동'));
  assert.ok(!$('#feed-list').textContent.includes('AI 이미지 설명'));
  assert.equal($('#feed-list b'),null);
  $('#more-feed').click();await until(()=>$('#feed-list').children.length===2);
  assert.deepEqual([...document.querySelectorAll('#feed-list article')].map(element=>element.dataset.postId),['newest','older']);
  assert.equal($('#more-feed').hidden,true);
  $('#open-contacts').click();await until(()=>$('#contact-incoming button'));
  $('#contact-query').value='민지';$('#contact-search').dispatchEvent(new win.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>$('#contact-results button'));$('#contact-results button').click();
  await until(()=>$('#contact-outgoing').textContent.includes('수락 대기'));
  assert.equal($('#contact-results button').disabled,true);
  $('#contact-incoming button').click();await until(()=>$('#contact-friends').textContent.includes('준호'));
  assert.ok($('#contact-friends').textContent.includes('서로의 게시물'));
  $('#close-contacts').click();assert.equal($('#contacts-dialog').open,false);
  $('#feed-scope').value='mine';$('#feed-scope').dispatchEvent(new win.Event('change'));
  await until(()=>$('#feed-list .empty'));
  assert.equal($('#feed-list article'),null);
  assert.equal(requests.at(-1)[0],'mine');
  broken=true;await feed.load();assert.ok($('#feed-status').classList.contains('error'));
  assert.equal($('#refresh-feed').disabled,false);
  dom.window.close();
});
