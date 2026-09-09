import {Battlefield} from './scene.js';
import {actionAudio} from './audio.js';
import {icon,button,hydrate} from './icons.js';
import {Minimap} from './minimap.js';
const $=id=>document.getElementById(id);
const itemOrder=['M4A1','HK416','M110','M249','M9','RPG-7','Frag grenade','Alien carbine','M24 sniper','Smoke grenade','Demolition charge','Shotgun','Medikit'];
const photographs={'Shotgun':'shotgun.png','Medikit':'medikit.png','M24 sniper':'m24.png','Smoke grenade':'smoke-grenade.png','Demolition charge':'demolition-charge.png'};
let state,battlefield,minimap,selected='s0',mode='move',busy=false,pending=null,draft=null,editSlot=null,configTheme='random',configSize=30;
let activeRequest=null,previewTask=null,goalKey=null,goalVersion=0,executedVersion=-1;
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function itemArt(name){return photographs[name]?`<img class="item-photo" src="/assets/${photographs[name]}" alt="${name}">`:`<span class="item-art art-${itemOrder.indexOf(name)}" role="img" aria-label="${name}"></span>`;}
function soldier(){return state?.units.find(u=>u.id===selected);}
function message(text){$('message').textContent=text;}
function stats(name){const w=state.weapons[name];return `${w.kind==='medical'?w.heal+' HEAL':w.damage+' DMG'} · ${w.range} tiles · ${w.capacity} ${w.kind==='medical'?'uses':'loaded'}${w.automatic?' · AUTO':''}${w.kind==='sniper'?' · 2 AP':''}`;}
function setBusy(value){busy=value;document.body.classList.toggle('busy',value);$('preparation').inert=value;$('equipment').inert=value;}
async function request(path,data){
  if(busy)return;activeRequest=path;setBusy(true);
  try{
    const response=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');
    if(path==='/api/preview'){pending={...result,payload:data};message('Goal selected. Double-click the same point to execute; Escape cancels.');}
    else{
      pending=null;
      if(state&&path==='/api/action')try{await battlefield.animate(result.events,data?.action==='end_turn');}catch(error){console.warn('Animation failed; applying authoritative state.',error);}
      state=result;await actionAudio.prepare(state);
      if(!state.units.some(u=>u.id===selected&&u.hp>0))selected=state.units.find(u=>u.team==='soldier'&&u.hp>0)?.id;
      message(state.status==='loadout'?'Choose the mission and equip your squad.':state.status==='active'?'Single-click a goal to preview; double-click it to execute.':'Mission complete. Prepare another operation.');
    }
  }catch(error){pending=null;message(error.message);if($('loadout-error'))$('loadout-error').textContent=error.message;}
  finally{activeRequest=null;setBusy(false);if(state)render();}
}
function act(action,extra={}){goalVersion++;goalKey=null;pending=null;return request('/api/action',{action,unit:selected,...extra});}
function preview(action,extra={}){return request('/api/preview',{action,unit:selected,...extra});}
function cancel(){goalVersion++;goalKey=null;pending=null;render();message('Preview cancelled. Choose another point.');}
function select(id){if(busy)return;selected=id;goalVersion++;goalKey=null;pending=null;mode='move';battlefield.setView('auto');$('view-level').value='auto';render();battlefield.focus(soldier());}
function render(){
  $('theme-label').textContent=`${state.scenery.label.toUpperCase()} / ${state.size} × ${state.size}`;
  $('round').textContent=String(state.round).padStart(2,'0');$('seed').textContent=`SEED ${state.seed}`;
  $('phase').textContent=state.status==='active'?'SQUAD PHASE':state.status.toUpperCase();
  $('contacts').textContent=state.units.filter(u=>u.team==='alien'&&u.hp>0).length+' VISIBLE CONTACTS';
  $('alive').textContent=state.units.filter(u=>u.team==='soldier'&&u.hp>0).length;
  $('civilians').textContent=`CIVILIANS ${state.civilians.alive}/${state.civilians.total} · ${state.civilians.evacuated} EVAC`;
  $('squad').innerHTML=state.units.filter(u=>u.team==='soldier').map((u,i)=>`<button class="soldier ${u.id===selected?'selected':''}" data-unit="${u.id}" title="Select ${u.name} (${i+1})" ${u.hp<=0?'disabled':''}><span class="portrait portrait-${i}"></span><span class="info"><b>${u.name}</b><small>${u.role} · L${u.z}</small><span class="health"><i style="width:${u.hp/u.max_hp*100}%"></i></span><small>${u.hp}/${u.max_hp} HP</small></span><span class="ap">${u.overwatch?'◉':'●'.repeat(u.ap)+'○'.repeat(2-u.ap)}</span></button>`).join('');
  document.querySelectorAll('[data-unit]').forEach(b=>b.onclick=()=>select(b.dataset.unit));
  renderDetails();renderOrderInfo();
  $('log').replaceChildren(...state.log.map(line=>{const el=document.createElement('div');el.textContent=line;return el;}));$('log').scrollTop=$('log').scrollHeight;
  $('end').disabled=state.status!=='active';
  $('outcome').hidden=['active','loadout'].includes(state.status);
  if(!$('outcome').hidden){$('outcome').innerHTML=`<h2>${state.status==='victory'?'Sector secured':'Squad lost'}</h2><p>${state.status==='victory'?'All hostiles eliminated.':'All operatives have fallen.'}</p>${button('again','new','Prepare another mission')}`;$('again').onclick=newMission;}
  if(state.status==='loadout'){renderPreparation();if(!$('preparation').open)$('preparation').showModal();}
  else if($('preparation').open)$('preparation').close();
  const aim=pending?.action==='attack'?pending:null;
  battlefield.sync(state,selected,null,mode,aim);
  battlefield.showPreview(pending);
  actionAudio.setListener(state,battlefield.camera);
  minimap.draw(state,selected,battlefield.controls.target);
}
function renderDetails(){
  const u=soldier();if(!u){$('details').textContent='No surviving operatives.';return;}
  const w=state.weapons[u.weapon],item=u.inventory[u.weapon],enabled=u.hp>0&&u.ap>0&&state.status==='active';
  const explosive=['grenade','rocket','smoke','charge','medical'].includes(w.kind);
  $('details').innerHTML=`<div class="eyebrow">${u.name} / EQUIPMENT</div><h2>${u.weapon}</h2><div class="stats"><span>${u.ammo}/${w.capacity} ${w.kind==='medical'?'USES':'LOADED'}</span><span>${item.reserve} RESERVE</span><span>${u.ap}/2 AP</span></div><div class="toolbar"><div><div class="eyebrow">ORDER</div>${button('move-mode','move','Preview movement to a tile',!enabled,mode==='move')}${button('attack-mode','attack',w.kind==='medical'?'Treat an adjacent wounded teammate':'Aim at any visible point within weapon range',!enabled,mode==='attack')}${button('face-mode','face','Choose facing direction · 0 AP',u.hp<=0||state.status!=='active',mode==='face')}</div><div><div class="eyebrow">ACTIONS</div>${button('reload','reload','Reload · 1 AP',!enabled||u.ammo===w.capacity||!item.reserve)}${button('watch','watch','Overwatch · ends turn',!enabled||!u.ammo||explosive||(w.kind==='sniper'&&u.ap<2))}</div></div><div class="inventory">${Object.entries(u.inventory).map(([name,item])=>`<button class="item ${name===u.weapon?'active':''}" data-weapon="${name}" title="Equip ${name}: ${stats(name)}" ${!enabled?'disabled':''}>${itemArt(name)}<b>${name}</b><small>${item.ammo} + ${item.reserve} ${state.weapons[name].kind==='medical'?'treatments':'rounds'}</small></button>`).join('')}</div>${w.automatic?`<div class="control-row"><span>FIRE MODE</span><div>${button('single-mode','single','Single shot · accurate',!enabled,u.fire_mode!=='auto')}${button('auto-mode','auto','Automatic · 3 rounds, −20 aim per shot',!enabled,u.fire_mode==='auto')}</div></div>`:''}<div class="control-row"><span>STANCE · 1 AP</span><div>${Object.keys(state.stances).map(s=>button(`stance-${s}`,s,`${s} · ${state.stances[s].speed} tiles/AP`,!enabled||s===u.stance,s===u.stance)).join('')}</div></div><div class="small-note">${stats(u.weapon)}${w.kind==='charge'?'<br>2-phase timer · 4-tile blast. Withdraw before detonation.':w.kind==='smoke'?'<br>Blocks both sides’ sight for 3 hostile phases.':''}</div>${interactionPanel(u,enabled)}`;
  document.querySelectorAll('[data-weapon]').forEach(b=>b.onclick=()=>{goalVersion++;goalKey=null;pending=null;mode='attack';act('equip',{weapon:b.dataset.weapon});});
  $('move-mode').onclick=()=>{mode='move';goalVersion++;goalKey=null;pending=null;render();};$('attack-mode').onclick=()=>{mode='attack';goalVersion++;goalKey=null;pending=null;render();};
  $('face-mode').onclick=()=>{mode='face';goalVersion++;goalKey=null;pending=null;render();message('Click any map point to face it · 0 AP.');};
  document.querySelectorAll('[data-peek]').forEach(b=>b.onclick=()=>{const [x,y,z]=b.dataset.peek.split(',').map(Number);act('peek',{x,y,z});});
  $('reload').onclick=()=>act('reload');$('watch').onclick=()=>act('overwatch');
  if(w.automatic){$('single-mode').onclick=()=>act('fire_mode',{mode:'single'});$('auto-mode').onclick=()=>act('fire_mode',{mode:'auto'});}
  Object.keys(state.stances).forEach(s=>$(`stance-${s}`).onclick=()=>act('stance',{stance:s}));
  document.querySelectorAll('[data-portal]').forEach(b=>{const data={action:'interact',unit:selected,portal:b.dataset.portal};b.onclick=()=>chooseGoal(data);b.ondblclick=()=>chooseGoal(data,true);});
  document.querySelectorAll('[data-climb]').forEach(b=>{const [x,y,z]=b.dataset.climb.split(',').map(Number),data={action:'move',unit:selected,x,y,z};b.onclick=()=>chooseGoal(data);b.ondblclick=()=>chooseGoal(data,true);});
}
function interactionPanel(u,enabled){const portals=state.interactions[u.id]||[],transitions=state.transitions[u.id]||[],corners=state.corners?.[u.id]||[];if(!portals.length&&!transitions.length&&!corners.length)return '';return `<div class="interactions"><div class="eyebrow">NEARBY INTERACTIONS</div><div class="interaction-icons">${corners.map(p=>`<button class="icon-button" data-peek="${p.x},${p.y},${p.z}" title="Peek ${p.x<u.x?'west':p.x>u.x?'east':p.y<u.y?'north':'south'} and retreat · 1 AP · enemy hit chance ≤10%" aria-label="Peek around cover" ${!enabled?'disabled':''}>${icon('peek')}</button>`).join('')}${portals.map(p=>`<button class="icon-button" data-portal="${p.id}" title="Double-click to ${p.open?'close':'open'} ${p.side} ${p.kind} · 1 AP" aria-label="${p.open?'Close':'Open'} ${p.kind}" ${!enabled?'disabled':''}>${icon(p.kind)}</button>`).join('')}${transitions.map(p=>`<button class="icon-button" data-climb="${p.x},${p.y},${p.z}" title="Double-click to climb to level ${p.z}" aria-label="Climb to level ${p.z}" ${!enabled?'disabled':''}>${icon(p.z>u.z?'up':'down')}</button>`).join('')}</div></div>`;}
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
function pick(hit,execute=false){
  if(!state||(busy&&activeRequest!=='/api/preview')||state.status!=='active')return;
  const u=state.units.find(u=>u.id===hit.unit),memory=state.last_seen?.find(m=>m.id===hit.memory);
  const p=u||memory||hit;
  if(mode==='face'){if(!busy&&!execute)act('face',{x:p.x,y:p.y});return;}
  if(mode==='move'&&u?.team==='soldier'&&u.hp>0){select(u.id);return;}
  if(mode==='move'&&hit.portal){chooseGoal({action:'interact',unit:selected,portal:hit.portal},execute);return;}
  const data=mode==='attack'?(state.weapons[soldier().weapon].kind==='medical'?{action:'heal',unit:selected,target:u?.id}:{action:'attack',unit:selected,x:p.x,y:p.y,z:p.z,...(hit.structure?{structure:hit.structure}:{})}):{action:'move',unit:selected,x:p.x,y:p.y,z:p.z};
  chooseGoal(data,execute);
}
function hover(hit){if(!state||!hit)return;if(hit.memory){const m=state.last_seen.find(m=>m.id===hit.memory);$('tile-info').textContent=`${m.name} · LAST SEEN ROUND ${m.round} · UNCONFIRMED`;return;}const u=state.units.find(u=>u.id===hit.unit),p=[...state.props,...state.buildings].find(p=>p.id===hit.structure);$('tile-info').textContent=u?`${u.name} · ${u.hp}/${u.max_hp} HP · L${u.z}`:p?`${p.name||p.kind} · ${p.hp}/${p.max_hp} HP`:`TILE ${hit.x+1}, ${hit.y+1} · L${hit.z}`;}
function initializeDraft(){if(draft)return;draft={};state.units.filter(u=>u.team==='soldier').forEach((u,i)=>draft[u.id]={primary:u.weapon,sidearm:'M9',utility1:i===2?'Smoke grenade':'Frag grenade',utility2:i===3?'Demolition charge':'RPG-7'});}
function renderPreparation(){
  initializeDraft();
  $('loadout-content').innerHTML=`<div class="mission-options"><label>THEATER<select id="mission-theme">${[['random','Random theater'],...Object.entries(state.themes).map(([key,t])=>[key,t.label])].map(([key,label])=>`<option value="${key}" ${configTheme===key?'selected':''}>${label}</option>`).join('')}</select></label><label>MAP SIZE<select id="mission-size">${[24,30,40].map((n,i)=>`<option value="${n}" ${configSize===n?'selected':''}>${['Compact','Standard','Large'][i]} · ${n} × ${n}</option>`).join('')}</select></label><div class="mission-summary">${state.scenery.label}<small>${state.size*state.size} ground tiles · randomized layout</small></div></div><p class="small-note">Click an equipment image to replace it. Four different items per fighter. Every slot accepts any weapon or item.</p><div class="loadout-grid">${state.units.filter(u=>u.team==='soldier').map((u,i)=>`<article class="loadout-card"><div class="loadout-person"><span class="portrait portrait-${i}"></span><div><b>${u.name}</b><small>${u.role}</small></div></div>${['primary','sidearm','utility1','utility2'].map((slot,j)=>`<div class="slot"><span class="eyebrow">${`SLOT ${j+1}`}</span><button class="equipment-slot" data-slot="${u.id}:${slot}" title="Choose equipment for ${u.name}">${itemArt(draft[u.id][slot])}<b>${draft[u.id][slot]}</b></button></div>`).join('')}</article>`).join('')}</div><div class="deploy-row"><div><b>Ready for insertion</b><p id="loadout-error" role="alert">Equipment is fixed after deployment.</p></div>${button('deploy','deploy','Deploy equipped squad')}</div>`;
  $('mission-theme').onchange=()=>{configTheme=$('mission-theme').value;request('/api/new',{theme:configTheme,size:configSize});};
  $('mission-size').onchange=()=>{configSize=Number($('mission-size').value);request('/api/new',{theme:configTheme,size:configSize});};
  document.querySelectorAll('[data-slot]').forEach(b=>b.onclick=()=>{editSlot=b.dataset.slot.split(':');openEquipment();});
  $('deploy').onclick=()=>request('/api/action',{action:'deploy',loadouts:draft});
}
function openEquipment(){
  const choices=itemOrder;
  $('equipment-title').textContent=editSlot?'Choose equipment for this slot':'Equipment catalog';
  $('equipment-grid').innerHTML=choices.map(name=>`<${editSlot?'button':'article'} class="catalog-item ${editSlot&&draft[editSlot[0]][editSlot[1]]===name?'active':''}" ${editSlot?`data-choice="${name}" title="Select ${name}"`:''}>${itemArt(name)}<b>${name}</b><p>${stats(name)}</p><small>${state.weapons[name].kind==='medical'?'2 treatments · +6 HP · 1 AP':state.weapons[name].kind==='shotgun'?'High power · short range':state.weapons[name].kind==='smoke'?'3-phase visual screen':state.weapons[name].kind==='charge'?'2-phase timer · heavy demolition':state.weapons[name].kind==='sniper'?'Bolt-action precision · 2 AP':'Finite ammunition'}</small></${editSlot?'button':'article'}>`).join('');
  document.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{draft[editSlot[0]][editSlot[1]]=b.dataset.choice;$('equipment').close();renderPreparation();});
  if(!$('equipment').open)$('equipment').showModal();
}
function newMission(){if(busy)return;draft=null;selected='s0';mode='move';configTheme=state?.theme||'random';configSize=state?.size||30;request('/api/new',{theme:configTheme,size:configSize});}
hydrate();
$('preparation').addEventListener('cancel',e=>e.preventDefault());
$('close-equipment').onclick=()=>$('equipment').close();$('close-help').onclick=()=>$('manual').close();
$('armory').onclick=()=>{if(!state)return;editSlot=null;openEquipment();};$('help').onclick=()=>$('manual').showModal();
$('new').onclick=newMission;$('end').onclick=()=>act('end_turn');$('focus').onclick=()=>battlefield?.focus(soldier());$('reset-camera').onclick=()=>battlefield?.home();
$('view-level').onchange=()=>{if(busy)return;pending=null;battlefield.setView($('view-level').value);render();};
$('sound').checked=actionAudio.enabled;$('volume').value=actionAudio.volume;$('sound').onchange=()=>actionAudio.setEnabled($('sound').checked);$('volume').oninput=()=>actionAudio.setVolume($('volume').value);
document.addEventListener('pointerdown',()=>actionAudio.unlock(),{once:true});document.addEventListener('keydown',()=>actionAudio.unlock(),{once:true});
document.addEventListener('keydown',e=>{if(e.repeat||e.ctrlKey||e.metaKey||e.altKey||!state||busy||state.status!=='active'||document.querySelector('dialog[open]')||['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.key==='Escape')cancel();else if('1234'.includes(e.key)){const u=state.units.filter(u=>u.team==='soldier')[+e.key-1];if(u?.hp>0)select(u.id);}else if(e.key.toLowerCase()==='f')battlefield.focus(soldier());else if(e.key.toLowerCase()==='r')act('reload');else if(e.key.toLowerCase()==='o')act('overwatch');else if(e.key==='Enter'&&document.activeElement.tagName!=='BUTTON'){e.preventDefault();if(pending)chooseGoal(pending.payload,true);else act('end_turn');}});
try{
  battlefield=new Battlefield($('map'),pick,hover);
  minimap=new Minimap($('minimap'),p=>battlefield.focus(p));
  battlefield.controls.addEventListener('change',()=>{if(state){minimap.draw(state,selected,battlefield.controls.target);actionAudio.setListener(state,battlefield.camera);}});
  request('/api/state').then(()=>{if(state){configTheme=state.theme;configSize=state.size;if(state.status==='loadout')renderPreparation();}});
}catch(error){message('WebGL could not start. Enable WebGL in your browser and reload. '+error.message);$('phase').textContent='WEBGL REQUIRED';}
// Expose the renderer instance for integration tests and local development tools.
export {battlefield};
