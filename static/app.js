/** @fileoverview Coordinate sessions, UI state, rendering, input, and campaign navigation. */
import {actionAudio} from './audio.js';
import {icon,button,hydrate} from './icons.js';
import {Minimap} from './minimap.js';
import {testWebGPU} from './webgpu-check.js';
import {LoadingGuide} from './loading-guide.js';
const $=id=>document.getElementById(id);
const itemOrder=['M4A1','HK416','M110','M249','M9','RPG-7','Frag grenade','M24 sniper','Smoke grenade','Demolition charge','Shotgun','Medikit'];
const photographs={'Shotgun':'shotgun.png','Medikit':'medikit.png','M24 sniper':'m24.png','Smoke grenade':'smoke-grenade.png','Demolition charge':'demolition-charge.png'};
let state,battlefield,minimap,selected='s0',mode='move',busy=false,pending=null,draft=null,editSlot=null,configTheme='random',configSize=30,configDifficulty='medium',configMission='rescue',configLighting='day';
let activeRequest=null,previewTask=null,goalKey=null,goalVersion=0,executedVersion=-1;
let screen='landing',campaignData=null,campaignProgress=null,campaignRun=false;
const bodyCount=document.createElement('span');bodyCount.id='body-count';$('seed').before(bodyCount);
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cookie=name=>document.cookie.split('; ').find(v=>v.startsWith(name+'='))?.slice(name.length+1);
const cookieJSON=name=>{try{return JSON.parse(decodeURIComponent(cookie(name)||''));}catch{return null;}};
const setCookie=(name,value)=>document.cookie=`${name}=${encodeURIComponent(JSON.stringify(value))}; Path=/; Max-Age=31536000; SameSite=Lax`;
const deleteCookie=name=>document.cookie=`${name}=; Path=/; Max-Age=0; SameSite=Lax`;
/** Show server full. */
function showServerFull(){closeDialogs();$('landing').hidden=true;$('campaign-screen').hidden=true;$('server-full').hidden=false;}
/**
 * Settle the landing card as soon as the independent capability probe finishes.
 *
 * @param {Object} result Serializable result returned by testWebGPU.
 */
function showGPUCheckStatus(result){
  const card=$('gpu-status'),info=result.info||{};
  document.documentElement.dataset.gpuTest=result.ok?'pass':'fail';
  card.className=`gpu-status ${result.ok?'available':'fallback'}`;
  if(result.ok){
    const name=[info.vendor,info.architecture||info.device].filter(Boolean).join(' ');
    $('gpu-status-title').textContent=result.fallback?'WEBGPU · FALLBACK ADAPTER READY':'WEBGPU · READY';
    $('gpu-status-detail').textContent=name||'Compute and canvas rendering passed';
  }else{
    $('gpu-status-title').textContent='WEBGL · DEFAULT';
    $('gpu-status-detail').textContent=result.reason||'WebGPU test did not pass';
  }
}
/**
 * Replace capability status with the renderer that actually started.
 *
 * This preserves a WebGL fallback reason when WebGPU was not selected.
 */
function showRendererStatus(){
  const card=$('gpu-status'),detail=$('gpu-status-detail'),webgpu=battlefield.renderer==='webgpu';
  document.documentElement.dataset.renderer=battlefield.renderer;
  card.className=`gpu-status ${webgpu?'available':'fallback'}`;
  $('render-label').textContent=`BABYLON.JS · ${battlefield.renderer.toUpperCase()}`;
  $('renderer-brand').textContent=`TACTICAL OPERATIONS / ${battlefield.renderer.toUpperCase()}`;
  if(webgpu){
    const info=battlefield.gpuInfo||{},name=[info.vendor,info.architecture||info.device].filter(Boolean).join(' ');
    $('gpu-status-title').textContent=info.fallback?'WEBGPU · FALLBACK ADAPTER':'WEBGPU · HARDWARE ACCELERATED';
    detail.textContent=name||'WebGPU adapter ready';
  }else{
    $('gpu-status-title').textContent='WEBGL · COMPATIBILITY MODE';detail.textContent=battlefield.fallbackReason||'WebGPU unavailable';
  }
}
/** @type {Promise<Object>} Shared gate for landing status and engine choice. */
const gpuTestPromise=testWebGPU({timeoutMs:8000})
  .catch(error=>({ok:false,stage:'unknown',reason:error?.message||String(error)}))
  .then(result=>{showGPUCheckStatus(result);return result});

/** Require consent and establish the current player session. */
async function ensureSession(){
  const current=await fetch('/api/session').then(r=>r.json());if(current.accepted)return true;
  const dialog=$('welcome'),form=$('welcome-form'),error=$('welcome-error');$('welcome-name').value=decodeURIComponent(cookie('turn4turn_name')||'');dialog.showModal();
  return new Promise(resolve=>form.onsubmit=async event=>{event.preventDefault();error.textContent='';
    try{const response=await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({consent:$('cookie-consent').checked,username:$('welcome-name').value})});const result=await response.json();if(!response.ok){if(result.full){dialog.close();showServerFull();resolve(false);return;}throw Error(result.error);}dialog.close();resolve(true);}
    catch(reason){error.textContent=reason.message;}
  });
}
/** Return local image or generated artwork markup for equipment. */
function itemArt(name){return photographs[name]?`<img class="item-photo" src="/assets/${photographs[name]}" alt="${name}">`:`<span class="item-art art-${itemOrder.indexOf(name)}" role="img" aria-label="${name}"></span>`;}
/** Return the currently selected squad member. */
function soldier(){return state?.units.find(u=>u.id===selected);}
/** Update the tactical status message. */
function message(text){$('message').textContent=text;}
/** Return a concise equipment-statistics label. */
function stats(name){const w=state.weapons[name];return `${w.kind==='medical'?w.heal+' HEAL':w.damage+' DMG'} · ${w.range} tiles · ${w.capacity} ${w.kind==='medical'?'uses':'loaded'}${w.automatic?' · AUTO':''}${w.kind==='sniper'?' · 2 AP':''}`;}
const previewImages=Object.fromEntries(itemOrder.map(name=>[name,'/assets/'+(photographs[name]||'items.png')]));
const loadingGuide=new LoadingGuide($('loading-feature'),itemArt,previewImages);
/** Keep loading visible above both the battlefield and preparation dialogs. */
function loading(label,value){
  const panel=$('mission-loading');
  if(!panel.open){panel.showModal();loadingGuide.start(state?.weapons);}
  $('loading-detail').textContent=label;
  if(value===undefined)$('loading-progress').removeAttribute('value');
  else $('loading-progress').value=value;
}
$('mission-loading').addEventListener('cancel',e=>e.preventDefault());
$('mission-loading').addEventListener('close',()=>{if(!$('mission-loading').open)loadingGuide.stop();});
const paintLoading=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
/** Track texture readiness, then wait for shaders and the complete scene. */
async function finishLoading(){
  const panel=$('mission-loading');panel.close();loading('Loading textures…',80);
  const update=()=>{
    const textures=battlefield.nativeScene.textures.filter(t=>!t.isRenderTarget),done=textures.filter(t=>t.isReady()).length;
    loading(done===textures.length?'Preparing scene…':`Loading textures · ${done} / ${textures.length}`,80+15*done/Math.max(1,textures.length));
  };
  update();const timer=setInterval(update,100);let timeout;
  try{
    await Promise.race([battlefield.nativeScene.whenReadyAsync(),new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('Mission resources took too long to load. Please reload to retry.')),120000);})]);
    loading('Ready',100);await paintLoading();
  }finally{clearInterval(timer);clearTimeout(timeout);}
}
/** Update busy. */
function setBusy(value){busy=value;document.body.classList.toggle('busy',value);$('preparation').inert=value;$('equipment').inert=value;}
/** Fetch heavy renderer code only when a mission is opened. */
let rendererTask;
const scripts=new Map();
function loadScript(url){
  if(!scripts.has(url))scripts.set(url,new Promise((resolve,reject)=>{
    const script=document.createElement('script');script.src=url;
    script.onload=resolve;script.onerror=()=>{scripts.delete(url);script.remove();reject(Error('Could not load game resources. Please try starting the mission again.'));};
    document.head.append(script);
  }));
  return scripts.get(url);
}
async function ensureBattlefield(){
  if(rendererTask)return rendererTask;
  rendererTask=(async()=>{
    loading('Loading game engine…',10);await paintLoading();
    await loadScript('/vendor/babylon.js');await loadScript('/vendor/babylonjs.loaders.min.js');
    const {Battlefield}=await import('./scene.js');
    loading('Starting renderer…',20);
    battlefield=await Battlefield.create($('map'),pick,hover,await gpuTestPromise);
    showRendererStatus();loading('Loading characters, vehicles, textures and sounds…',30);
    await battlefield.ready;
    minimap=new Minimap($('minimap'),p=>battlefield.focus(p));
    battlefield.controls.addEventListener('change',()=>{if(state){minimap.draw(state,selected,battlefield.controls.target);actionAudio.setListener(state,battlefield.camera);}});
  })();
  try{await rendererTask;}catch(error){
    battlefield?.engine.stopRenderLoop();battlefield?.nativeScene.dispose();battlefield?.engine.dispose();
    battlefield=null;minimap=null;rendererTask=null;throw error;
  }
}
/** Send one state request and reconcile its authoritative response. */
async function request(path,data){
  if(busy)return;activeRequest=path;setBusy(true);
  const missionLoad=(['/api/state','/api/new'].includes(path)||path==='/api/action'&&data?.action==='deploy');
  try{
    if(missionLoad){
      if(!await ensureSession())return;
      if(campaignRun)campaignSave();
      loading('Preparing mission…',5);await paintLoading();
    }
    const response=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');
    if(path==='/api/preview'){pending={...result,payload:data};message('Goal selected. Double-click the same point to execute; Escape cancels.');}
    else{
      pending=null;
      if(missionLoad){
        loading('Loading equipment previews…',7);loadingGuide.start(result.weapons);
        await loadingGuide.preload();loadingGuide.start(result.weapons);await paintLoading();
        // Artwork is ready before the engine, models, or audio compete for bandwidth.
        await Promise.all([ensureBattlefield(),actionAudio.prepare(result)]);
      }
      if(state&&path==='/api/action')try{await battlefield.animate(result.events,data?.action==='end_turn');}catch(error){console.warn('Animation failed; applying authoritative state.',error);}
      state=result;await actionAudio.prepare(state,missionLoad?(done,total)=>loading(`Loading sounds · ${done} / ${total}`,50+30*done/Math.max(1,total)):undefined);
      if(!state.units.some(u=>u.id===selected&&u.hp>0))selected=state.units.find(u=>u.team==='soldier'&&u.hp>0)?.id;
      message(state.status==='loadout'?'Choose the mission and equip your squad.':state.status==='active'?'Single-click a goal to preview; double-click it to execute.':'Mission complete. Prepare another operation.');
    }
    if(missionLoad&&state){render();await finishLoading();}
  }catch(error){pending=null;message(error.message);if($('loadout-error'))$('loadout-error').textContent=error.message;if(!battlefield){showLanding();$('startup-error').hidden=false;$('startup-error').textContent=error.message;}}
  finally{activeRequest=null;setBusy(false);if(state&&battlefield&&minimap)render();if(missionLoad)$('mission-loading').close();}
}
/** Submit an authoritative action for the selected unit. */
function act(action,extra={}){goalVersion++;goalKey=null;pending=null;return request('/api/action',{action,unit:selected,...extra});}
/** Request a non-mutating tactical action preview. */
function preview(action,extra={}){return request('/api/preview',{action,unit:selected,...extra});}
/** Change order mode and clear stale previews. */
function refreshMode(next,note=''){
  mode=next;goalVersion++;goalKey=null;pending=null;
  for(const [id,value] of [['move-mode','move'],['attack-mode','attack'],['face-mode','face']])$(id)?.classList.toggle('active',value===mode);
  battlefield.sync(state,selected,null,mode,null);battlefield.showPreview(null);
  minimap.draw(state,selected,battlefield.controls.target);
  message(note||'Single-click a goal to preview; double-click it to execute.');
}
/** Cancel the current tactical preview. */
function cancel(){refreshMode(mode,'Preview cancelled. Choose another point.');}
/** Select a squad member and focus the tactical camera. */
function select(id){if(busy)return;selected=id;goalVersion++;goalKey=null;pending=null;mode='move';battlefield.setView('auto');$('view-level').value='auto';render();battlefield.focus(soldier());}
/** Render all game UI from the current authoritative state. */
function render(){
  $('theme-label').textContent=`${state.scenery.label.toUpperCase()} / ${state.size} × ${state.size}`;
  document.querySelector('.mission h1').textContent=state.mission.label;
  document.querySelector('.mission p').textContent=state.mission.objective;
  $('round').textContent=String(state.round).padStart(2,'0');$('seed').textContent=`SEED ${state.seed}`;
  $('phase').textContent=state.status==='active'?'SQUAD PHASE':state.status.toUpperCase();
  $('contacts').textContent=state.units.filter(u=>u.team==='alien'&&u.hp>0).length+' VISIBLE CONTACTS';
  $('body-count').textContent=`BODY COUNT · ENEMY ${state.casualties.enemy} / FRIENDLY ${state.casualties.friendly}`;
  $('alive').textContent=state.units.filter(u=>u.team==='soldier'&&u.hp>0).length;
  $('civilians').textContent=state.civilians.total?`CIVILIANS ${state.civilians.alive}/${state.civilians.total} · ${state.civilians.evacuated} EVAC`:state.mission.round_limit?`OBJECTIVE · ${Math.max(0,state.mission.round_limit-state.round+1)} ROUNDS LEFT`:'NO CIVILIANS';
  $('squad').innerHTML=state.units.filter(u=>u.team==='soldier').map((u,i)=>`<button class="soldier ${u.id===selected?'selected':''}" data-unit="${u.id}" title="Select ${u.name} (${i+1})" ${u.hp<=0?'disabled':''}><span class="portrait portrait-${i}"></span><span class="info"><b>${u.name}</b><small>${u.role} · L${u.z}</small><span class="health"><i style="width:${u.hp/u.max_hp*100}%"></i></span><small>${u.hp}/${u.max_hp} HP</small></span><span class="ap">${u.overwatch?'◉':'●'.repeat(u.ap)+'○'.repeat(Math.max(0,state.player_time-u.ap))}</span></button>`).join('');
  document.querySelectorAll('[data-unit]').forEach(b=>b.onclick=()=>select(b.dataset.unit));
  renderDetails();renderOrderInfo();
  $('log').replaceChildren(...state.log.map(line=>{const el=document.createElement('div');el.textContent=line;return el;}));$('log').scrollTop=$('log').scrollHeight;
  $('end').disabled=state.status!=='active';
  $('outcome').hidden=['active','loadout'].includes(state.status);
  if(!$('outcome').hidden){if(campaignRun&&state.status==='victory')recordCampaignVictory();const label=campaignRun?(state.status==='victory'?'Campaign overview':'Retry mission'):'Prepare another mission';$('outcome').innerHTML=`<h2>${state.status==='victory'?'Mission accomplished':'Mission failed'}</h2><p>${state.mission.objective}</p>${button('again','new',label)}`;$('again').onclick=campaignRun?(state.status==='victory'?showCampaign:startCampaignMission):newMission;}
  if(state.status==='loadout'&&screen==='game'){renderPreparation();if(!$('preparation').open)$('preparation').showModal();}
  else if($('preparation').open)$('preparation').close();
  const aim=pending?.action==='attack'?pending:null;
  battlefield.sync(state,selected,null,mode,aim);
  battlefield.showPreview(pending);
  actionAudio.setListener(state,battlefield.camera);
  minimap.draw(state,selected,battlefield.controls.target);
}
/** Render controls and equipment for the selected fighter. */
function renderDetails(){
  const u=soldier();if(!u){$('details').textContent='No surviving operatives.';return;}
  const w=state.weapons[u.weapon],item=u.inventory[u.weapon],enabled=u.hp>0&&u.ap>0&&state.status==='active';
  const explosive=['grenade','rocket','smoke','charge','medical'].includes(w.kind);
  $('details').innerHTML=`<div class="eyebrow">${u.name} / EQUIPMENT</div><h2>${u.weapon}</h2><div class="stats"><span>${u.ammo}/${w.capacity} ${w.kind==='medical'?'USES':'LOADED'}</span><span>${item.reserve} RESERVE</span><span>${u.ap}/2 AP</span></div><div class="toolbar"><div><div class="eyebrow">ORDER</div>${button('move-mode','move','Preview movement to a tile',!enabled,mode==='move')}${button('attack-mode','attack',w.kind==='medical'?'Treat an adjacent wounded teammate':'Aim at any visible point within weapon range',!enabled,mode==='attack')}${button('face-mode','face','Choose facing direction · 0 AP',u.hp<=0||state.status!=='active',mode==='face')}</div><div><div class="eyebrow">ACTIONS</div>${button('reload','reload','Reload · 1 AP',!enabled||u.ammo===w.capacity||!item.reserve)}${button('watch','watch','Overwatch · ends turn',!enabled||!u.ammo||explosive||(w.kind==='sniper'&&u.ap<2))}</div></div><div class="inventory">${Object.entries(u.inventory).map(([name,item])=>`<button class="item ${name===u.weapon?'active':''}" data-weapon="${name}" title="Equip ${name}: ${stats(name)}" ${!enabled?'disabled':''}>${itemArt(name)}<b>${name}</b><small>${item.ammo} + ${item.reserve} ${state.weapons[name].kind==='medical'?'treatments':'rounds'}</small></button>`).join('')}</div>${w.automatic?`<div class="control-row"><span>FIRE MODE</span><div>${button('single-mode','single','Single shot · accurate',!enabled,u.fire_mode!=='auto')}${button('auto-mode','auto','Automatic · 3 rounds, −20 aim per shot',!enabled,u.fire_mode==='auto')}</div></div>`:''}<div class="control-row"><span>STANCE · 1 AP</span><div>${Object.keys(state.stances).map(s=>button(`stance-${s}`,s,`${s} · ${state.stances[s].speed} tiles/AP`,!enabled||s===u.stance,s===u.stance)).join('')}</div></div><div class="small-note">${stats(u.weapon)}${w.kind==='charge'?'<br>2-phase timer · 4-tile blast. Withdraw before detonation.':w.kind==='smoke'?'<br>Blocks both sides’ sight for 3 hostile phases.':''}</div>${interactionPanel(u,enabled)}`;
  $('details').querySelector('.stats span:last-child').textContent=`${u.ap}/${state.player_time} AP`;
  document.querySelectorAll('[data-weapon]').forEach(b=>b.onclick=()=>{goalVersion++;goalKey=null;pending=null;mode='attack';act('equip',{weapon:b.dataset.weapon});});
  $('move-mode').onclick=()=>refreshMode('move');$('attack-mode').onclick=()=>refreshMode('attack');
  $('face-mode').onclick=()=>refreshMode('face','Click any map point to face it · 0 AP.');
  document.querySelectorAll('[data-peek]').forEach(b=>b.onclick=()=>{const [x,y,z]=b.dataset.peek.split(',').map(Number);act('peek',{x,y,z});});
  $('reload').onclick=()=>act('reload');$('watch').onclick=()=>act('overwatch');
  if(w.automatic){$('single-mode').onclick=()=>act('fire_mode',{mode:'single'});$('auto-mode').onclick=()=>act('fire_mode',{mode:'auto'});}
  Object.keys(state.stances).forEach(s=>$(`stance-${s}`).onclick=()=>act('stance',{stance:s}));
  document.querySelectorAll('[data-portal]').forEach(b=>{const data={action:'interact',unit:selected,portal:b.dataset.portal};b.onclick=()=>chooseGoal(data);b.ondblclick=()=>chooseGoal(data,true);});
  document.querySelectorAll('[data-climb]').forEach(b=>{const [x,y,z]=b.dataset.climb.split(',').map(Number),data={action:'move',unit:selected,x,y,z};b.onclick=()=>chooseGoal(data);b.ondblclick=()=>chooseGoal(data,true);});
}
/** Return controls for nearby doors, windows, and fieldcraft. */
function interactionPanel(u,enabled){const portals=state.interactions[u.id]||[],transitions=state.transitions[u.id]||[],corners=state.corners?.[u.id]||[];if(!portals.length&&!transitions.length&&!corners.length)return '';return `<div class="interactions"><div class="eyebrow">NEARBY INTERACTIONS</div><div class="interaction-icons">${corners.map(p=>`<button class="icon-button" data-peek="${p.x},${p.y},${p.z}" title="Peek ${p.x<u.x?'west':p.x>u.x?'east':p.y<u.y?'north':'south'} and retreat · 1 AP · enemy hit chance ≤10%" aria-label="Peek around cover" ${!enabled?'disabled':''}>${icon('peek')}</button>`).join('')}${portals.map(p=>`<button class="icon-button" data-portal="${p.id}" title="Double-click to ${p.open?'close':'open'} ${p.side} ${p.kind} · 1 AP" aria-label="${p.open?'Close':'Open'} ${p.kind}" ${!enabled?'disabled':''}>${icon(p.kind)}</button>`).join('')}${transitions.map(p=>`<button class="icon-button" data-climb="${p.x},${p.y},${p.z}" title="Double-click to climb to level ${p.z}" aria-label="Climb to level ${p.z}" ${!enabled?'disabled':''}>${icon(p.z>u.z?'up':'down')}</button>`).join('')}</div></div>`;}
/** Render the currently previewed tactical order. */
function renderOrderInfo(){
  if(!pending)return;
  let detail=`${pending.action.toUpperCase()} PREVIEW · ${pending.name} · ${pending.cost} AP`;
  if(pending.action==='attack'){
    detail+=` · ${pending.radius?pending.radius+'-tile radius':pending.chance+'% · '+pending.rounds+' round(s)'}`;
    if(pending.hp!==null)detail+=` · ${pending.hp}/${pending.max_hp} HP`;
    if(pending.friendly||pending.victims?.some(v=>v.team!=='alien'))detail+=' · FRIENDLY FIRE RISK';
    if(pending.via)detail+=' · CORNER THROW';
  }
  if(pending.action==='heal')detail+=` · +${pending.heal} HP`;
  message(detail+' · Double-click goal to execute; Esc cancels.');
}
/** Validate a clicked goal and preview or execute its action. */
async function chooseGoal(data,execute=false){
  if(busy&&activeRequest!=='/api/preview')return;
  const key=JSON.stringify(data);
  if(key!==goalKey){
    goalKey=key;const version=++goalVersion,previous=previewTask;pending=null;
    previewTask=(async()=>{await previous;if(version!==goalVersion)return;await request('/api/preview',data);if(version!==goalVersion){pending=null;render();}})();
  }
  const version=goalVersion;await previewTask;
  if(execute&&version===goalVersion&&pending&&JSON.stringify(pending.payload)===key&&!busy&&executedVersion!==version){
    executedVersion=version;await request('/api/action',pending.payload);goalKey=null;
  }
}
/** Resolve a canvas pointer event to tactical scene data. */
function pick(hit,execute=false){
  if(!state||(busy&&activeRequest!=='/api/preview')||state.status!=='active')return;
  const u=state.units.find(u=>u.id===hit.unit),memory=state.last_seen?.find(m=>m.id===hit.memory);
  let p=u||memory||hit;
  if(mode==='move'&&hit.transition){const own=soldier(),at=hit.ends.findIndex(v=>v[0]===own.x&&v[1]===own.y&&v[2]===own.z);const end=at>=0?hit.ends[1-at]:hit.ends.find(v=>v[2]===own.z)||hit.ends[0];p={x:end[0],y:end[1],z:end[2]};}
  if(mode==='face'){if(!busy&&!execute)act('face',{x:p.x,y:p.y});return;}
  if(mode==='move'&&u?.team==='soldier'&&u.hp>0){select(u.id);return;}
  if(mode==='move'&&hit.portal){chooseGoal({action:'interact',unit:selected,portal:hit.portal},execute);return;}
  const data=mode==='attack'?(state.weapons[soldier().weapon].kind==='medical'?{action:'heal',unit:selected,target:u?.id}:{action:'attack',unit:selected,x:p.x,y:p.y,z:p.z,...(hit.structure?{structure:hit.structure}:{})}):{action:'move',unit:selected,x:p.x,y:p.y,z:p.z};
  chooseGoal(data,execute);
}
/** Update UI messaging for the currently hovered scene target. */
function hover(hit){if(!state)return;if(!hit){$('tile-info').textContent='RECON VIEW';return;}if(hit.transition){$('tile-info').textContent=`${hit.transition.startsWith('ladder:')?'LADDER':'STAIRS'} · L${hit.ends[0][2]} ↔ L${hit.ends[1][2]} · Double-click to approach or climb`;return;}if(hit.portal){const p=state.portals.find(p=>p.id===hit.portal);if(p){$('tile-info').textContent=`${p.open?'OPEN':'CLOSED'} ${p.kind.toUpperCase()} · L${p.a[2]}`;return;}}if(hit.memory){const m=state.last_seen.find(m=>m.id===hit.memory);$('tile-info').textContent=`${m.name} · LAST SEEN ROUND ${m.round} · UNCONFIRMED`;return;}const u=state.units.find(u=>u.id===hit.unit),p=[...state.props,...state.buildings].find(p=>p.id===hit.structure);$('tile-info').textContent=u?`${u.name} · ${u.hp}/${u.max_hp} HP · L${u.z}`:p?`${p.name||p.kind} · ${p.hp}/${p.max_hp} HP`:`TILE ${hit.x+1}, ${hit.y+1} · L${hit.z}`;}
/** Create or restore the editable squad loadout. */
function initializeDraft(){
  if(draft)return;const saved=cookieJSON('turn4turn_loadout'),soldiers=state.units.filter(u=>u.team==='soldier'),slots=['primary','sidearm','utility1','utility2'];
  if(saved&&soldiers.every(u=>saved[u.id]&&slots.every(slot=>state.weapons[saved[u.id][slot]]))){draft=saved;return;}
  draft={};soldiers.forEach((u,i)=>draft[u.id]={primary:u.weapon,sidearm:'M9',utility1:i===2?'Smoke grenade':'Frag grenade',utility2:i===3?'Demolition charge':'RPG-7'});
}
/** Render mission configuration and squad loadouts. */
function renderPreparation(){
  initializeDraft();
  $('loadout-content').innerHTML=`<div class="mission-options"><label>MISSION<select id="mission-type">${Object.entries(state.missions).map(([key,m])=>`<option value="${key}" ${configMission===key?'selected':''}>${m.label}</option>`).join('')}</select></label><label>THEATER<select id="mission-theme">${[['random','Random theater'],...Object.entries(state.themes).map(([key,t])=>[key,t.label])].map(([key,label])=>`<option value="${key}" ${configTheme===key?'selected':''}>${label}</option>`).join('')}</select></label><label>MAP SIZE<select id="mission-size">${[24,30,40].map((n,i)=>`<option value="${n}" ${configSize===n?'selected':''}>${['Compact','Standard','Large'][i]} · ${n} × ${n}</option>`).join('')}</select></label><div class="mission-summary">${state.mission.objective}<small>${state.size*state.size} ground tiles · randomized layout</small></div></div><p class="small-note">Click an equipment image to replace it. Four different items per fighter. Every slot accepts any weapon or item.</p><div class="loadout-grid">${state.units.filter(u=>u.team==='soldier').map((u,i)=>`<article class="loadout-card"><div class="loadout-person"><span class="portrait portrait-${i}"></span><div><b>${u.name}</b><small>${u.role}</small></div></div>${['primary','sidearm','utility1','utility2'].map((slot,j)=>`<div class="slot"><span class="eyebrow">${`SLOT ${j+1}`}</span><button class="equipment-slot" data-slot="${u.id}:${slot}" title="Choose equipment for ${u.name}">${itemArt(draft[u.id][slot])}<b>${draft[u.id][slot]}</b></button></div>`).join('')}</article>`).join('')}</div><div class="deploy-row"><div><b>Ready for insertion</b><p id="loadout-error" role="alert">Equipment is fixed after deployment.</p></div>${button('deploy','deploy','Deploy equipped squad')}</div>`;
  const difficultyLabel=document.createElement('label');difficultyLabel.textContent='DIFFICULTY';
  const difficultySelect=document.createElement('select');difficultySelect.id='mission-difficulty';
  for(const [key,d] of Object.entries(state.difficulties)){const option=new Option(`${d.label} · ${d.player_time} squad / ${d.enemy_time} hostile`,key);option.selected=configDifficulty===key;difficultySelect.add(option);}
  difficultyLabel.append(difficultySelect);document.querySelector('.mission-summary').before(difficultyLabel);
  const lightingLabel=document.createElement('label');lightingLabel.textContent='TIME';const lightingSelect=document.createElement('select');lightingSelect.id='mission-lighting';
  for(const [key,label] of Object.entries(state.lighting_options)){const option=new Option(label,key);option.selected=configLighting===key;lightingSelect.add(option);}lightingLabel.append(lightingSelect);document.querySelector('.mission-summary').before(lightingLabel);
  document.querySelector('.mission-options').style.gridTemplateColumns='repeat(auto-fit,minmax(150px,1fr))';
  if(campaignRun){
    for(const select of document.querySelectorAll('.mission-options select'))select.disabled=true;
    document.querySelector('.mission-summary').insertAdjacentHTML('beforeend','<small>Campaign mission settings are fixed.</small>');
  }
  const remember=document.createElement('label');remember.className='remember-loadout';remember.innerHTML=`<input id="save-loadout" type="checkbox" ${cookie('turn4turn_loadout')?'checked':''}> Use this equipment selection as my default loadout`;document.querySelector('.deploy-row>div').append(remember);
  const reloadMission=()=>request('/api/new',{theme:configTheme,size:configSize,difficulty:configDifficulty,mission:configMission,lighting:configLighting});
  $('mission-type').onchange=()=>{configMission=$('mission-type').value;reloadMission();};
  $('mission-theme').onchange=()=>{configTheme=$('mission-theme').value;reloadMission();};
  $('mission-size').onchange=()=>{configSize=Number($('mission-size').value);reloadMission();};
  $('mission-difficulty').onchange=()=>{configDifficulty=$('mission-difficulty').value;reloadMission();};
  $('mission-lighting').onchange=()=>{configLighting=$('mission-lighting').value;reloadMission();};
  document.querySelectorAll('[data-slot]').forEach(b=>b.onclick=()=>{editSlot=b.dataset.slot.split(':');openEquipment();});
  $('deploy').onclick=()=>{if($('save-loadout').checked)setCookie('turn4turn_loadout',draft);else deleteCookie('turn4turn_loadout');request('/api/action',{action:'deploy',loadouts:draft});};
}
/** Open equipment. */
function openEquipment(){
  const choices=itemOrder;
  $('equipment-title').textContent=editSlot?'Choose equipment for this slot':'Equipment catalog';
  $('equipment-grid').innerHTML=choices.map(name=>`<${editSlot?'button':'article'} class="catalog-item ${editSlot&&draft[editSlot[0]][editSlot[1]]===name?'active':''}" ${editSlot?`data-choice="${name}" title="Select ${name}"`:''}>${itemArt(name)}<b>${name}</b><p>${stats(name)}</p><small>${state.weapons[name].kind==='medical'?'2 treatments · +6 HP · 1 AP':state.weapons[name].kind==='shotgun'?'High power · short range':state.weapons[name].kind==='smoke'?'3-phase visual screen':state.weapons[name].kind==='charge'?'2-phase timer · heavy demolition':state.weapons[name].kind==='sniper'?'Bolt-action precision · 2 AP':'Finite ammunition'}</small></${editSlot?'button':'article'}>`).join('');
  document.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{draft[editSlot[0]][editSlot[1]]=b.dataset.choice;$('equipment').close();renderPreparation();});
  if(!$('equipment').open)$('equipment').showModal();
}
/** Request a new configurable standalone mission. */
function newMission(){if(busy)return;draft=null;selected='s0';mode='move';configTheme=state?.theme||'random';configSize=state?.size||30;configDifficulty=state?.difficulty||'medium';configMission=state?.mission?.key||'rescue';configLighting=state?.lighting||'day';request('/api/new',{theme:configTheme,size:configSize,difficulty:configDifficulty,mission:configMission,lighting:configLighting});}
/** Persist current campaign progress in the browser. */
function campaignSave(){if(campaignProgress&&cookie('turn4turn_name'))setCookie('turn4turn_campaign',campaignProgress);}
/** Load campaign save. */
function loadCampaignSave(){const p=cookieJSON('turn4turn_campaign');return p?.id===campaignData.id&&Number.isInteger(p.index)&&p.index>=0&&p.index<=campaignData.missions.length?p:null;}
/** Close dialogs. */
function closeDialogs(){for(const d of document.querySelectorAll('dialog[open]'))d.close();}
/** Show landing. */
function showLanding(){screen='landing';closeDialogs();$('campaign-screen').hidden=true;$('landing').hidden=false;}
/** Show game. */
function showGame(){$('startup-error').hidden=true;screen='game';$('landing').hidden=true;$('campaign-screen').hidden=true;if(state)render();}
/** Render campaign progress and available actions. */
function renderCampaign(){
  const p=campaignProgress||{id:campaignData.id,index:0};$('campaign-title').textContent=campaignData.title;$('campaign-description').textContent=campaignData.description;
  $('campaign-progress').innerHTML=campaignData.missions.map((m,i)=>`<button class="campaign-node ${i<p.index?'complete':i===p.index?'current':'locked'}" data-campaign-mission="${i}" ${i!==p.index?'disabled':''}><small>${String(i+1).padStart(2,'0')} · ${i<p.index?'COMPLETE':i===p.index?'CURRENT':'LOCKED'}</small><b>${escape(m.title)}</b><span>${escape(m.objective)}</span></button>`).join('');
  const complete=p.index>=campaignData.missions.length,hasSave=!!loadCampaignSave();$('campaign-actions').innerHTML=`<button id="new-campaign">Start new campaign</button>${hasSave&&!complete?'<button id="resume-campaign" class="primary">Resume current mission</button>':''}${complete?'<button id="replay-campaign" class="primary">Play campaign again</button>':''}`;
  document.querySelector('[data-campaign-mission]:not([disabled])')?.addEventListener('click',startCampaignMission);$('new-campaign').onclick=()=>{campaignProgress={id:campaignData.id,index:0,activeSeed:null};campaignSave();renderCampaign();};
  $('resume-campaign')?.addEventListener('click',startCampaignMission);$('replay-campaign')?.addEventListener('click',()=>{campaignProgress={id:campaignData.id,index:0,activeSeed:null};campaignSave();startCampaignMission();});
}
/** Show campaign. */
async function showCampaign(){if(busy)return;try{campaignData??=await fetch('/api/campaign').then(r=>{if(!r.ok)throw Error('Could not load campaign. Please try again.');return r.json();});}catch(error){$('startup-error').hidden=false;$('startup-error').textContent=error.message;return;}screen='campaign';campaignRun=true;closeDialogs();$('landing').hidden=true;$('campaign-screen').hidden=false;campaignProgress=loadCampaignSave()||{id:campaignData.id,index:0,activeSeed:null};renderCampaign();}
/** Start campaign mission. */
function startCampaignMission(){if(busy||campaignProgress.index>=campaignData.missions.length)return;const m=campaignData.missions[campaignProgress.index];campaignRun=true;campaignProgress.activeSeed=m.seed;campaignSave();draft=null;selected='s0';mode='move';configTheme=m.theme;configSize=m.size;configDifficulty=m.difficulty;configMission=m.mission;configLighting=m.lighting;showGame();request('/api/new',m);}
/** Advance and persist campaign progress after victory. */
function recordCampaignVictory(){if(!campaignProgress||campaignProgress.activeSeed!==state.seed)return;campaignProgress.index=Math.min(campaignData.missions.length,campaignProgress.index+1);campaignProgress.activeSeed=null;campaignSave();}
/** Start single. */
function startSingle(){if(busy)return;campaignRun=false;showGame();newMission();}
hydrate();
$('preparation').addEventListener('cancel',e=>e.preventDefault());
$('welcome').addEventListener('cancel',e=>e.preventDefault());
$('close-equipment').onclick=()=>$('equipment').close();$('close-help').onclick=()=>$('manual').close();
$('armory').onclick=()=>{if(!state)return;editSlot=null;openEquipment();};$('help').onclick=()=>$('manual').showModal();
$('home').onclick=showLanding;$('campaign-home').onclick=showLanding;$('campaign-mode').onclick=showCampaign;$('single-game').onclick=startSingle;$('new').onclick=()=>campaignRun?startCampaignMission():newMission();$('end').onclick=()=>act('end_turn');$('focus').onclick=()=>battlefield?.focus(soldier());$('reset-camera').onclick=()=>battlefield?.home();
$('view-level').onchange=()=>{if(busy)return;pending=null;battlefield.setView($('view-level').value);render();};
$('sound').checked=actionAudio.enabled;$('volume').value=actionAudio.volume;$('sound').onchange=()=>actionAudio.setEnabled($('sound').checked);$('volume').oninput=()=>actionAudio.setVolume($('volume').value);
document.addEventListener('pointerdown',()=>actionAudio.unlock(),{once:true});document.addEventListener('keydown',()=>actionAudio.unlock(),{once:true});
document.addEventListener('click',e=>{if(e.target.closest('button'))actionAudio.play({type:'button'});});
document.addEventListener('change',e=>{if(e.target.matches('select'))actionAudio.play({type:'button'});});
document.addEventListener('keydown',e=>{if(e.repeat||e.ctrlKey||e.metaKey||e.altKey||!state||busy||state.status!=='active'||document.querySelector('dialog[open]')||['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.key==='Escape')cancel();else if('1234'.includes(e.key)){const u=state.units.filter(u=>u.team==='soldier')[+e.key-1];if(u?.hp>0)select(u.id);}else if(e.key.toLowerCase()==='f')battlefield.focus(soldier());else if(e.key.toLowerCase()==='r')act('reload');else if(e.key.toLowerCase()==='o')act('overwatch');else if(e.key==='Enter'&&document.activeElement.tagName!=='BUTTON'){e.preventDefault();if(pending)chooseGoal(pending.payload,true);else act('end_turn');}});
// The landing page needs no mission state, renderer, models, textures or audio.
showLanding();
if(new URLSearchParams(location.search).get('mode')==='single'){
  showGame();request('/api/state');
}
// Expose the renderer instance for integration tests and local development tools.
export {battlefield};
