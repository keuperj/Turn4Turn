/** Batched suburban pavements and four-lane intersection paint. */
import * as G from './rendering.js';

/** One mesh per finish keeps hundreds of road stripes cheap to render and update. */
export function surfaceBatch(view,parent,name,rectangles,material,height=.034){
 if(!rectangles.length)return;
 const positions=[],indices=[],normals=[],uvs=[];
 for(const {x,z,w,d} of rectangles){const i=positions.length/3;
  positions.push(x-w/2,height,z-d/2,x+w/2,height,z-d/2,x+w/2,height,z+d/2,x-w/2,height,z+d/2);
  normals.push(0,1,0,0,1,0,0,1,0,0,1,0);uvs.push(0,0,1,0,1,1,0,1);indices.push(i,i+1,i+2,i,i+2,i+3);
 }
 const mesh=new G.B.Mesh(name,view.nativeScene),data=new G.B.VertexData();Object.assign(data,{positions,indices,normals,uvs});data.applyToMesh(mesh);
 const owner=new G.Group(mesh);owner.isMesh=true;owner.material=material;mesh.material=material.native;mesh.isPickable=false;mesh.receiveShadows=true;
 if(parent.native)parent.add(owner);else{mesh.parent=parent;mesh.metadata={background:true};}
 return owner;
}

/** Shared paint coordinates keep the map and background roads aligned. */
export function crossingPaint(rx,cy,start,end){
 const white=[],yellow=[];
 for(let i=Math.ceil(start);i<end;i++){
  if(Math.abs(i-cy)>6.5){
   for(const side of [-1,1])yellow.push({x:rx+side*.13,z:i,w:.09,d:1});
   if(i%3===0)for(const side of [-1,1])white.push({x:rx+side*3,z:i,w:.10,d:1.5});
  }
  if(Math.abs(i-rx)>6.5){
   for(const side of [-1,1])yellow.push({x:i,z:cy+side*.13,w:1,d:.09});
   if(i%3===0)for(const side of [-1,1])white.push({x:i,z:cy+side*3,w:1.5,d:.10});
  }
 }
 for(const side of [-1,1]){
  for(let i=-5.5;i<6;i++){
   white.push({x:rx+i,z:cy+side*5,w:.52,d:1.2},{x:rx+side*5,z:cy+i,w:1.2,d:.52});
  }
  white.push({x:rx-side*3,z:cy+side*6.6,w:5.8,d:.16},{x:rx+side*6.6,z:cy+side*3,w:.16,d:5.8});
 }
 return {white,yellow};
}

