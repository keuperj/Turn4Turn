// Local synthesized action effects. No music, downloads or external audio service.
export class ActionAudio {
  constructor(){this.enabled=localStorage.getItem('sound')!=='off';this.volume=Number(localStorage.getItem('volume')||.35);this.context=null;this.lastStep=0;}
  async unlock(){if(!this.enabled)return;try{this.context??=new (window.AudioContext||window.webkitAudioContext)();await this.context.resume();}catch{this.enabled=false;}}
  setEnabled(value){this.enabled=value;localStorage.setItem('sound',value?'on':'off');if(value)this.unlock();}
  setVolume(value){this.volume=Number(value);localStorage.setItem('volume',this.volume);}
  noise(duration,gain,lowpass=1500,delay=0){const c=this.context;if(!c||c.state!=='running')return;const n=Math.ceil(c.sampleRate*duration),b=c.createBuffer(1,n,c.sampleRate),d=b.getChannelData(0);for(let i=0;i<n;i++)d[i]=(Math.random()*2-1)*Math.exp(-i/n*5);const s=c.createBufferSource(),f=c.createBiquadFilter(),g=c.createGain();s.buffer=b;f.type='lowpass';f.frequency.value=lowpass;g.gain.value=gain*this.volume;s.connect(f).connect(g).connect(c.destination);s.start(c.currentTime+delay);s.onended=()=>{s.disconnect();f.disconnect();g.disconnect();};}
  tone(frequency,duration,gain,delay=0){const c=this.context;if(!c||c.state!=='running')return;const o=c.createOscillator(),g=c.createGain();o.type='triangle';o.frequency.setValueAtTime(frequency,c.currentTime+delay);o.frequency.exponentialRampToValueAtTime(Math.max(30,frequency*.35),c.currentTime+delay+duration);g.gain.setValueAtTime(gain*this.volume,c.currentTime+delay);g.gain.exponentialRampToValueAtTime(.0001,c.currentTime+delay+duration);o.connect(g).connect(c.destination);o.start(c.currentTime+delay);o.stop(c.currentTime+delay+duration);o.onended=()=>{o.disconnect();g.disconnect();};}
  scream(){const c=this.context;if(!c||c.state!=='running')return;const o=c.createOscillator(),f=c.createBiquadFilter(),g=c.createGain();o.type='sawtooth';const base=240+Math.random()*110;o.frequency.setValueAtTime(base,c.currentTime);o.frequency.linearRampToValueAtTime(base*1.8,c.currentTime+.08);o.frequency.exponentialRampToValueAtTime(base*.65,c.currentTime+.48);f.type='bandpass';f.frequency.value=1100;f.Q.value=2;g.gain.setValueAtTime(.001,c.currentTime);g.gain.linearRampToValueAtTime(this.volume*.25,c.currentTime+.035);g.gain.exponentialRampToValueAtTime(.001,c.currentTime+.5);o.connect(f).connect(g).connect(c.destination);o.start();o.stop(c.currentTime+.52);o.onended=()=>{o.disconnect();f.disconnect();g.disconnect();};this.noise(.25,.12,1800);}
  play(event){if(!this.enabled||!this.context)return;const t=event.type;
    if(t==='move'){if(performance.now()-this.lastStep<100)return;this.lastStep=performance.now();this.noise(.08,.3,450);this.noise(.07,.2,600,.10);}
    if(t==='shot'){const profiles={'Shotgun':[.38,1,1600,60],'M9':[.12,.52,4300,180],'M4A1':[.19,.8,3300,100],'HK416':[.17,.82,3800,115],'M110':[.30,.95,2600,75],'M24 sniper':[.48,1,2100,55],'M249':[.23,.9,2900,90],'Alien carbine':[.2,.75,5500,290]};const [d,g,f,b]=profiles[event.weapon]||profiles.M4A1;this.noise(d,g,f);this.tone(b,d,.6);this.noise(.06,.17,6000,d);}
    if(t==='heal'){this.noise(.15,.15,1700);this.tone(520,.15,.15);this.tone(680,.17,.13,.15);}
    if(t==='hurt'){this.scream();}
    if(t==='smoke'){this.noise(1.1,.4,4800);this.tone(130,.1,.2);}
    if(t==='impact'){this.noise(.14,.5,1800);this.tone(210,.08,.25);}
    if(t==='blast'){this.noise(.85,1.1,950);this.tone(65,.7,.8);this.noise(.5,.5,1800,.15);}
    if(t==='portal'){this.tone(180,.17,.13);this.noise(.10,.4,600,.13);}
    if(t==='reload'){this.noise(.09,.32,4000);this.noise(.10,.38,3000,.20);this.tone(400,.05,.12,.28);}
  }
}
export const actionAudio=new ActionAudio();
