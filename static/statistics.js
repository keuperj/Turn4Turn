/** Cookie-backed lifetime totals and a bounded recent mission history. */
const NAME='turn4turn_statistics';
export const fields={enemies_killed:'Enemies killed',fighters_killed:'Own fighters killed',civilians_rescued:'Civilians rescued',civilians_killed:'Civilians killed',shots_fired:'Shots fired',shots_hit:'Hits',shots_missed:'Misses',turns:'Turns'};
const keys=Object.keys(fields);
const empty=()=>({v:1,count:0,wins:0,totals:keys.map(()=>0),history:[]});
const cookie=name=>document.cookie.split('; ').find(c=>c.startsWith(name+'='))?.slice(name.length+1);
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const counts=a=>Array.isArray(a)&&a.length===keys.length&&a.every(n=>Number.isSafeInteger(n)&&n>=0);
/** Read the versioned cookie, falling back safely when it is malformed. */
export function loadStatistics(){
  try{
    const s=JSON.parse(decodeURIComponent(cookie(NAME)||''));
    if(s.v!==1||!Number.isSafeInteger(s.count)||s.count<0||!Number.isSafeInteger(s.wins)||s.wins<0||s.wins>s.count||!counts(s.totals)||!Array.isArray(s.history)||!s.history.every(r=>Array.isArray(r)&&r.length===7&&typeof r[0]==='string'&&Number.isFinite(r[1])&&typeof r[2]==='string'&&typeof r[3]==='string'&&typeof r[4]==='string'&&['victory','defeat'].includes(r[5])&&counts(r[6])))return empty();
    return s;
  }catch{return empty();}
}
let saveFailed=false;
/** Add each completed attempt once and retain totals when history is trimmed. */
export function recordMission(state){
  if(state.tutorial||!state.summary||!['victory','defeat'].includes(state.status)||!cookie('turn4turn_name'))return;
  const s=loadStatistics(),id=state.summary.id;
  if(s.history.some(r=>r[0]===id))return;
  const values=keys.map(k=>state.summary[k]);
  if(!counts(values))return;
  s.count++;s.wins+=Number(state.status==='victory');s.totals=s.totals.map((n,i)=>n+values[i]);
  s.history.unshift([id,Date.now(),state.mission.label,state.theme,state.difficulty,state.status,values]);
  s.history=s.history.slice(0,20);
  let encoded=encodeURIComponent(JSON.stringify(s));
  while(encoded.length>3700&&s.history.length>1){s.history.pop();encoded=encodeURIComponent(JSON.stringify(s));}
  document.cookie=`${NAME}=${encoded}; Path=/; Max-Age=31536000; SameSite=Lax`;
  saveFailed=cookie(NAME)!==encoded;
}
/** Render the shared mission and lifetime counter grid. */
export function statisticsMarkup(values){
  if(!values)return '';
  return `<dl class="statistics-grid">${keys.map(k=>`<div><dt>${fields[k]}</dt><dd>${Number(values[k])||0}</dd></div>`).join('')}</dl><p class="small-note">Shots count squad firearm rounds, including bursts and overwatch. Hits include units and structures; empty-ground shots are misses. Explosives and utility items are excluded. Turns count rounds entered.</p>`;
}
/** Open the service record without loading a mission or renderer. */
export function showStatistics(){
  const s=loadStatistics();
  let name='No player profile yet';try{name=decodeURIComponent(cookie('turn4turn_name')||'')||name;}catch{}
  document.getElementById('statistics-name').textContent=name;
  document.getElementById('statistics-content').innerHTML=`<p>${s.count} missions completed · ${s.wins} victories · ${s.count-s.wins} defeats</p>${statisticsMarkup(Object.fromEntries(keys.map((k,i)=>[k,s.totals[i]])))}<h2>Mission history</h2><p class="small-note">Lifetime totals and up to 20 recent missions are saved in this browser’s cookie for one year after your latest completed mission. Older history is trimmed to fit the cookie; totals remain. Clearing cookies clears this record. Abandoned missions are excluded.</p>${saveFailed?'<p role="alert">The browser could not save the latest mission statistics. Please allow cookies.</p>':''}${s.history.length?`<div class="history-scroll" tabindex="0" aria-label="Mission history"><table class="history-table"><thead><tr><th>Completed</th><th>Mission</th><th>Result</th>${keys.map(k=>`<th>${fields[k]}</th>`).join('')}</tr></thead><tbody>${s.history.map(r=>`<tr><td>${escape(new Date(r[1]).toLocaleString())}</td><td>${escape(r[2])}<small>${escape(r[3])} · ${escape(r[4])}</small></td><td>${r[5]==='victory'?'Victory':'Defeat'}</td>${r[6].map(n=>`<td>${n}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<p>Complete your first mission to begin your service record.</p>'}`;
  document.getElementById('landing').hidden=true;
  document.getElementById('statistics-screen').hidden=false;
}
