import { api, request } from './api.mjs';
import { config } from './app-config.mjs';
let historyTimer;
const titleSelect = document.querySelector('#title-select');
async function titles() {
  try {
    const options = await request('/api/titles');
    titleSelect.replaceChildren(new Option('대표 칭호 없음',''));
    for (const item of options) {
      const option = new Option(item.name+(item.earned?'':' · 미획득'),item.id,item.selected,item.selected);
      option.disabled = !item.earned;titleSelect.append(option);
    }
    const summary = document.querySelector('#title-description');
    summary.textContent = options.map(item=>(item.earned?'✓ ':'○ ')+item.name+' · '+item.description).join(' / ');
  } catch (error) { document.querySelector('#title-description').textContent=error.message; }
}
titleSelect.addEventListener('change',async()=>{
  try {
    await request('/api/titles/selected',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title_id:titleSelect.value||null})});
    window.dispatchEvent(new Event('campus:refresh-profile'));
  } catch(error) {document.querySelector('#title-description').textContent=error.message;}
});
window.addEventListener('campus:state-updated',()=>{titles();loadHistory();window.dispatchEvent(new Event('campus:refresh-profile'));});
document.querySelector('#open-history').addEventListener('click',()=>{document.querySelector('#history-dialog').showModal();loadHistory();});
document.querySelector('#close-history').addEventListener('click',()=>{clearTimeout(historyTimer);document.querySelector('#history-dialog').close();});
async function loadHistory() {
  clearTimeout(historyTimer);
  try {
    const records=await request('/api/records');const host=document.querySelector('#history-list');host.replaceChildren();
    for(const record of records) {
      const row=document.createElement('article');row.className='history-item';
      const text=document.createElement('p');text.textContent=(record.source==='demo'?'[샘플] ':'')+(record.text||'사진 기록');row.append(text);
      const status=document.createElement('small');status.textContent=record.analysis?.summary||record.analysis_error?.message||record.status;row.append(status);
      if(record.has_image){const image=document.createElement('img');image.src=`/api/records/${record.id}/image`;image.alt='내 기록 사진';image.loading='lazy';row.append(image);}
      if(record.status==='failed'||record.stat_status==='failed') {
        const button=document.createElement('button');button.textContent='다시 처리';button.onclick=async()=>{button.disabled=true;try{await request(`/api/records/${record.id}/retry`,{method:'POST'});historyTimer=setTimeout(loadHistory,1000);window.dispatchEvent(new Event('campus:refresh-profile'));}catch(error){status.textContent=error.message;button.disabled=false;}};row.append(button);
      }
      host.append(row);
    }
    if(!records.length)host.textContent='아직 기록이 없어요.';
    if(document.querySelector('#history-dialog').open && !document.hidden && records.some(record=>['pending','processing'].includes(record.status)||(record.status==='completed'&&record.stat_status==='pending')))historyTimer=setTimeout(loadHistory,1500);
  } catch(error){document.querySelector('#history-list').textContent=error.message;}
}
document.querySelector('#analysis-mode').textContent=config.demoAnalysis?'샘플 체험 · AI 사진 분석 아님':'Gemini 사진·글 분석';
document.querySelector('#sample-options').hidden=!config.demoAnalysis;
document.querySelector('#gemini-disclosure').textContent=config.demoAnalysis?'샘플 활동을 직접 고르는 체험입니다. 사진을 AI로 분석하지 않습니다.':'글·사진 중 하나 이상 올려 주세요. 입력한 내용은 Google Gemini로 전송됩니다.';
titles();
