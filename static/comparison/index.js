/** @fileoverview Control the isolated renderer-comparison user interface. */
const $=id=>document.getElementById(id),frame=$('view');let engine=new URLSearchParams(location.search).get('engine')==='webgpu'?'webgpu':'babylon',ready=false,records={};
const state={preset:'hero',cutaway:'exterior',motion:'walk',paused:false,orbit:null};
/** Post a command to the active comparison frame. */
function send(type,extra={}){if(ready)frame.contentWindow.postMessage({type,...extra},location.origin);}
/** Load the selected renderer in the comparison frame. */
function switchEngine(name){engine=name;ready=false;$('status').hidden=false;$('status').textContent='Loading shared scene…';$('timing').textContent='Warming up…';$('startup').textContent='—';$('resolution').textContent='—';$('engineLabel').textContent=name==='three'?'THREE.JS':name.toUpperCase();document.querySelectorAll('[data-engine]').forEach(b=>b.classList.toggle('active',b.dataset.engine===name));frame.src=`view.html?engine=${name}`;}
document.querySelectorAll('[data-engine]').forEach(b=>b.onclick=()=>switchEngine(b.dataset.engine));
for(const key of ['preset','cutaway','motion'])$(key).onchange=()=>{state[key]=$(key).value;if(key==='preset')state.orbit=null;send('state',{state});};
$('pause').onclick=()=>{state.paused=!state.paused;$('pause').textContent=state.paused?'Resume':'Pause';send('state',{state});};
$('reset').onclick=()=>{state.orbit=null;send('reset',{state});};
for(const effect of ['smoke','explosion'])$(effect).onclick=()=>send('effect',{effect});
/** Download captured comparison data with the requested filename. */
function save(data,name){const a=document.createElement('a');a.href=data;a.download=name;a.click();}
$('capture').onclick=()=>send('capture');$('report').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({date:new Date().toISOString(),userAgent:navigator.userAgent,notes:'Frame intervals include browser scheduling; not GPU timings. Engine lighting is not numerically equivalent.',records},null,2)],{type:'application/json'}));save(url,'engine-comparison.json');setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('message',e=>{if(e.origin!==location.origin||e.source!==frame.contentWindow)return;const d=e.data;if(d.type==='ready'){ready=true;$('status').hidden=true;$('startup').textContent=`${(d.ms/1000).toFixed(2)} s`;send('state',{state});}if(d.type==='error'){$('status').hidden=false;$('status').textContent=`Renderer could not start: ${d.message}`;}if(d.type==='orbit')state.orbit=d.orbit;if(d.type==='metrics'){$('timing').textContent=`${d.median.toFixed(1)} / ${d.p95.toFixed(1)} ms`;$('resolution').textContent=`${d.width} × ${d.height}`;records[engine]={...d,backend:d.backend,quality:d.quality,state:structuredClone(state)};}if(d.type==='capture')save(d.data,`${engine}-${state.preset}.png`);});switchEngine(engine);
