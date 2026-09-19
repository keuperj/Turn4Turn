import {B} from '../../rendering.js';
const trees=['CommonTree_1','CommonTree_3','BirchTree_1','BirchTree_3'];
const shrubs=['Bush_1','BushBerries_1'];
export function background(state,rng){
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
