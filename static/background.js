/** Seeded decorative scenery outside the tactical grid, shared by both renderers. */
import {B} from './rendering.js';
const trees=['CommonTree_1','CommonTree_3','BirchTree_1','BirchTree_3'];
const shrubs=['Bush_1','BushBerries_1'];
export const backgroundProfiles={
 urban:{color:'#9b9a8c',sky:'#9aaeb8',texture:'concrete-weathered-v2.webp',buildings:['Flat','Flat2','Shop','House3'],buildCount:32,plantCount:32},
 streets:{color:'#a29e8c',sky:'#a3b2b5',texture:'concrete-weathered-v2.webp',buildings:['House','House2','House3','Shop','Flat'],buildCount:28,plantCount:40},
 factory:{color:'#777b76',sky:'#9ca9aa',texture:'concrete-weathered-v2.webp',buildings:['OpenBarn','BigBarn','WaterTower','Silo','Flat'],buildCount:24,plantCount:16},
 train_station:{color:'#958a75',sky:'#a8afa9',texture:'concrete-weathered-v2.webp',buildings:['Shop','OpenBarn','WaterTower','Flat','House2'],buildCount:24,plantCount:24},
 airport:{color:'#9ca7a0',sky:'#a7bbc2',texture:'concrete-weathered-v2.webp',buildings:['OpenBarn','BigBarn','Flat2','WaterTower','Shop'],buildCount:16,plantCount:20},
 woods:{color:'#81916a',sky:'#96a89b',texture:'terrain-mixed-v2.webp',buildings:['SmallBarn','House','OpenBarn'],buildCount:4,plantCount:112},
 farm:{color:'#b3a47b',sky:'#b7b8a6',texture:'terrain-mixed-v2.webp',buildings:['Barn','BigBarn','SmallBarn','Silo','Windmill','House2'],buildCount:20,plantCount:48},
};
function randomFor(seed){let value=(Number(seed)||1)>>>0;return ()=>{value=(Math.imul(value,1664525)+1013904223)>>>0;return value/4294967296;};}
export class BackgroundAssets {
 constructor(view){this.view=view;this.sources=new Map();this.materials=new Map();this.failures=[];}
 async load(){
  try{
   const response=await fetch('/assets/models/background/manifest.json');if(!response.ok)throw Error('Background catalog unavailable');
   this.catalog=(await response.json()).models;
   await Promise.all(this.catalog.map(async entry=>{
    try{const container=await B.SceneLoader.LoadAssetContainerAsync('/assets/models/background/',entry.file,this.view.nativeScene);this.sources.set(entry.id,container);}
    catch(error){this.failures.push(entry.id);console.warn('Background asset unavailable:',entry.id,error);}
   }));
  }catch(error){this.failures.push('manifest');console.warn(error);}
 }
 material(key,color,texture,repeat=1){
  if(this.materials.has(key))return this.materials.get(key);
  const mat=new B.PBRMaterial('background-'+key,this.view.nativeScene);mat.albedoColor=B.Color3.FromHexString(color).toLinearSpace();mat.roughness=1;mat.metallic=0;
  if(texture){mat.albedoTexture=new B.Texture('/assets/'+texture,this.view.nativeScene,false,false);mat.albedoTexture.uScale=mat.albedoTexture.vScale=repeat;mat.albedoTexture.wrapU=mat.albedoTexture.wrapV=B.Texture.WRAP_ADDRESSMODE;mat.albedoTexture.anisotropicFilteringLevel=4;}
  this.materials.set(key,mat);return mat;
 }
 plane(name,x,z,width,depth,material,y=-.61){
  const mesh=B.MeshBuilder.CreateGround(name,{width,height:depth},this.view.nativeScene);mesh.parent=this.root;mesh.position.set(x,y,z);mesh.material=material;mesh.isPickable=false;mesh.receiveShadows=true;mesh.metadata={background:true};return mesh;
 }
 add(id,x,z,scale,angle,ground=-.6){
  const container=this.sources.get(id);if(!container)return;
  const instance=container.instantiateModelsToScene(name=>'background:'+id+':'+name,false,{doNotInstantiate:false});
  for(const root of instance.rootNodes){root.parent=this.root;root.position.addInPlace(new B.Vector3(x,ground,z));root.scaling.scaleInPlace(scale);root.rotationQuaternion=B.Quaternion.RotationAxis(B.Axis.Y,angle);
   for(const mesh of [root,...root.getChildMeshes()]){mesh.isPickable=false;mesh.receiveShadows=true;mesh.metadata={background:true,asset:id};}
  }
  this.placements.push({id,x,z,scale,angle});
 }
 sync(state){
  this.state=state;this.atmosphere();
  const key=[state.seed,state.theme,state.size].join(':');if(key===this.key)return;
  this.key=key;this.root?.dispose(false,false);this.placements=[];
  this.root=new B.TransformNode('scenario-background-'+state.theme,this.view.nativeScene);
  const p=backgroundProfiles[state.theme]||backgroundProfiles.urban,n=state.size,c=(n-1)/2,rng=randomFor(state.seed+state.theme.length*797);
  this.plane('background-ground',c,c,900,900,this.material(state.theme+'-ground',p.color,p.texture,90),state.theme==='urban'?-.025:-.64);
  if(state.theme==='urban'){this.urban(state,rng);return;}
  const road=this.material(state.theme+'-road',['farm','woods'].includes(state.theme)?'#8d7958':'#525b5b','concrete-weathered-v2.webp',12);
  // A clear perimeter separates the board from the scenery and stays unobstructed.
  if(!['woods','farm'].includes(state.theme))for(const side of [-1,1]){
   const edge=c+side*(n/2+4);this.plane('background-service-road',c,edge,n+16,3.8,road);this.plane('background-service-road',edge,c,3.8,n+16,road);
  }
  if(state.theme==='airport'){
   this.plane('background-runway',c,-28,n+95,10,road,-.59);
   const paint=this.material('runway-marking','#cbc6a7');for(let x=-35;x<n+40;x+=10)this.plane('background-runway-stripe',x,-28,4,.22,paint,-.57);
  }
  if(state.theme==='train_station'){
   const ballast=this.material('rail-ballast','#756f62','concrete-weathered-v2.webp',18),steel=this.material('rails','#414a49');
   this.plane('background-rail-yard',c,-25,n+100,10,ballast,-.59);
   for(const z of [-28,-26.8,-23,-21.8])this.plane('background-rail',c,z,n+100,.10,steel,-.57);
  }
  if(state.theme==='farm'){
   const earth=this.material('furrow-soil','#79603f','terrain-mixed-v2.webp',8),crop=this.material('crop-rows','#a2a064','terrain-mixed-v2.webp',8);
   for(const side of [-1,1])for(let row=0;row<18;row++)this.plane('background-crop-row',c,c+side*(n/2+8+row*1.2),n+26,.9,row%3?crop:earth,-.60);
  }
  // Buildings sit on three staggered rings, beyond the roads/fields. Spacing
  // uses the largest model footprint so nothing crosses into playable tiles.
  for(let i=0;i<p.buildCount;i++){
   const side=i%4,ring=Math.floor(i/4)%3,along=-8+(Math.floor(i/12)+.5)*(n+16)/Math.ceil(p.buildCount/12)+(rng()-.5)*2;
   const offset=17+ring*21+(state.theme==='farm'?14:state.theme==='airport'?26:state.theme==='train_station'?25:0),edge=side<2?-offset:n-1+offset;
   const x=side%2===0?along:edge,z=side%2===0?edge:along;
   this.add(p.buildings[(i%4+Math.floor(i/4))%p.buildings.length],x,z,.82+rng()*.28,side%2===0?(side===0?0:Math.PI):(side===1?Math.PI/2:-Math.PI/2));
  }
  for(let i=0;i<p.plantCount;i++){
   const side=i%4,ring=Math.floor(i/4)%3,offset=8+ring*19+rng()*6,along=-8+rng()*(n+16),edge=side<2?-offset:n-1+offset;
   let x=side%2===0?along:edge,z=side%2===0?edge:along;
   // Keep the airport runway and rail tracks open.
   if(['airport','train_station'].includes(state.theme)&&z<0){x=n+12+ring*10;z=along;}
   const list=i%3===0?shrubs:trees;this.add(list[Math.floor(i/3)%list.length],x,z,.7+rng()*.55,rng()*Math.PI*2);
  }
 }
 urban(state,rng){
  const n=state.size,c=(n-1)/2,rx=state.scenery.road_x,cy=state.scenery.cross_y,step=n+14,extent=76;
  const asphalt=this.material('urban-asphalt',state.scenery.road,'concrete-weathered-v2.webp',18),paving=this.material('urban-paving','#c6c4b5','concrete-weathered-v2.webp',18),paint=this.material('urban-road-paint','#e8d195');
  // Clip every street surface to the outside of the playable square. Matching
  // height, width and centerlines make the four exits continuous with the board.
  const outside=(name,x,z,w,d,mat,y)=>{
   const l=x-w/2,r=x+w/2,t=z-d/2,b=z+d/2,lo=-.5,hi=n-.5;
   const rect=(x0,z0,x1,z1)=>{if(x1>x0&&z1>z0)this.plane(name,(x0+x1)/2,(z0+z1)/2,x1-x0,z1-z0,mat,y);};
   rect(l,t,Math.min(r,lo),b);rect(Math.max(l,hi),t,r,b);
   rect(Math.max(l,lo),t,Math.min(r,hi),Math.min(b,lo));rect(Math.max(l,lo),Math.max(t,hi),Math.min(r,hi),b);
  };
  const xs=[rx-step,rx,rx+step],zs=[cy-step,cy,cy+step];
  for(const x of xs)outside('background-city-sidewalk',x,c,9,extent*2,paving,.021);
  for(const z of zs)outside('background-city-sidewalk',c,z,extent*2,9,paving,.021);
  for(const x of xs)outside('background-road-extension',x,c,5,extent*2,asphalt,.026);
  for(const z of zs)outside('background-road-extension',c,z,extent*2,5,asphalt,.026);
  for(let i=Math.ceil(c-extent);i<c+extent;i+=3){
   for(const x of xs)if(zs.every(z=>Math.abs(z-i)>4))outside('background-lane-mark',x,i,.1,1.4,paint,.041);
   for(const z of zs)if(xs.every(x=>Math.abs(x-i)>4))outside('background-lane-mark',i,z,1.4,.1,paint,.041);
  }
  for(const x of xs)for(const z of zs)for(const side of [-1,1])for(let stripe=-2;stripe<=2;stripe++){
   outside('background-crosswalk',x+stripe*.85,z+side*3.45,.52,1.05,paint,.042);
   outside('background-crosswalk',x+side*3.45,z+stripe*.85,1.05,.52,paint,.042);
  }
  // Repeated facade parts share geometry/materials through thin instances.
  const batches=new Map();
  const box=(color,w,h,d,x,y,z)=>{
   if(!batches.has(color))batches.set(color,[]);
   batches.get(color).push(B.Matrix.Compose(new B.Vector3(w,h,d),B.Quaternion.Identity(),new B.Vector3(x,y,z)));
  };
  let index=0;
  for(let x=c-65;x<=c+65;x+=10)for(let z=c-65;z<=c+65;z+=10){
   if(x+4>-.8&&x-4<n+.3&&z+4>-.8&&z-4<n+.3)continue;
   if(xs.some(v=>Math.abs(x-v)<8.5)||zs.some(v=>Math.abs(z-v)<8.5))continue;
   const h=9+Math.floor(rng()*6)*3,w=6.5+rng(),d=6.5+rng(),color=['#a49b8d','#aab2af','#917b6f','#7e9199'][index%4];
   if(index%9===0){
    const id=['Flat','Flat2','Shop','House3'][Math.floor(index/9)%4],entry=this.catalog.find(e=>e.id===id);
    const scale=Math.min(7/entry.dimensions[0],7/entry.dimensions[2],1.4);
    this.add(id,x,z,scale,0,0);
   }else{
    box(color,w,h,d,x,h/2,z);box('#cbc6b8',w+.18,.22,d+.18,x,h+.11,z);
    box('#536366',1.5,.7,1.4,x+1,h+.35,z);
    for(let y=1.7;y<h-1;y+=3){
     for(const off of [-2.3,0,2.3])for(const side of [-1,1]){
      box('#344e59',1.18,1.55,.035,x+off,y,z+side*(d/2+.02));
      box('#344e59',.035,1.55,1.18,x+side*(w/2+.02),y,z+off);
     }
     box('#c2b9a6',w+.06,.12,d+.06,x,y+1.22,z);
    }
    if(index%3===0){box('#456f68',w*.8,.24,.9,x,2.6,z+d/2+.2);box('#d9ca9b',w*.7,.32,.05,x,2.97,z+d/2+.03);}
   }
   // Small planted forecourts sit between buildings, never in road lanes.
   if(index<6)this.add([...trees,...shrubs][index],x+4.1,z,.48,0,0);
   index++;
  }
  for(const [color,matrices] of batches){
   const mesh=B.MeshBuilder.CreateBox('background-city-facade',{size:1},this.view.nativeScene);mesh.parent=this.root;
   mesh.material=this.material('city-'+color,color);mesh.isPickable=false;mesh.receiveShadows=true;mesh.metadata={background:true};
   const buffer=new Float32Array(matrices.length*16);matrices.forEach((m,i)=>m.copyToArray(buffer,i*16));mesh.thinInstanceSetBuffer('matrix',buffer,16,true);mesh.thinInstanceRefreshBoundingInfo();
  }
 }
 atmosphere(){
  if(!this.state)return;
  const scene=this.view.nativeScene,p=backgroundProfiles[this.state.theme]||backgroundProfiles.urban,night=this.state.lighting==='night';
  const color=B.Color3.FromHexString(night?'#101b29':p.sky);scene.fogColor=color;scene.clearColor=new B.Color4(color.r,color.g,color.b,1);scene.fogMode=B.Scene.FOGMODE_LINEAR;
  // Move the clear zone with zoom: soften the distant surround without hiding
  // the tactical board when the camera is pulled back to a full-map view.
  const distance=B.Vector3.Distance(this.view.camera.native.position,this.view.controls.target);
  scene.fogStart=Math.max(30,distance+this.state.size*.35);scene.fogEnd=scene.fogStart+(night?50:75);
 }
}
