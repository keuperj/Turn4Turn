import {B} from '../../rendering.js';
import {surfaceBatch,crossingPaint} from '../../surfaces.js';
const trees=['CommonTree_1','CommonTree_3','BirchTree_1','BirchTree_3'];
const shrubs=['Bush_1','BushBerries_1'];
export function background(state,rng){
  const n=state.size,c=(n-1)/2,rx=state.scenery.road_x,cy=state.scenery.cross_y,extent=84,step=n+24;
  const xs=[rx-step,rx,rx+step],zs=[cy-step,cy,cy+step];
  const asphalt=this.material('suburban-asphalt',state.scenery.road,'concrete-weathered-v2.webp',20),paving=this.material('suburban-sidewalk','#c8c6b7','concrete-weathered-v2.webp',20);
  const lawn=this.material('suburban-lawn','#8fa573','terrain-mixed-v2.webp',3),path=this.material('suburban-path','#d2c2a3','concrete-weathered-v2.webp',3);
  const clipped=rect=>{
   const {x,z,w,d}=rect,l=x-w/2,r=x+w/2,t=z-d/2,b=z+d/2,lo=-.5,hi=n-.5,result=[];
   const part=(x0,z0,x1,z1)=>{if(x1>x0&&z1>z0)result.push({x:(x0+x1)/2,z:(z0+z1)/2,w:x1-x0,d:z1-z0});};
   part(l,t,Math.min(r,lo),b);part(Math.max(l,hi),t,r,b);
   part(Math.max(l,lo),t,Math.min(r,hi),Math.min(b,lo));part(Math.max(l,lo),Math.max(t,hi),Math.min(r,hi),b);
   return result;
  };
  const plane=(name,x,z,w,d,mat,y)=>{for(const r of clipped({x,z,w,d}))this.plane(name,r.x,r.z,r.w,r.d,mat,y);};
  for(const x of xs)plane('background-suburban-sidewalk',x,c,16,extent*2,paving,.023);
  for(const z of zs)plane('background-suburban-sidewalk',c,z,extent*2,16,paving,.023);
  for(const x of xs)plane('background-suburban-road',x,c,12,extent*2,asphalt,.025);
  for(const z of zs)plane('background-suburban-road',c,z,extent*2,12,asphalt,.025);
  const white=[],yellow=[];
  // Each crossing contributes paint only within its own block, avoiding overlaps.
  for(const x of xs)for(const z of zs){
   const paint=crossingPaint(x,z,c-extent,c+extent);
   for(const [color,list] of Object.entries(paint))for(const r of list){
    if(Math.abs(r.x-x)>step/2||Math.abs(r.z-z)>step/2)continue;
    (color==='white'?white:yellow).push(...clipped(r));
   }
  }
  surfaceBatch(this.view,this.root,'background-suburban-white-lines',white,{native:this.material('suburban-white','#eee9d7')},.039);
  surfaceBatch(this.view,this.root,'background-suburban-center-lines',yellow,{native:this.material('suburban-yellow','#ecd18c')},.039);
  const outside=(x,z,w,d)=>x+w/2<-.6||z+d/2<-.6||x-w/2>n-.4||z-d/2>n-.4;
  let index=0;
  for(const horizontal of [false,true])for(const road of horizontal?zs:xs)for(const side of [-1,1]){
   for(let along=c-extent+6;along<c+extent-6;along+=12){
    if((horizontal?xs:zs).some(v=>Math.abs(v-along)<16))continue;
    const x=horizontal?along:road+side*14,z=horizontal?road+side*14:along,w=horizontal?11:10,d=horizontal?10:11;
    if(!outside(x,z,w,d))continue;
    this.plane('background-suburban-garden',x,z,w,d,lawn,.005);
    const id=['House','House2','House3'][index%3],angle=horizontal?(side<0?0:Math.PI):(side<0?Math.PI/2:-Math.PI/2);
    this.add(id,x+(horizontal?0:side),z+(horizontal?side:0),.88+rng()*.18,angle,0);
    const px=horizontal?x:road+side*10.5,pz=horizontal?road+side*10.5:z;
    this.plane('background-suburban-garden-path',px,pz,horizontal?.9:5,horizontal?5:.9,path,.015);
    const plant=[...trees,...shrubs][index%6];this.add(plant,x+(horizontal?3.9:-side*2),z+(horizontal?-side*2:3.9),.40+rng()*.12,0,0);
    index++;
   }
  }
  // Static traffic shares the same already-loaded vehicle assets as the board.
  const cars=this.view.transport.models.filter(m=>m.kind==='car').slice(0,3),traffic=new Map();
  for(const horizontal of [false,true])for(const lane of [-4.5,-1.5,1.5,4.5])for(let along=c-extent+8+rng()*17;along<c+extent-8;along+=9+rng()*22){
   if((horizontal?xs:zs).some(v=>Math.abs(along-v)<9))continue;
   const x=horizontal?along:rx+lane,z=horizontal?cy+lane:along;
   if(!outside(x,z,horizontal?5:2,horizontal?2:5))continue;
   const entry=cars[Math.floor(rng()*cars.length)],source=entry&&this.view.transport.sources.get(entry.id);if(!source)continue;
   if(!traffic.has(entry.id))traffic.set(entry.id,[]);
   traffic.get(entry.id).push(B.Matrix.Compose(B.Vector3.One(),B.Quaternion.RotationAxis(B.Axis.Y,(horizontal?Math.PI/2:0)+(lane>0?Math.PI:0)),new B.Vector3(x,0,z)));
  }
  // A model can contain many small parts. Instance each part in one draw instead
  // of creating a full hierarchy for every distant car.
  for(const [id,placements] of traffic)for(const part of this.view.transport.sources.get(id).meshes){
   if(!part.getTotalVertices())continue;
   part.computeWorldMatrix(true);const local=part.getWorldMatrix().clone();
   const mesh=part.clone('background-traffic:'+id,this.root,true);mesh.position.setAll(0);mesh.scaling.setAll(1);mesh.rotation.setAll(0);mesh.rotationQuaternion=B.Quaternion.Identity();
   mesh.makeGeometryUnique();mesh.setEnabled(true);mesh.isVisible=true;mesh.isPickable=false;mesh.receiveShadows=true;mesh.metadata={background:true,vehicle:id};
   const buffer=new Float32Array(placements.length*16);placements.forEach((matrix,i)=>local.multiply(matrix).copyToArray(buffer,i*16));
   mesh.thinInstanceSetBuffer('matrix',buffer,16,true);mesh.thinInstanceRefreshBoundingInfo();
  }
 }
