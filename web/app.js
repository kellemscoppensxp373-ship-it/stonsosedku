const pinKey = 'tg-orchestrator-pin';
let pin = sessionStorage.getItem(pinKey) || '';
const headers = () => ({'Content-Type':'application/json', ...(pin ? {'X-Web-PIN':pin} : {})});
const el = id => document.getElementById(id);
function authPrompt(){pin=prompt('Введите PIN локальной панели:')||'';sessionStorage.setItem(pinKey,pin)}
async function request(path, options={}){
  let response=await fetch(path,{...options,headers:{...headers(),...(options.headers||{})}});
  if(response.status===401){authPrompt();response=await fetch(path,{...options,headers:{...headers(),...(options.headers||{})}})}
  const payload=await response.json().catch(()=>({detail:'Ответ сервера не распознан'}));
  if(!response.ok) throw new Error(payload.detail||`HTTP ${response.status}`);
  return payload;
}
function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function render(data){
  const channels=data.channels||[],bots=data.bots||[];
  el('channel-count').textContent=channels.length;el('bot-count').textContent=bots.length;
  el('api-status').textContent=data.status.control_bot_configured?'Готов':'Не задан';
  el('api-detail').textContent=data.status.control_bot_configured?'Проверка только по запросу':'Добавьте CTRL_BOT_TOKEN в .env';
  const select=el('channel-select'),chosen=select.value;
  select.innerHTML='<option value="">Выберите канал</option>'+channels.map(c=>`<option value="${esc(c.id)}">${esc(c.title)} · ${esc(c.id)}</option>`).join('');
  if(channels.some(c=>c.id===chosen))select.value=chosen;
  el('inventory-total').textContent=`${channels.length} каналов · ${bots.length} ботов`;
  if(!channels.length){el('inventory-list').innerHTML='<div class="empty">Пока нет записей. Добавьте канал, чтобы начать.</div>';return}
  el('inventory-list').innerHTML=channels.map(channel=>{
    const related=bots.filter(bot=>bot.channel_id===channel.id);
    const chips=related.length?related.map(bot=>`<span class="bot-chip">@${esc(bot.username)} <span class="unverified">· ${esc(bot.status)}</span><button class="remove" title="Удалить бота" data-kind="bots" data-id="${esc(bot.username)}">×</button></span>`).join(''):'<span class="muted">Нет записанных ботов</span>';
    return `<div class="channel-card"><div class="channel-title"><span>${esc(channel.title)}</span><button class="remove" title="Удалить канал" data-kind="channels" data-id="${esc(channel.id)}">×</button></div><div class="channel-id">${esc(channel.id)}</div><div class="channel-bots">${chips}</div></div>`;
  }).join('');
}
function addLog(message){const row=document.createElement('div');row.className='console-line';const t=document.createElement('span');t.className='time';t.textContent=new Date().toLocaleTimeString('ru-RU',{hour12:false});const m=document.createElement('span');m.className='log-info';m.textContent=message;row.append(t,m);el('console').append(row);while(el('console').children.length>120)el('console').firstChild.remove();el('console').scrollTop=el('console').scrollHeight}
async function load(){try{const data=await request('/api/state');render(data);el('slot-timer').textContent=`${Number(data.status.seconds_until_slot).toFixed(1)}s`}catch(e){addLog(`Не удалось загрузить состояние: ${e.message}`)}}
el('channel-form').addEventListener('submit',async e=>{e.preventDefault();const form=new FormData(e.currentTarget);try{await request('/api/channels',{method:'POST',body:JSON.stringify({title:form.get('title'),id:form.get('id')})});e.currentTarget.reset();await load()}catch(err){alert(err.message)}});
el('bot-form').addEventListener('submit',async e=>{e.preventDefault();const form=new FormData(e.currentTarget);try{await request('/api/bots',{method:'POST',body:JSON.stringify({username:form.get('username'),channel_id:form.get('channel_id'),note:form.get('note')})});e.currentTarget.reset();await load()}catch(err){alert(err.message)}});
el('inventory-list').addEventListener('click',async e=>{const button=e.target.closest('[data-kind]');if(!button)return;try{await request(`/api/${button.dataset.kind}/${encodeURIComponent(button.dataset.id)}`,{method:'DELETE'});await load()}catch(err){alert(err.message)}});
el('refresh').addEventListener('click',load);
el('diagnose').addEventListener('click',async()=>{const button=el('diagnose'),result=el('diagnose-result');button.disabled=true;result.textContent='Ожидание свободного диагностического слота…';try{const data=await request('/api/diagnostics/bot-api',{method:'POST'});result.textContent=`Успешно: @${data.username} (ID ${data.id})`;el('api-status').textContent='Online';addLog('Проверка Bot API завершена успешно')}catch(e){result.textContent=e.message;addLog(`Ошибка диагностики: ${e.message}`)}finally{button.disabled=false;await load()}});
function connect(){const scheme=location.protocol==='https:'?'wss':'ws';const socket=new WebSocket(`${scheme}://${location.host}/ws${pin?'?pin='+encodeURIComponent(pin):''}`);socket.onmessage=event=>{const item=JSON.parse(event.data);if(item.type==='snapshot'||item.type==='state')render(item.type==='snapshot'?item.data:item.data);if(item.type==='log')addLog(item.message)};socket.onclose=()=>setTimeout(connect,2500);socket.onerror=()=>socket.close()}
load();connect();setInterval(()=>{const value=parseFloat(el('slot-timer').textContent);if(Number.isFinite(value)&&value>0)el('slot-timer').textContent=`${Math.max(0,value-.1).toFixed(1)}s`},100);
