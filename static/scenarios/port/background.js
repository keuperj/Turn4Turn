/** The harbour continues offshore; warehouses and cranes occupy the land side. */
import {B} from '../../rendering.js';
import {surfaceBatch} from '../../surfaces.js';
import {placeModel} from './scene.js';

/** Build static industrial silhouettes on the same coordinate system as the quay. */
export function background(state,rng){
 const n=state.size,s=state.scenery.shore_y,c=(n-1)/2;
 const water=this.material('port-water','#245d69');water.roughness=.28;water.metallic=.25;
 const sea=this.view.nativeScene.getMeshByName('background-ground');sea.material=water;
 this.plane('background-port-land',c,(s-.5+450)/2,900,450-s+.5,this.material('port-land','#8b9795','concrete-weathered-v2.webp',60),-.03);
 this.plane('background-port-road',c,s+1.5,900,2,this.material('port-road','#525f64','concrete-weathered-v2.webp',60),-.015);
 const mat=this.material('port-ripples','#447d86');mat.alpha=.35;const ripples=[];
 for(let i=0;i<100;i++){
   const x=c+(rng()-.5)*160,z=s-2-rng()*100;
   ripples.push({x,z,w:1+rng()*4,d:.03+rng()*.05});
 }
 surfaceBatch(this.view,this.root,'port-water-ripples',ripples,{native:mat},-.19);
 const vessel=(id,x,z,scale,angle)=>{placeModel(this.view,this.root,id,x,-.2-.35*scale,z,scale,angle);this.placements.push({id,x,z,scale,angle});};
 for(let i=0;i<8;i++)vessel(i%3===0?'PortTender':i%2?'PortCruiser':'PortCruiserNavy',c-36+i*11,-9-(i%3)*14,1+rng()*.55,rng()*Math.PI*2);
 for(const x of [-8,n+8]){vessel('PortCruiserNavy',x,s-7,1,0);placeModel(this.view,this.root,'PortBuoy',x,-.65,-3,.65);}
 const box=(name,x,y,z,w,h,d,color)=>{
   const mesh=B.MeshBuilder.CreateBox(name,{width:w,height:h,depth:d},this.view.nativeScene);mesh.parent=this.root;mesh.position.set(x,y,z);
   mesh.material=this.material(name+color,color);mesh.isPickable=false;mesh.receiveShadows=true;mesh.metadata={background:true,industrial:true};return mesh;
 };
 const warehouse=(x,z,index)=>{
   const w=8+rng()*4,d=7+rng()*3,h=4+rng()*2;
   box('port-warehouse',x,h/2,z,w,h,d,index%2?'#829396':'#a5aaa0');
   box('port-industrial-roof',x,h+.2,z,w+.5,.4,d+.5,'#465d68');
   for(let i=-1;i<=1;i++)box('port-loading-door',x+i*w*.27,1.4,z-d/2-.03,1.6,2.8,.1,'#344953');
   for(let i=0;i<3;i++)box('port-roof-vent',x-w*.3+i*w*.3,h+.6,z,.8,.8,1.2,'#b7c0bb');
   if(index%2===0){const chimney=B.MeshBuilder.CreateCylinder('port-industry-stack',{height:9,diameter:.8,tessellation:10},this.view.nativeScene);chimney.parent=this.root;chimney.position.set(x+w/2-1,4.5,z+d/2-1);chimney.material=this.material('port-stack','#796f63');chimney.isPickable=false;chimney.metadata={background:true,industrial:true};}
 };
 for(let row=0;row<2;row++)for(let col=-2;col<=3;col++)warehouse(c+col*16,n+10+row*18,row*6+col+2);
 for(const x of [-13,n+13]){
   warehouse(x,s+10,1);
   placeModel(this.view,this.root,'PortHoist',x,-.03,s+2,1.1);
   placeModel(this.view,this.root,'PortCrane',x+6,-.03,s,1.2,Math.PI/2);
   for(let i=0;i<3;i++)box('port-cargo-container',x+6,.85,s+8+i*2.5,4,1.7,2,i%2?'#987651':'#487781');
 }
}
