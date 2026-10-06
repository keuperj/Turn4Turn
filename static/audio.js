/** @fileoverview Select and play local action sounds and environmental ambience. */
// Audio is generated offline. Only local, numbered files are fetched during play.
const weapons={'M4A1':'m4a1','HK416':'hk416','M110':'m110','M249':'m249','M9':'m9','M24 sniper':'m24_sniper','Shotgun':'shotgun'};
/** Map a public game event to its local audio action name. */
export function soundAction(e){
  if(e.type==='shot')return 'shot_'+(weapons[e.weapon]||'m4a1');
  if(e.type==='move')return e.origin&&e.origin[2]!==e.z?'climb':e.actor?.stance==='prone'?'crawl':'move';
  if(e.type==='blast')return 'blast_'+({rocket:'rocket',charge:'charge'}[e.kind]||'grenade');
  if(e.type==='portal')return `${e.kind==='window'?'window':'door'}_${e.open?'open':'close'}`;
  if(e.type==='peek_out'||e.type==='peek_return')return 'peek';
  if(['reload','throw','rocket_launch','smoke','charge_place','impact','hurt','heal','equip','stance','face','overwatch','fire_mode','evacuate','button'].includes(e.type))return e.type;
  return null;
}
/** Manage local Web Audio effects, ambience, and listener state. */
export class ActionAudio {
  /** Initialize this instance. */
  constructor(){
    this.enabled=localStorage.getItem('sound')!=='off';this.volume=Number(localStorage.getItem('volume')||.35);
    this.context=null;this.manifest={};this.buffers=new Map();this.previous=new Map();this.voices=new Set();this.ambientVoices=new Set();this.ambientVersion=0;this.theme=null;this.sceneKey=null;this.listener={x:0,y:0,z:0,rightX:1,rightY:0};
    this.catalogReady=null;
    document.addEventListener('visibilitychange',()=>{if(document.hidden){this.stopAmbience();this.stopEffects();}else this.startAmbience();});
  }
  /** Reload the server-provided local audio catalog. */
  async refreshCatalog(){
    try{const response=await fetch('/api/audio');if(!response.ok)throw Error('Audio catalog unavailable');this.manifest=await response.json();}
    catch{this.manifest={};}
  }
  /** Create or resume the Web Audio context after user interaction. */
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
      if(this.sceneKey)await this.preload();this.startAmbience();
    }catch{this.enabled=false;}
  }
  /** Update enabled. */
  setEnabled(value){this.enabled=value;localStorage.setItem('sound',value?'on':'off');if(value)this.unlock();else{this.stopEffects();this.stopAmbience();}}
  /** Update volume. */
  setVolume(value){this.volume=Math.max(0,Math.min(1,Number(value)||0));localStorage.setItem('volume',this.volume);if(this.master)this.master.gain.setTargetAtTime(this.volume,this.context.currentTime,.02);}
  /** Fetch and decode one local audio sample. */
  async buffer(url){
    if(!this.context)return null;
    if(!this.buffers.has(url))this.buffers.set(url,(async()=>{
      try{const r=await fetch(url);if(!r.ok)throw Error('Missing sample');return await this.context.decodeAudioData(await r.arrayBuffer());}
      catch{return null;}
    })());
    return this.buffers.get(url);
  }
  /** Fetch and decode every variant for an audio action. */
  async preload(onProgress=()=>{}){
    if(!this.context||!this.enabled){onProgress(1,1);return;}
    await this.catalogReady;
    this.progressListeners??=new Set();this.progressListeners.add(onProgress);
    const report=()=>{for(const listener of this.progressListeners)listener(this.preloadDone||0,this.preloadTotal||0);};
    if(!this.preloadTask){
      // Cache every theme as well as action variants for subsequent missions.
      const urls=[...new Set(Object.values(this.manifest).flatMap(samples=>samples.map(s=>s.url)))];
      this.preloadDone=0;this.preloadTotal=urls.length;
      this.preloadTask=Promise.all(Array.from({length:4},async()=>{
        while(urls.length){await this.buffer(urls.shift());this.preloadDone++;report();}
      })).finally(()=>{this.preloadTask=null;});
    }
    report();
    try{await this.preloadTask;}finally{this.progressListeners.delete(onProgress);}
  }
  /** Load the sound catalog and current theme ambience. */
  async prepare(state,onProgress=()=>{}){
    this.catalogReady??=this.refreshCatalog();
    const key=`${state.seed}:${state.theme}:${state.status}`;
    if(key===this.sceneKey)return;
    const sameMission=this.sceneSeed===state.seed&&this.sceneTheme===state.theme;this.sceneKey=key;this.sceneSeed=state.seed;this.sceneTheme=state.theme;if(!sameMission||state.status==='loadout')this.stopEffects();this.stopAmbience();this.theme=state.status==='active'?state.theme:null;
    await this.catalogReady;
    if(this.context&&this.enabled){await this.preload(onProgress);this.startAmbience();}else onProgress(1,1);
  }
  /** Choose a playable sample for an audio action. */
  choose(action){
    const all=this.manifest[action]||[],candidates=all.length>1?all.filter(s=>s.url!==this.previous.get(action)):all;
    if(!candidates.length)return null;
    const sample=candidates[Math.floor(Math.random()*candidates.length)];this.previous.set(action,sample.url);return sample;
  }
  /** Return the next available decoded sample for an action. */
  async sample(action){
    await this.catalogReady;
    const chosen=this.choose(action);
    // Try the other variants if one local file is missing or cannot be decoded.
    for(const s of [chosen,...(this.manifest[action]||[]).filter(s=>s!==chosen)]){
      if(!s)continue;const b=await this.buffer(s.url);if(b)return {buffer:b,sample:s};
    }
    return {buffer:this.fallback(action),sample:{placeholder:true}};
  }
  /** Synthesize an oscillator-based fallback for a missing sample. */
  fallback(action){
    if(!this.context)return null;
    const ambient=action.startsWith('ambient_'),b=this.context.createBuffer(1,this.context.sampleRate*(ambient?2:.12),this.context.sampleRate),a=b.getChannelData(0);
    let low=0;for(let i=0;i<a.length;i++){low=.92*low+.08*(Math.random()*2-1);a[i]=low*(ambient?.035:.12)*Math.sin(Math.PI*i/(a.length-1))**2;}
    return b;
  }
  /** Update listener. */
  setListener(state,camera){
    const squad=state.units.filter(u=>u.team==='soldier'&&u.hp>0);if(!squad.length)return;
    const avg=k=>squad.reduce((sum,u)=>sum+u[k],0)/squad.length;
    // Anchor loudness to the squad, not zoom; use camera orientation for stereo.
    this.listener={x:avg('x'),y:avg('y'),z:avg('z'),rightX:camera.matrixWorld.elements[0],rightY:camera.matrixWorld.elements[2]};
  }
  /** Stop effects. */
  stopEffects(){this.effectsVersion=(this.effectsVersion||0)+1;for(const s of [...this.voices])s.stop();this.voices.clear();}
  /** Play the local sound associated with a public game event. */
  async play(e){
    const action=soundAction(e);
    if(!action||!this.enabled||!this.context||document.hidden)return;
    const version=this.effectsVersion||0,{buffer}=await this.sample(action);
    if(!buffer||!this.enabled||version!==(this.effectsVersion||0)||document.hidden)return;
    while(this.voices.size>=24){const first=this.voices.values().next().value;first.stop();this.voices.delete(first);}
    const c=this.context,s=c.createBufferSource(),gain=c.createGain(),pan=c.createStereoPanner();s.buffer=buffer;
    const point=e.type==='shot'?e.origin:e.type==='move'?[e.x,e.y,e.z]:e.point||(e.x!==undefined?[e.x,e.y,e.z]:e.actor?[e.actor.x,e.actor.y,e.actor.z]:null);
    let volume=action.startsWith('blast_')?.92:['face','peek','stance','equip','overwatch','fire_mode'].includes(action)?.28:action==='hurt'?.48:.7;
    if(point){const dx=point[0]-this.listener.x,dy=point[1]-this.listener.y;volume/=1+Math.hypot(dx,dy)*.035;pan.pan.value=Math.max(-.85,Math.min(.85,(dx*this.listener.rightX+dy*this.listener.rightY)/14));}
    gain.gain.value=volume;s.connect(gain).connect(pan).connect(this.master);this.voices.add(s);
    s.onended=()=>{this.voices.delete(s);s.disconnect();gain.disconnect();pan.disconnect();};s.start();
  }
  /** Stop ambience. */
  stopAmbience(){
    this.ambientVersion++;clearTimeout(this.ambientTimer);this.ambientRunning=false;
    for(const s of [...this.ambientVoices])s.stop();this.ambientVoices.clear();
  }
  /** Start ambience. */
  startAmbience(){
    if(this.ambientRunning||!this.theme||!this.enabled||!this.context||document.hidden)return;
    this.ambientRunning=true;const version=this.ambientVersion;
    const next=async()=>{
      const {buffer}=await this.sample('ambient_'+this.theme);
      if(!buffer||version!==this.ambientVersion||!this.enabled||document.hidden)return;
      const c=this.context,s=c.createBufferSource(),g=c.createGain(),pan=c.createStereoPanner(),now=c.currentTime,fade=Math.min(.7,buffer.duration/3),level=.34+Math.random()*.14;
      s.buffer=buffer;s.playbackRate.value=.92+Math.random()*.16;pan.pan.value=(Math.random()-.5)*.45;g.gain.setValueAtTime(0,now);g.gain.linearRampToValueAtTime(level,now+fade);g.gain.setValueAtTime(level,now+buffer.duration/s.playbackRate.value-fade);g.gain.linearRampToValueAtTime(0,now+buffer.duration/s.playbackRate.value);
      s.connect(g).connect(pan).connect(this.master);this.ambientVoices.add(s);s.onended=()=>{this.ambientVoices.delete(s);s.disconnect();g.disconnect();pan.disconnect();};s.start();
      this.ambientTimer=setTimeout(next,Math.max(50,(buffer.duration/s.playbackRate.value-fade*1.5)*1000));
    };next();
  }
}
/** Export the action audio value. */
export const actionAudio=new ActionAudio();
