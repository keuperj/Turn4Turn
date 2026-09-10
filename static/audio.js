// Audio is generated offline. Only local, numbered files are fetched during play.
const weapons={'M4A1':'m4a1','HK416':'hk416','M110':'m110','M249':'m249','M9':'m9','M24 sniper':'m24_sniper','Shotgun':'shotgun'};
export function soundAction(e){
  if(e.type==='shot')return 'shot_'+(weapons[e.weapon]||'m4a1');
  if(e.type==='move')return e.origin&&e.origin[2]!==e.z?'climb':e.actor?.stance==='prone'?'crawl':'move';
  if(e.type==='blast')return 'blast_'+({rocket:'rocket',charge:'charge'}[e.kind]||'grenade');
  if(e.type==='portal')return `${e.kind==='window'?'window':'door'}_${e.open?'open':'close'}`;
  if(e.type==='peek_out'||e.type==='peek_return')return 'peek';
  if(['reload','throw','rocket_launch','smoke','charge_place','impact','hurt','heal','equip','stance','face','overwatch','fire_mode','evacuate','button'].includes(e.type))return e.type;
  return null;
}
export class ActionAudio {
  constructor(){
    this.enabled=localStorage.getItem('sound')!=='off';this.volume=Number(localStorage.getItem('volume')||.35);
    this.context=null;this.manifest={};this.buffers=new Map();this.previous=new Map();this.voices=new Set();this.ambientVoices=new Set();this.ambientVersion=0;this.theme=null;this.sceneKey=null;this.listener={x:0,y:0,z:0,rightX:1,rightY:0};
    this.catalogReady=this.refreshCatalog();
    document.addEventListener('visibilitychange',()=>{if(document.hidden){this.stopAmbience();this.stopEffects();}else this.startAmbience();});
  }
  async refreshCatalog(){
    try{const response=await fetch('/api/audio');if(!response.ok)throw Error('Audio catalog unavailable');this.manifest=await response.json();this.buffers.clear();}
    catch{this.manifest={};}
  }
  async unlock(){
    if(!this.enabled)return;
    try{
      if(!this.context){
        this.context=new (window.AudioContext||window.webkitAudioContext)();
        this.master=this.context.createGain();this.master.gain.value=this.volume;
        const limiter=this.context.createDynamicsCompressor();limiter.threshold.value=-10;limiter.knee.value=12;limiter.ratio.value=8;limiter.attack.value=.003;limiter.release.value=.15;
        this.master.connect(limiter).connect(this.context.destination);
      }
      await this.context.resume();await this.catalogReady;
      this.preload();this.startAmbience();
    }catch{this.enabled=false;}
  }
  setEnabled(value){this.enabled=value;localStorage.setItem('sound',value?'on':'off');if(value)this.unlock();else{this.stopEffects();this.stopAmbience();}}
  setVolume(value){this.volume=Math.max(0,Math.min(1,Number(value)||0));localStorage.setItem('volume',this.volume);if(this.master)this.master.gain.setTargetAtTime(this.volume,this.context.currentTime,.02);}
  async buffer(url){
    if(!this.context)return null;
    if(!this.buffers.has(url))this.buffers.set(url,(async()=>{
      try{const r=await fetch(url);if(!r.ok)throw Error('Missing sample');return await this.context.decodeAudioData(await r.arrayBuffer());}
      catch{return null;}
    })());
    return this.buffers.get(url);
  }
  async preload(){
    if(!this.context)return;
    const urls=[...new Set(Object.entries(this.manifest).filter(([a])=>!a.startsWith('ambient_')||a==='ambient_'+this.theme).flatMap(([,samples])=>samples.map(s=>s.url)))];
    // Limit simultaneous fetches; the Python localhost server is deliberately small.
    await Promise.all(Array.from({length:4},async()=>{while(urls.length)await this.buffer(urls.shift());}));
  }
  async prepare(state){
    const key=`${state.seed}:${state.theme}:${state.status}`;
    if(key===this.sceneKey)return;
    this.sceneKey=key;this.stopEffects();this.stopAmbience();this.theme=state.status==='active'?state.theme:null;
    this.catalogReady=this.refreshCatalog();await this.catalogReady;
    if(this.context){await this.preload();this.startAmbience();}
  }
  choose(action){
    const all=this.manifest[action]||[],candidates=all.length>1?all.filter(s=>s.url!==this.previous.get(action)):all;
    if(!candidates.length)return null;
    const sample=candidates[Math.floor(Math.random()*candidates.length)];this.previous.set(action,sample.url);return sample;
  }
  async sample(action){
    await this.catalogReady;
    const chosen=this.choose(action);
    // Try the other variants if one local file is missing or cannot be decoded.
    for(const s of [chosen,...(this.manifest[action]||[]).filter(s=>s!==chosen)]){
      if(!s)continue;const b=await this.buffer(s.url);if(b)return {buffer:b,sample:s};
    }
    return {buffer:this.fallback(action),sample:{placeholder:true}};
  }
  fallback(action){
    if(!this.context)return null;
    const ambient=action.startsWith('ambient_'),b=this.context.createBuffer(1,this.context.sampleRate*(ambient?2:.12),this.context.sampleRate),a=b.getChannelData(0);
    let low=0;for(let i=0;i<a.length;i++){low=.92*low+.08*(Math.random()*2-1);a[i]=low*(ambient?.035:.12)*Math.sin(Math.PI*i/(a.length-1))**2;}
    return b;
  }
  setListener(state,camera){
    const squad=state.units.filter(u=>u.team==='soldier'&&u.hp>0);if(!squad.length)return;
    const avg=k=>squad.reduce((sum,u)=>sum+u[k],0)/squad.length;
    // Anchor loudness to the squad, not zoom; use camera orientation for stereo.
    this.listener={x:avg('x'),y:avg('y'),z:avg('z'),rightX:camera.matrixWorld.elements[0],rightY:camera.matrixWorld.elements[2]};
  }
  stopEffects(){this.effectsVersion=(this.effectsVersion||0)+1;for(const s of [...this.voices])s.stop();this.voices.clear();}
  async play(e){
    const action=soundAction(e);
    if(!action||!this.enabled||!this.context||document.hidden)return;
    const version=this.effectsVersion||0,{buffer}=await this.sample(action);
    if(!buffer||!this.enabled||version!==(this.effectsVersion||0)||document.hidden)return;
    while(this.voices.size>=24){const first=this.voices.values().next().value;first.stop();this.voices.delete(first);}
    const c=this.context,s=c.createBufferSource(),gain=c.createGain(),pan=c.createStereoPanner();s.buffer=buffer;
    const point=e.type==='shot'?e.origin:e.type==='move'?[e.x,e.y,e.z]:e.point||(e.x!==undefined?[e.x,e.y,e.z]:e.actor?[e.actor.x,e.actor.y,e.actor.z]:null);
    let volume=['face','peek','stance','equip','overwatch','fire_mode'].includes(action)?.28:action==='hurt'?.48:.65;
    if(point){const dx=point[0]-this.listener.x,dy=point[1]-this.listener.y;volume/=1+Math.hypot(dx,dy)*.035;pan.pan.value=Math.max(-.85,Math.min(.85,(dx*this.listener.rightX+dy*this.listener.rightY)/14));}
    gain.gain.value=volume;s.connect(gain).connect(pan).connect(this.master);this.voices.add(s);
    s.onended=()=>{this.voices.delete(s);s.disconnect();gain.disconnect();pan.disconnect();};s.start();
  }
  stopAmbience(){
    this.ambientVersion++;clearTimeout(this.ambientTimer);this.ambientRunning=false;
    for(const s of [...this.ambientVoices])s.stop();this.ambientVoices.clear();
  }
  startAmbience(){
    if(this.ambientRunning||!this.theme||!this.enabled||!this.context||document.hidden)return;
    this.ambientRunning=true;const version=this.ambientVersion;
    const next=async()=>{
      const {buffer}=await this.sample('ambient_'+this.theme);
      if(!buffer||version!==this.ambientVersion||!this.enabled||document.hidden)return;
      const c=this.context,s=c.createBufferSource(),g=c.createGain(),now=c.currentTime,fade=Math.min(.3,buffer.duration/4);
      s.buffer=buffer;g.gain.setValueAtTime(0,now);g.gain.linearRampToValueAtTime(.22,now+fade);g.gain.setValueAtTime(.22,now+buffer.duration-fade);g.gain.linearRampToValueAtTime(0,now+buffer.duration);
      s.connect(g).connect(this.master);this.ambientVoices.add(s);s.onended=()=>{this.ambientVoices.delete(s);s.disconnect();g.disconnect();};s.start();
      this.ambientTimer=setTimeout(next,Math.max(50,(buffer.duration-fade)*1000));
    };next();
  }
}
export const actionAudio=new ActionAudio();
