/** Rotating equipment cards use the server's authoritative weapon statistics. */
const descriptions={
 'M4A1':'A versatile rifle for advancing with the squad. Choose single shots or automatic fire.',
 'HK416':'An accurate assault rifle with automatic fire for close engagements.',
 'M110':'A marksman rifle with extra reach for covering an advance.',
 'M249':'A support weapon with a larger magazine and automatic fire.',
 'M9':'A compact sidearm. Firing costs one action point.',
 'RPG-7':'An explosive rocket for clustered targets and structures. Keep friendlies clear.',
 'Frag grenade':'An area weapon for enemies behind cover. Watch the blast radius.',
 'M24 sniper':'Long-range precision. A shot requires two action points.',
 'Smoke grenade':'Blocks sight for both sides for three hostile phases. Cover a crossing or withdrawal.',
 'Demolition charge':'Plant nearby, then withdraw. Detonates after two hostile phases.',
 'Shotgun':'High damage at short range. Close the distance using cover.',
 'Medikit':'Treat an adjacent wounded teammate for one action point. Cannot revive fallen fighters.'
};
// Alternate firearms and support items so short waits still offer variety.
const order=['M4A1','Medikit','M24 sniper','Smoke grenade','Shotgun','Frag grenade','HK416','Demolition charge','M110','RPG-7','M249','M9'];
export class LoadingGuide {
 constructor(element,art,images){this.element=element;this.art=art;this.images=images;this.readyImages=new Map();this.index=0;}
 /** Decode the preview artwork before allowing large mission downloads. */
 preload(){
  if(this.preloadTask)return this.preloadTask;
  this.preloadTask=Promise.all([...new Set(Object.values(this.images))].map(async url=>{
   if(this.readyImages.has(url))return;
   const image=new Image();image.fetchPriority='high';image.src=url;
   try{await image.decode();this.readyImages.set(url,image);if(this.weapons)this.start(this.weapons);}
   catch(error){console.warn('Equipment preview unavailable:',url,error);}
  })).finally(()=>{this.preloadTask=null;});
  return this.preloadTask;
 }
 start(weapons){
  if(!weapons)return;
  this.weapons=weapons;
  if(this.timer||!Object.keys(weapons).some(name=>this.readyImages.has(this.images[name])))return;
  this.show();this.timer=setInterval(()=>{this.index++;this.show();},4500);
 }
 show(){
  const names=order.filter(name=>this.weapons[name]&&this.readyImages.has(this.images[name])),name=names[this.index%names.length];
  if(!name)return;
  const w=this.weapons[name],facts=[['Range',`${w.range} tiles`]];
  if(w.heal)facts.push(['Healing',`+${w.heal} HP`]);
  else if(w.damage)facts.push(['Damage',`${w.damage}`]);
  else facts.push(['Effect','Sight screen']);
  facts.push(['Capacity',`${w.capacity} ${['medical','grenade','smoke','charge'].includes(w.kind)?'uses':'rounds'}`]);
  if(w.radius)facts.push(['Radius',`${w.radius} tiles`]);
  else if(w.automatic)facts.push(['Fire modes','Single / auto']);
  else if(w.kind==='sniper')facts.push(['Shot cost','2 AP']);
  this.element.hidden=false;this.element.dataset.item=name;
  this.element.innerHTML=`<div class="loading-guide-label">FIELD GUIDE <span>${this.index%names.length+1} / ${names.length}</span></div><div class="loading-item">${this.art(name)}<h3>${name}</h3><p>${descriptions[name]}</p><dl>${facts.map(([key,value])=>`<div><dt>${key}</dt><dd>${value}</dd></div>`).join('')}</dl></div>`;
 }
 stop(){clearInterval(this.timer);this.timer=null;this.element.hidden=true;}
}
