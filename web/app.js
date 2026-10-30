'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names = {sos:'Yêu cầu hỗ trợ SOS',periodic:'Ảnh cập nhật định kỳ',manual:'Ảnh người nhà yêu cầu',drop:'Cảnh báo rơi gậy',privacy:'Thay đổi ảnh định kỳ',test:'Thử thiết bị'};
const sources = {test:'ESP32 thử nghiệm',chest:'Thiết bị ở ngực',cane:'Thiết bị ở gậy',phone:'Điện thoại',caregiver:'Người nhà',remote:'Nút tìm gậy cầm tay'};
const noticeNames = {sent:'Đã đẩy tới điện thoại',pending:'Đang chờ đẩy',no_device:'Chưa có máy bật thông báo',unavailable:'Máy chủ chưa bật thông báo đẩy',failed:'Đẩy thất bại (vẫn có trong hộp tin)'};
const stageNames = {sos:'Tin SOS',image:'Tin kèm ảnh',drop:'Tin rơi gậy'};
let firstMessages = true, messages = [], unreadMessages = 0, mutedSos = new Set(), audio = null, alarmTimer = null, installPrompt = null;
const timeText = t => t ? new Date(t*1000).toLocaleString('vi-VN') : 'Chưa có thời gian';
const age = t => t ? Math.max(0, Math.floor(Date.now()/1000-t)) : Infinity;
const ageText = t => {const s=age(t);return !Number.isFinite(s)?'chưa có':s<60?`${s} giây trước`:s<3600?`${Math.floor(s/60)} phút trước`:`${Math.floor(s/3600)} giờ trước`;};
const scene = () => `<div class="demo-scene"><svg viewBox="0 0 800 480" role="img" aria-label="Hình vẽ minh họa lối đi, không phải ảnh từ thiết bị"><rect width="800" height="480" fill="#dce8d9"/><rect y="0" width="800" height="245" fill="#d5e3df"/><circle cx="650" cy="88" r="39" fill="#f5edd0"/><path d="M0 240L160 146 300 250 468 168 620 220 800 157V330H0Z" fill="#bdcfb6"/><path d="M310 230H458L740 480H50Z" fill="#d8d5c1"/><path d="M340 230H430L568 480H204Z" fill="#ede8d7"/><path d="M387 240L391 480" stroke="#d7d2bf" stroke-width="2"/><path d="M290 313H488M247 383H530" stroke="#d5ceba" stroke-width="2"/><path d="M0 290Q135 242 304 260L204 480H0Z" fill="#8fa77d"/><path d="M454 247Q626 238 800 292V480H568Z" fill="#a1b98d"/><g fill="#638168"><ellipse cx="119" cy="171" rx="70" ry="103"/><ellipse cx="697" cy="188" rx="65" ry="90"/></g><path d="M119 193V368M697 208V379" stroke="#73806a" stroke-width="12"/><g fill="#b3c895"><ellipse cx="48" cy="341" rx="66" ry="33"/><ellipse cx="766" cy="358" rx="92" ry="39"/></g><path d="M601 293H680V310H601Z" fill="#a69d7b"/><path d="M615 309V340M668 309V340" stroke="#888b71" stroke-width="5"/><path d="M26 27H58M26 27V59M774 27H742M774 27V59M26 453H58M26 453V421M774 453H742M774 453V421" stroke="#fff8e7" stroke-width="2" fill="none"/></svg><span class="scene-stamp">HÌNH MINH HỌA · KHÔNG PHẢI CAMERA</span><span class="scene-label">Kết nối máy chủ để xem ảnh thật từ thiết bị.</span></div>`;
let session = null;
// Phiên trong tab; nếu người nhà chọn “Ghi nhớ”, giữ trong localStorage để mở từ thông báo/app.
try { session = JSON.parse(sessionStorage.getItem('donghanh-session') || localStorage.getItem('donghanh-session')); } catch {}
let demo = !session, data = null, selected = null, filter = 'all', busy = false, failed = false, page = 'overview';
let stream = null, gps = null, phoneReady = false, notify = false, knownSos = new Set(), firstLoad = true, toastTimer;
const blobs = new Map();
const now = Date.now()/1000;
function demoData(){return {mode:'demo',demoMessages:[{id:'demo-drop-1:drop',event_id:'demo-drop-1',stage:'drop',level:'warn',title:'Gậy có thể bị rơi',body:'Tin minh họa. Khi kết nối thật, SOS và cảnh báo rơi gậy xuất hiện ở đây và được đẩy tới điện thoại.',created_at:now-600,read_at:null,push_state:'no_device'}],camera_source:'phone',server_time:now,devices:[{id:'test',last_seen:now,state:{distance_cm:86,sensor_valid:true,periodic_enabled:true,simulated:true,camera_ready:false}},{id:'phone',last_seen:now,state:{camera_ready:true}}],settings:{periodic_enabled:true,interval_s:60},location:null,events:[{id:'demo-periodic-1',kind:'periodic',source:'phone',received_at:now-35,captured_at:now-36,image_received_at:now-35,has_image:true,image_status:'ready',demo:true,ai:{status:'not_configured',risk:'unknown',summary:'Chưa cài mô hình. Hình minh họa không được phân tích.'}},{id:'demo-sos-1',kind:'sos',source:'test',received_at:now-980,captured_at:null,has_image:false,image_status:'camera_unavailable',acknowledged_at:now-900,demo:true,ai:{status:'not_requested',risk:'unknown'},details:'Sự kiện minh họa đã được người thân xem.'},{id:'demo-drop-1',kind:'drop',source:'test',received_at:now-1500,has_image:false,image_status:'not_requested',demo:true,ai:{status:'not_requested',risk:'unknown'},details:'Nút bấm giả lập rơi gậy.'}]};}
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500);}
async function api(path, options={}){
  if(!session) throw Error('Chưa kết nối máy chủ.');
  const response=await fetch(session.url+path,{...options,signal:AbortSignal.timeout(10000),headers:{Authorization:'Bearer '+session.token,...(options.body&&typeof options.body==='string'?{'Content-Type':'application/json'}:{}),...options.headers}});
  if(!response.ok){let msg=`HTTP ${response.status}`;try{const x=await response.json();msg=typeof x.detail==='string'?x.detail:msg;}catch{}throw Error(msg);}
  return response.headers.get('content-type')?.includes('image/')?response.blob():response.json();
}
const post=(path, body={})=>api(path,{method:'POST',body:JSON.stringify(body)});
function showPage(id){if(!$(id))return;page=id;document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.id===id));document.querySelectorAll('.nav').forEach(el=>el.classList.toggle('active',el.dataset.page===id));$('pageName').textContent=document.querySelector(`[data-page="${id}"]`)?.textContent.trim()||id;history.replaceState(null,'','#'+id);if(id==='history')renderHistory();}
document.querySelectorAll('[data-page]').forEach(el=>el.onclick=()=>showPage(el.dataset.page));
document.querySelectorAll('[data-goto]').forEach(el=>el.onclick=()=>showPage(el.dataset.goto));
function statusBadge(event){return event.kind==='sos'?'danger':event.kind==='drop'?'warn':'neutral';}
function aiName(result){return ({not_configured:'Chưa cấu hình',pending:'Đang chờ',waiting:'Chờ ảnh',ready:'Đã phân tích',error:'Lỗi phân tích',not_requested:'Không yêu cầu'})[result?.status]||'Chưa xác định';}
async function imageUrl(event){
  if(event.demo||!event.has_image)return null;
  if(blobs.has(event.id))return blobs.get(event.id);
  const blob=await api(`/api/v1/events/${encodeURIComponent(event.id)}/image`);
  const url=URL.createObjectURL(blob);blobs.set(event.id,url);return url;
}
function renderImage(container,event){
  container.innerHTML=event?.demo&&event?.has_image?scene():`<div class="empty-image"><span>▧</span>${event?.has_image?'Đang tải ảnh…':'Chưa có ảnh cho cập nhật này.'}</div>`;
  container.dataset.event=event?.id||'';
  if(event?.has_image&&!event.demo)imageUrl(event).then(url=>{if(container.dataset.event===event.id){container.innerHTML='';const img=new Image();img.src=url;img.alt='Ảnh từ '+(sources[event.source]||event.source);container.append(img);}}).catch(()=>{container.innerHTML='<div class="empty-image">Không tải được ảnh. Thử làm mới.</div>';});
}
function render(){
  if(!data)return;
  const isLive=!demo&&!failed;
  $('modeBanner').className='mode-banner'+(demo?'':failed?' error-mode':' live');
  $('modeBanner').innerHTML=demo?`BẢN TRẢI NGHIỆM <span>Dữ liệu minh họa · Chưa kết nối thiết bị</span><button id="demoSos">Thử tình huống SOS ↗</button>`:failed?'MẤT KẾT NỐI MÁY CHỦ <span>Dữ liệu bên dưới là dữ liệu cũ. Đang thử kết nối lại.</span>':`DỮ LIỆU THẬT <span>${({test:'Cấu hình thử 1 ESP32 · Ảnh từ điện thoại',duo:'ESP32 + ESP32-CAM · Ảnh từ ESP32-CAM',final:'Cấu hình 2 bo đeo · Ảnh từ ESP32-CAM ngực'})[data.mode]||data.mode}</span>`;
  if($('demoSos'))$('demoSos').onclick=simulateSos;
  $('syncBadge').textContent=demo?'Dữ liệu minh họa':failed?'Máy chủ mất kết nối':'Đã đồng bộ';
  $('syncBadge').className='badge '+(failed?'danger':demo?'neutral':'good');
  const online=data.devices.filter(d=>(demo||age(d.last_seen)<20)&&isLive);
  $('deviceCount').textContent=demo?'2 / 2':`${online.length} / ${data.devices.length}`;
  $('deviceHint').textContent=demo?'Hai nguồn giả lập':failed?'Không xác định trạng thái hiện tại':'Có tín hiệu trong 20 giây gần nhất';
  const device=data.devices.find(d=>d.id===(data.mode==='final'?'chest':'test'));// duo/test: ESP32 thử giữ cảm biến và nút riêng tư
  const fresh=device&&(demo||isLive&&age(device.last_seen)<20);
  const valid=fresh&&device.state.sensor_valid&&device.state.distance_cm!=null;
  $('distance').innerHTML=valid?`${Math.round(device.state.distance_cm)} <em>cm</em>`:'— <em>cm</em>';
  $('distanceHint').textContent=!valid?'Không xác định · kiểm tra cảm biến':device.state.simulated?'Khoảng cách đang được giả lập':device.state.distance_cm<40?'Vật cản rất gần':device.state.distance_cm<120?'Trong ngưỡng cảnh báo':'Ngoài ngưỡng cảnh báo đã đặt';
  const periodic=fresh&&device.state.periodic_enabled&&data.settings.periodic_enabled;
  $('periodicState').textContent=!fresh?'Chưa rõ':periodic?'Đang bật':'Đang tắt';
  $('periodicHint').textContent=periodic?`Mỗi ${data.settings.interval_s} giây · cần camera sẵn sàng`:'Nút riêng tư trên thiết bị có quyền ưu tiên';
  const sos=data.events.filter(e=>e.kind==='sos'&&!e.acknowledged_at);
  $('sosCount').textContent=sos.length;
  $('sosBanner').hidden=!sos.length;
  if(sos.length){$('sosBanner').innerHTML=`<div><strong>Có yêu cầu hỗ trợ chưa được xem</strong><p>${esc(sources[sos[0].source]||sos[0].source)} · Máy chủ nhận ${esc(timeText(sos[0].received_at))}</p></div><button class="button danger" id="openSos">Xem SOS ngay →</button>`;$('openSos').onclick=()=>openEvent(sos[0]);}
  const newest=data.events.find(e=>e.has_image)||data.events.find(e=>['sos','periodic','manual'].includes(e.kind));
  selected=newest||null;
  const heroKey=(newest?.id||'none')+':'+(newest?.has_image||false);
  if($('heroImage').dataset.key!==heroKey){renderImage($('heroImage'),newest);$('heroImage').dataset.key=heroKey;}
  $('imageSub').textContent=newest?`${sources[newest.source]||newest.source} · ${ageText(newest.received_at)}`:'Đang chờ camera gửi ảnh';
  $('imageType').textContent=newest?(names[newest.kind]||newest.kind):'Chưa có ảnh';
  $('imageType').className='badge '+(newest?statusBadge(newest):'neutral');
  $('imageTime').textContent=newest?.captured_at?'Chụp lúc '+timeText(newest.captured_at):newest?'Chưa có giờ chụp · Nhận '+timeText(newest.received_at):'Chưa có thời gian chụp';
  $('aiStatus').textContent=aiName(newest?.ai);
  $('aiSummary').textContent=newest?.ai?.summary||'Chưa có ảnh hoặc chưa có kết quả phân tích.';
  const pos=data.location;
  $('locationBadge').textContent=pos?(age(pos.captured_at)>60?'Vị trí cũ':'Có vị trí'):'Chưa có GPS';
  $('locationBadge').className='badge '+(pos&&age(pos.captured_at)>60?'warn':'neutral');
  $('locationText').textContent=pos?`${pos.latitude.toFixed(5)}, ${pos.longitude.toFixed(5)}`:'Đang chờ chia sẻ vị trí';
  $('locationInfo').textContent=pos?`Sai số khoảng ${Math.round(pos.accuracy)} m · ${ageText(pos.captured_at)}`:'Hình nền chỉ minh họa, không phải bản đồ tọa độ.';
  $('mapLink').hidden=!pos;if(pos)$('mapLink').href=`https://www.google.com/maps/search/?api=1&query=${pos.latitude},${pos.longitude}`;
  $('recentFeed').innerHTML=data.events.length?data.events.slice(0,5).map(e=>`<div class="feed-item" tabindex="0" role="button" data-event="${esc(e.id)}"><span class="event-dot ${esc(e.kind)}">${e.kind==='sos'?'!':e.kind==='drop'?'⌁':'▧'}</span><div><h3>${esc(names[e.kind]||e.kind)}</h3><p>${esc(sources[e.source]||e.source)}${e.demo?' · Minh họa':''} · ${e.has_image?'Có ảnh':imageStatus(e.image_status)}</p></div><time>${esc(timeText(e.received_at))}</time><span class="arrow">↗</span></div>`).join(''):'<div class="empty-state">Chưa có sự kiện. Bấm SOS trên thiết bị để thử kết nối.</div>';
  bindEvents($('recentFeed'));
  $('deviceList').innerHTML=data.devices.map(d=>`<div class="device-item"><span>${esc(sources[d.id]||d.id)}</span><span class="badge ${isLive&&age(d.last_seen)<20?'good':'neutral'}">${demo?'Giả lập':isLive&&age(d.last_seen)<20?'Có tín hiệu':'Mất tín hiệu'}</span></div>`).join('')||'<p>Chưa có thiết bị.</p>';
  $('connectionInfo').textContent=demo?'Đang xem dữ liệu minh họa.':`${session?.url||location.origin} · ${session?.role||''}`;
  if(firstLoad){$('periodicToggle').checked=data.settings.periodic_enabled;$('interval').value=data.settings.interval_s;}
  // Cùng tag với thông báo đẩy (`<event>:sos`) nên không hiện trùng khi máy đã đăng ký push.
  if(notify&&!firstLoad&&!demo&&'Notification'in window&&Notification.permission==='granted')for(const e of sos)if(!knownSos.has(e.id))new Notification('SOS: người thân cần hỗ trợ',{body:`${sources[e.source]||e.source} cần hỗ trợ. Mở web để xem chi tiết.`,tag:e.id+':sos'});
  updateAlarm(sos);
  if(voiceEnabled && !firstLoad){
    if(newest?.has_image && newest?.ai?.status === 'ready' && newest?.ai?.summary){
      const aiKey = newest.id + ':' + newest.ai.summary;
      if(lastAnnouncedAiKey !== aiKey){
        lastAnnouncedAiKey = aiKey;
        speakText('Kết quả nhận diện AI: ' + newest.ai.summary);
      }
    }
    if(isLive && valid && device.state.distance_cm < 40 && !device.state.simulated){
      const tNow = Date.now()/1000;
      if(tNow - lastDistanceAlertTime > 8){
        lastDistanceAlertTime = tNow;
        speakText('Cảnh báo: Vật cản phía trước rất gần, khoảng ' + Math.round(device.state.distance_cm) + ' centimét.');
      }
    }
    if(sos.length && !lastSosSpoken){
      lastSosSpoken = true;
      speakText('Khẩn cấp: Có tín hiệu SOS cần trợ giúp!');
    } else if(!sos.length){
      lastSosSpoken = false;
    }
  }
  $('aiInfo').textContent=demo?'Minh họa':({none:'Chưa bật AI',segformer:'SegFormer-B0 trên máy chủ',gemini:'Gemini'})[data.ai_provider]||'Chưa rõ';
  knownSos=new Set(sos.map(e=>e.id));firstLoad=false;
  if(page==='history')renderHistory();
  for(const [id,url] of blobs)if(!data.events.some(e=>e.id===id)){URL.revokeObjectURL(url);blobs.delete(id);}
}
function renderMessages(){
  $('msgBadge').hidden=!unreadMessages;$('msgBadge').textContent=unreadMessages;
  $('messageList').innerHTML=messages.length?messages.map(m=>`<div class="feed-item msg-item${m.read_at?'':' unread'}" tabindex="0" role="button" data-msg="${esc(m.id)}" data-event="${esc(m.event_id)}"><span class="event-dot ${m.level==='sos'?'sos':'warn'}">${m.level==='sos'?'!':'⌁'}</span><div><h3>${esc(m.title)}</h3><p>${esc(m.body)}</p></div><time>${esc(timeText(m.created_at))}</time></div>`).join(''):'<div class="empty-state">Chưa có tin nhắn. SOS và cảnh báo rơi gậy sẽ xuất hiện ở đây.</div>';
  $('messageList').querySelectorAll('[data-msg]').forEach(el=>{const open=async()=>{const m=messages.find(x=>x.id===el.dataset.msg);if(m&&!m.read_at){m.read_at=Date.now()/1000;unreadMessages=Math.max(0,unreadMessages-1);if(!demo)post('/api/v1/messages/read',{ids:[m.id]}).catch(()=>{});renderMessages();}openEvent(data?.events.find(e=>e.id===el.dataset.event));};el.onclick=open;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}};});
}
// ---- PHÁT ÂM THANH GIỌNG NÓI TIẾNG VIỆT (Web Speech API) ----
let voiceEnabled = localStorage.getItem('donghanh-voice') !== 'false';
let lastSpokenText = '', lastSpokenTime = 0;
let lastAnnouncedAiKey = '', lastDistanceAlertTime = 0, lastSosSpoken = false;

function updateVoiceUI(){
  if(voiceToggle){
    voiceToggle.textContent = voiceEnabled ? '🔊 Giọng đọc: Bật' : '🔇 Giọng đọc: Tắt';
    voiceToggle.className = 'button small ' + (voiceEnabled ? 'secondary' : '');
  }
}

function speakText(text, force=false){
  if(!text || (!voiceEnabled && !force) || !('speechSynthesis' in window)) return;
  const now = Date.now();
  if(!force && text === lastSpokenText && (now - lastSpokenTime < 10000)) return;
  try{
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'vi-VN';
    u.rate = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const vi = voices.find(v => v.lang && (v.lang.includes('vi') || v.lang.includes('VN')));
    if(vi) u.voice = vi;
    window.speechSynthesis.speak(u);
    lastSpokenText = text;
    lastSpokenTime = now;
  }catch(e){}
}

function toggleVoice(){
  voiceEnabled = !voiceEnabled;
  localStorage.setItem('donghanh-voice', voiceEnabled);
  updateVoiceUI();
  if(voiceEnabled) speakText('Đã bật giọng đọc cảnh báo.', true);
  else{ window.speechSynthesis?.cancel(); toast('Đã tắt giọng đọc cảnh báo.'); }
}

// Âm báo SOS khi trang đang mở. Trình duyệt chỉ cho phát âm sau lần chạm/nhấn đầu tiên trên trang.
function unlockAudio(){if(!audio&&(window.AudioContext||window.webkitAudioContext)){try{audio=new(window.AudioContext||window.webkitAudioContext)();}catch{}}audio?.resume?.();}
['pointerdown','keydown'].forEach(t=>document.addEventListener(t,unlockAudio,{once:false,passive:true}));
function beep(){if(!audio||audio.state!=='running')return;const t=audio.currentTime;for(let i=0;i<3;i++){const o=audio.createOscillator(),g=audio.createGain();o.frequency.value=880;g.gain.value=.25;o.connect(g).connect(audio.destination);o.start(t+i*.35);o.stop(t+i*.35+.2);}}
function updateAlarm(sos){
  const active=!demo&&sos.some(e=>!mutedSos.has(e.id));
  $('muteAlarm').hidden=!active;
  if(active&&!alarmTimer){beep();alarmTimer=setInterval(beep,2500);}
  if(!active&&alarmTimer){clearInterval(alarmTimer);alarmTimer=null;}
}
$('muteAlarm').onclick=()=>{for(const e of data?.events||[])if(e.kind==='sos'&&!e.acknowledged_at)mutedSos.add(e.id);updateAlarm([]);toast('Đã tắt âm báo cho các SOS hiện có. SOS mới sẽ kêu lại.');};
$('readAll').onclick=async()=>{try{if(!demo)await post('/api/v1/messages/read',{});messages.forEach(m=>m.read_at??=Date.now()/1000);unreadMessages=0;renderMessages();}catch(e){toast(e.message);}};
async function loadMessages(){if(demo){messages=data?.demoMessages||[];unreadMessages=messages.filter(m=>!m.read_at).length;}else{const box=await api('/api/v1/messages');messages=box.messages;unreadMessages=box.unread;}renderMessages();}
// ---- Thông báo đẩy (Web Push) và cài như ứng dụng ----
const pushSupported=()=>window.isSecureContext&&'serviceWorker'in navigator&&'PushManager'in window&&'Notification'in window;
function keyBytes(b64){const pad='='.repeat((4-b64.length%4)%4);const raw=atob((b64+pad).replace(/-/g,'+').replace(/_/g,'/'));return Uint8Array.from(raw,c=>c.charCodeAt(0));}
async function currentSubscription(){if(!pushSupported())return null;const reg=await navigator.serviceWorker.getRegistration();return reg?reg.pushManager.getSubscription():null;}
async function refreshPushStatus(){
  let text,on=false;
  if(demo)text='Kết nối bằng khóa người nhà để bật thông báo.';
  else if(!window.isSecureContext)text='Đang mở bằng HTTP: chỉ báo khi trang đang mở. Mở địa chỉ HTTPS để nhận thông báo khi đóng trình duyệt.';
  else if(!pushSupported())text='Trình duyệt này không hỗ trợ thông báo đẩy. iPhone: thêm vào màn hình chính rồi mở từ đó.';
  else{on=!!(await currentSubscription().catch(()=>null))&&Notification.permission==='granted';text=on?'Máy này đang nhận thông báo đẩy, kể cả khi đóng trình duyệt.':Notification.permission==='denied'?'Thông báo bị chặn trong cài đặt trình duyệt.':'Chưa bật thông báo trên máy này.';}
  $('pushStatus').textContent=text;$('pushOff').hidden=!on;$('pushBtn').hidden=on;notify=notify||on;
}
async function enablePush(){
  try{
    if(demo)return toast('Minh họa: kết nối bằng khóa người nhà để bật thông báo.');
    if(session?.role!=='caregiver')throw Error('Cần kết nối bằng CAREGIVER_TOKEN.');
    if(!('Notification'in window))throw Error('Trình duyệt không hỗ trợ thông báo.');
    if(await Notification.requestPermission()!=='granted')throw Error('Chưa được cấp quyền thông báo.');
    notify=true;
    if(!pushSupported()){await refreshPushStatus();return toast('Đã bật thông báo khi trang đang mở. Cần HTTPS để nhận khi đóng trình duyệt.');}
    const cfg=await api('/api/v1/push/config');if(!cfg.enabled)throw Error('Máy chủ chưa cài pywebpush; chỉ báo khi trang đang mở.');
    const reg=await navigator.serviceWorker.register('sw.js');await navigator.serviceWorker.ready;
    let sub=await reg.pushManager.getSubscription();const key=keyBytes(cfg.public_key);
    // Khóa máy chủ đổi (xóa thư mục data) thì đăng ký cũ không còn dùng được.
    if(sub&&sub.options?.applicationServerKey&&new Uint8Array(sub.options.applicationServerKey).join()!==key.join()){await sub.unsubscribe();sub=null;}
    sub??=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key});
    await post('/api/v1/push/subscriptions',sub.toJSON());
    await refreshPushStatus();toast('Đã bật thông báo đẩy trên máy này.');
  }catch(e){toast(e.message);await refreshPushStatus();}
}
async function disablePush(){try{const sub=await currentSubscription();if(sub){await post('/api/v1/push/unsubscribe',{endpoint:sub.endpoint}).catch(()=>{});await sub.unsubscribe();}toast('Đã tắt thông báo đẩy trên máy này.');}catch(e){toast(e.message);}await refreshPushStatus();}
$('pushBtn').onclick=enablePush;$('pushOff').onclick=disablePush;
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('installBtn').hidden=false;});
$('installBtn').onclick=async()=>{if(!installPrompt)return;installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('installBtn').hidden=true;};
if(pushSupported())navigator.serviceWorker.register('sw.js').catch(()=>{});
window.addEventListener('hashchange',()=>showPage(location.hash.slice(1)||'overview'));
function imageStatus(status){return ({pending:'Đang chờ ảnh',missing:'Hết hạn chờ ảnh',camera_unavailable:'Camera chưa sẵn sàng',privacy_off:'Ảnh định kỳ đã tắt',not_requested:'Không yêu cầu ảnh',failed:'Gửi ảnh thất bại',uploaded:'Đã nhận ảnh',analyzing:'Đang phân tích',ready:'Có ảnh'})[status]||'Chưa có ảnh';}
function bindEvents(root){root.querySelectorAll('[data-event]').forEach(el=>{const handler=()=>openEvent(data.events.find(e=>e.id===el.dataset.event));el.onclick=handler;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();handler();}};});}
function renderHistory(){
  if(!data)return;
  const search=$('search').value.toLowerCase();
  const list=data.events.filter(e=>(filter==='all'||e.kind===filter)&&[e.details,sources[e.source],names[e.kind],e.id].join(' ').toLowerCase().includes(search));
  const signature=JSON.stringify(list.map(e=>[e.id,e.has_image,e.image_status,e.ai?.status]))+filter+search;
  if($('historyGrid').dataset.signature===signature)return;
  $('historyGrid').dataset.signature=signature;
  $('historyGrid').innerHTML=list.length?list.map(e=>`<article class="panel history-card" tabindex="0" role="button" data-event="${esc(e.id)}"><div class="thumb" data-thumb="${esc(e.id)}"></div><div class="card-copy"><span class="badge ${statusBadge(e)}">${esc(names[e.kind]||e.kind)}</span><h3>${esc(sources[e.source]||e.source)}</h3><p>${e.demo?'Minh họa · ':''}${esc(imageStatus(e.image_status))}</p><time>Nhận ${esc(timeText(e.received_at))}</time></div></article>`).join(''):'<div class="empty-state">Không có cập nhật phù hợp bộ lọc.</div>';
  list.forEach(e=>renderImage($('historyGrid').querySelector(`[data-thumb="${e.id}"]`),e));bindEvents($('historyGrid'));
}
function contextLines(event){
  if(event.kind!=='sos')return '';
  const ctx=event.context||{},pos=ctx.location;
  const where=pos?`<a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(pos.latitude+','+pos.longitude)}" target="_blank" rel="noopener noreferrer">${pos.latitude.toFixed(5)}, ${pos.longitude.toFixed(5)}</a> · ±${Math.round(pos.accuracy)} m`:'Không có vị trí đủ mới tại thời điểm SOS';
  const notes=(event.notifications||[]).map(n=>`${stageNames[n.stage]||n.stage}: ${noticeNames[n.state]||n.state}${n.attempts?` (thử ${n.attempts} lần)`:''}${n.read_at?' · đã đọc':''}`).join(' · ');
  return `<div class="detail-line"><span>Vị trí lúc SOS</span><span>${where}</span></div><div class="detail-line"><span>Khoảng cách lúc SOS</span><span>${ctx.distance_cm!=null?Math.round(ctx.distance_cm)+' cm':'Không có phép đo hợp lệ'}</span></div>${notes?`<div class="detail-line"><span>Tin nhắn</span><span>${esc(notes)}</span></div>`:''}`;
}
async function openEvent(event){
  if(!event)return toast('Chưa có cập nhật để xem.');
  const el=$('eventContent');
  el.innerHTML=`<div id="detailImage" style="position:relative;min-height:140px"></div><div class="detail-line"><span>Loại / nguồn</span><b>${esc(names[event.kind])} · ${esc(sources[event.source])}</b></div><div class="detail-line"><span>Lúc xảy ra</span><span>${event.clock_synced?esc(timeText(event.occurred_at)):'Thiết bị chưa đồng bộ giờ / không cung cấp'}</span></div><div class="detail-line"><span>Máy chủ nhận sự kiện</span><span>${esc(timeText(event.received_at))}</span></div><div class="detail-line"><span>Lúc chụp ảnh</span><span>${event.captured_at?esc(timeText(event.captured_at)):'Không có giờ chụp đã đồng bộ'}</span></div><div class="detail-line"><span>Máy chủ nhận ảnh</span><span>${esc(timeText(event.image_received_at))}</span></div><div class="detail-line"><span>Trạng thái ảnh</span><span>${esc(imageStatus(event.image_status))}</span></div><p>${esc(event.details||'')}</p>${contextLines(event)}<div class="detail-ai"><strong>✦ AI · ${esc(aiName(event.ai))}${event.ai?.provider?' · '+esc(event.ai.provider):''}</strong><p>${esc(event.ai?.summary||'Chưa có kết quả nhận diện.')}</p>${event.ai?.observed_objects?.length?`<div class="detail-line"><span>Vật thể AI thấy</span><span>${esc(event.ai.observed_objects.join(', '))}</span></div>`:''}${(event.ai?.regions||[]).slice(0,6).map(r=>`<div class="detail-line"><span>${esc(r.label)}</span><span>${Math.round(r.fraction*100)}% vùng xét · điểm ${Math.round(r.confidence*100)}%</span></div>`).join('')}<p>Điểm mô hình không phải xác suất an toàn. Không kết luận được phép sang đường.</p></div>${event.kind==='sos'?`<button class="button full" id="ackSos" ${event.acknowledged_at?'disabled':''}>${event.acknowledged_at?'Người thân đã xem':'Đánh dấu: tôi đã xem SOS'}</button><p class="fineprint">Đã xem không có nghĩa người dùng đã được hỗ trợ. Còi dừng bằng thao tác tại thiết bị.</p>`:''}`;
  renderImage($('detailImage'),event);
  if(!$('eventDialog').open)$('eventDialog').showModal();
  if($('ackSos'))$('ackSos').onclick=async()=>{try{if(demo)event.acknowledged_at=Date.now()/1000;else await post(`/api/v1/events/${event.id}/ack`);$('eventDialog').close();await refresh();toast('Đã đánh dấu người thân xem SOS.');}catch(e){toast(e.message);}};
}
function simulateSos(){if(!demo)return;data.events.unshift({id:'demo-'+Date.now(),kind:'sos',source:'test',received_at:Date.now()/1000,has_image:false,image_status:'camera_unavailable',demo:true,ai:{status:'waiting',risk:'unknown'},details:'Tình huống mô phỏng. Chưa gửi thông tin đến thiết bị hay người khác.'});render();toast('Đã tạo một SOS minh họa. Bấm “Xem SOS ngay” để thử xác nhận.');}
async function refresh(){
  if(busy)return;busy=true;
  try{if(demo){data??=demoData();render();await loadMessages();}else if(session.role==='phone'){await pollPhone();}else{data=await api('/api/v1/dashboard');failed=false;render();if(data.unread_messages!==unreadMessages||page==='messages'||firstMessages){firstMessages=false;await loadMessages();}}}
  catch(e){failed=true;if(data)render();else{$('modeBanner').textContent='Không kết nối được: '+e.message;$('modeBanner').className='mode-banner error-mode';}}
  finally{busy=false;}
}
function openConnect(){$('apiUrl').value=session?.url||'';$('token').value='';$('loginError').textContent='';$('connectDialog').showModal();}
$('connectBtn').onclick=$('openConnection').onclick=openConnect;
$('closeConnect').onclick=()=>$('connectDialog').close();$('closeEvent').onclick=()=>$('eventDialog').close();
$('connectForm').onsubmit=async e=>{e.preventDefault();const old=session;try{const raw=$('apiUrl').value.trim();const url=raw?new URL(raw):null;if(url&&!['http:','https:'].includes(url.protocol))throw Error('Chỉ hỗ trợ HTTP/HTTPS.');if(url&&(url.username||url.password||url.search||url.hash||url.pathname!=='/'))throw Error('Chỉ nhập origin máy chủ, không kèm đường dẫn hoặc mật khẩu.');session={url:url?url.origin:'',token:$('token').value};const info=await api('/api/v1/session');if(!['phone','caregiver'].includes(info.role))throw Error('Web cần khóa caregiver hoặc phone; không dùng khóa thiết bị.');session.role=info.role;session.mode=info.mode;sessionStorage.setItem('donghanh-session',JSON.stringify(session));try{if($('remember').checked&&info.role==='caregiver')localStorage.setItem('donghanh-session',JSON.stringify(session));else localStorage.removeItem('donghanh-session');}catch{}firstMessages=true;mutedSos.clear();stopCamera();stopGps();demo=false;data=null;firstLoad=true;knownSos.clear();$('heroImage').dataset.key='';$('historyGrid').dataset.signature='';$('connectDialog').close();$('token').value='';if(info.role==='phone'){showPage('phone');$('modeBanner').className='mode-banner live';$('modeBanner').textContent=`ĐÃ KẾT NỐI · ĐIỆN THOẠI · ${info.mode==='test'?'Chế độ thử':'Chế độ hoàn thiện'}`;$('connectionInfo').textContent=(session.url||location.origin)+' · phone';}else showPage('overview');await refresh();refreshPushStatus();}catch(err){session=old;$('loginError').textContent=err.message;}};
function disconnect(){stopCamera();stopGps();session=null;sessionStorage.removeItem('donghanh-session');try{localStorage.removeItem('donghanh-session');}catch{}messages=[];unreadMessages=0;firstMessages=true;updateAlarm([]);refreshPushStatus();demo=true;failed=false;firstLoad=true;data=demoData();for(const url of blobs.values())URL.revokeObjectURL(url);blobs.clear();$('heroImage').dataset.key='';$('historyGrid').dataset.signature='';showPage('overview');render();}
$('disconnect').onclick=disconnect;$('useDemo').onclick=()=>{$('connectDialog').close();disconnect();};
$('imageDetail').onclick=()=>openEvent(selected);$('refresh').onclick=refresh;
$('filters').onclick=e=>{if(e.target.dataset.filter){filter=e.target.dataset.filter;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x.dataset.filter===filter));renderHistory();}};$('search').oninput=renderHistory;
async function findCane(){try{if(demo)return toast('Minh họa: khi kết nối, gậy sẽ nhận lệnh phát còi tối đa 30 giây.');await post('/api/v1/find-cane');toast('Đã xếp lệnh tìm gậy, có hiệu lực 20 giây. Gậy cần đang kết nối.');}catch(e){toast(e.message);}}
$('findCane').onclick=$('phoneFind').onclick=findCane;
async function stopAlarm(){try{if(demo)return toast('Minh họa: tắt còi.');await post('/api/v1/stop-alarm');toast('Đã gửi lệnh tắt còi gậy.');}catch(e){toast(e.message);}}
if($('stopAlarm'))$('stopAlarm').onclick=stopAlarm;
async function captureNow(){try{if(demo)return toast('Minh họa: khi kết nối, camera sẽ chụp nếu người đeo đang bật ảnh.');const r=await post('/api/v1/capture');toast(r.duplicate?'Camera đang có một yêu cầu chụp; chờ ảnh đó trước.':'Đã gửi yêu cầu chụp. Ảnh sẽ xuất hiện khi camera gửi về.');await refresh();}catch(e){toast(e.message);}}
$('captureNow').onclick=captureNow;
$('saveSettings').onclick=async()=>{try{const value={periodic_enabled:$('periodicToggle').checked,interval_s:Number($('interval').value)};if(demo)data.settings=value;else await api('/api/v1/settings',{method:'PUT',body:JSON.stringify(value)});await refresh();toast(demo?'Đã thay đổi cài đặt minh họa.':'Đã lưu. Công tắc riêng tư trên thiết bị vẫn có quyền ưu tiên.');}catch(e){toast(e.message);}};
$('notifyBtn').onclick=enablePush;
function needPhone(){if(demo||session?.role!=='phone')throw Error('Kết nối bằng PHONE_TOKEN trước khi dùng điện thoại.');}
function stopCamera(){stream?.getTracks().forEach(t=>t.stop());stream=null;phoneReady=false;$('phoneVideo').srcObject=null;$('cameraStatus').textContent='Camera đang tắt.';}
function stopGps(){if(gps!==null)navigator.geolocation.clearWatch(gps);gps=null;$('gpsStatus').textContent='Đã dừng chia sẻ vị trí. Vị trí cũ vẫn có dấu thời gian trên web.';}
$('startCamera').onclick=async()=>{try{needPhone();if(session.mode!=='test')throw Error('Cấu hình này lấy ảnh từ ESP32-CAM. Điện thoại chỉ cần GPS.');if(!window.isSecureContext)throw Error('Camera cần HTTPS. Mở địa chỉ HTTPS của máy chủ.');stopCamera();stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:640},height:{ideal:480}},audio:false});$('phoneVideo').srcObject=stream;await $('phoneVideo').play();phoneReady=true;$('cameraStatus').textContent='Đang sẵn sàng chụp khi có lệnh. Giữ trang ở phía trước.';}catch(e){toast(e.message);}};
$('stopCamera').onclick=stopCamera;$('stopGps').onclick=stopGps;
$('startGps').onclick=()=>{try{needPhone();if(!window.isSecureContext)throw Error('GPS cần HTTPS.');if(!navigator.geolocation)throw Error('Trình duyệt không hỗ trợ GPS.');stopGps();gps=navigator.geolocation.watchPosition(async p=>{try{await post('/api/v1/location',{latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,captured_at:p.timestamp/1000});$('gpsStatus').textContent=`Đã gửi ${new Date().toLocaleTimeString('vi-VN')} · sai số khoảng ${Math.round(p.coords.accuracy)} m.`;}catch(e){$('gpsStatus').textContent='Chưa gửi được vị trí: '+e.message;}},e=>{$('gpsStatus').textContent='Không lấy được GPS: '+e.message;},{enableHighAccuracy:true,maximumAge:5000,timeout:15000});$('gpsStatus').textContent='Đang xin quyền và tìm vị trí…';}catch(e){toast(e.message);}};
$('phoneSos').onclick=async()=>{try{needPhone();await post('/api/v1/events',{event_id:crypto.randomUUID(),kind:'sos',occurred_at:Date.now()/1000,clock_synced:true,message:'Người dùng bấm SOS trên điện thoại.'});toast('Máy chủ đã nhận SOS. Việc nhận ảnh còn phụ thuộc camera.');}catch(e){toast('Chưa gửi được SOS: '+e.message);}};
async function pollPhone(){
  if(!session||session.role!=='phone')return;
  await post('/api/v1/state',{camera_ready:phoneReady,periodic_enabled:true});
  const result=await api('/api/v1/commands');
  for(const cmd of result.commands){
    if(cmd.kind!=='capture')continue;
    if(!phoneReady||!stream||document.visibilityState!=='visible') {await post(`/api/v1/commands/${cmd.id}/ack`,{result:'camera_unavailable'});continue;}
    try{
      const video=$('phoneVideo');if(!video.videoWidth)throw Error('Camera chưa có khung hình.');
      const canvas=document.createElement('canvas');canvas.width=640;canvas.height=Math.round(video.videoHeight*640/video.videoWidth);
      const captured=Date.now()/1000;canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.8));
      if(!blob)throw Error('Không chụp được ảnh.');
      await api(`/api/v1/events/${cmd.event_id}/image`,{method:'POST',headers:{'Content-Type':'image/jpeg','X-Captured-At':String(captured)},body:blob});
      await post(`/api/v1/commands/${cmd.id}/ack`,{result:'done'});
      $('cameraStatus').textContent=`Đã gửi ảnh ${cmd.reason==='sos'?'SOS':'định kỳ'} lúc ${new Date(captured*1000).toLocaleTimeString('vi-VN')}.`;
    }catch(e){$('cameraStatus').textContent='Gửi ảnh chưa thành công: '+e.message;/* không ack: máy chủ có thể giao lại đến hết TTL */}
  }
}
document.addEventListener('visibilitychange',()=>{if(document.hidden&&stream){stopCamera();$('cameraStatus').textContent='Đã tắt camera khi rời trang. Bấm bật lại để tiếp tục.';}});
window.addEventListener('beforeunload',()=>{stopCamera();stopGps();});
$('clock').textContent=new Date().toLocaleDateString('vi-VN',{day:'2-digit',month:'long',year:'numeric'});
if(session?.role==='phone'){showPage('phone');$('modeBanner').textContent='ĐÃ KẾT NỐI BẰNG KHÓA ĐIỆN THOẠI';}else showPage(location.hash.slice(1)||'overview');
refresh().then(refreshPushStatus);setInterval(refresh,2500);

if(voiceToggle) voiceToggle.onclick = toggleVoice;
if(speakAiBtn) speakAiBtn.onclick = () => {
  const s = aiSummary?.textContent?.trim();
  if(s && !s.includes('Chưa có ảnh') && !s.includes('Chưa cài mô hình')) speakText('Kết quả nhận diện AI: ' + s, true);
  else speakText('Hiện chưa có kết quả phân tích hình ảnh từ AI.', true);
};
if(phoneSpeakTest) phoneSpeakTest.onclick = () => speakText('Hệ thống Đồng Hành đã sẵn sàng phát âm thanh cảnh báo.', true);
updateVoiceUI();
