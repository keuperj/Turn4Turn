/** Detailed vegetation and deterministic textured effects, exclusively for WebGPU. */
import {qualityMaterials} from './webgpu-quality.js';
const B=window.BABYLON,cache=new WeakMap();
export function smokeCanvas(){
 const c=document.createElement('canvas');c.width=c.height=256;const ctx=c.getContext('2d');
 for(let i=0;i<85;i++){const a=i*2.39996,r=Math.sqrt((i%29)/29)*64,x=128+Math.cos(a)*r,y=128+Math.sin(a)*r,s=25+(i%7)*6,g=ctx.createRadialGradient(x,y,0,x,y,s);const v=160+i%5*17;g.addColorStop(0,`rgba(${v},${v+3},${v+5},.13)`);g.addColorStop(.5,`rgba(${v-20},${v-17},${v-15},.08)`);g.addColorStop(1,'rgba(90,94,99,0)');ctx.fillStyle=g;ctx.fillRect(x-s,y-s,s*2,s*2);}
 return c;
}
function natureMaterials(scene){
 if(cache.has(scene))return cache.get(scene);
 const bark=new B.PBRMaterial('textured-bark',scene);bark.albedoTexture=qualityMaterials(scene).bark;bark.roughness=1;bark.metallic=0;bark.bumpTexture=qualityMaterials(scene).normal;
 const c=document.createElement('canvas');c.width=c.height=128;const ctx=c.getContext('2d');
 for(let i=0;i<7;i++){ctx.save();ctx.translate(64+Math.sin(i*2.4)*31,64+Math.cos(i*2.4)*31);ctx.rotate(i*2.4);const g=ctx.createLinearGradient(-12,0,12,0);g.addColorStop(0,'#506f34');g.addColorStop(.5,'#8f9f4e');g.addColorStop(1,'#3d632f');ctx.fillStyle=g;ctx.beginPath();ctx.ellipse(0,0,13,24,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#aab174';ctx.lineWidth=.8;ctx.beginPath();ctx.moveTo(0,-22);ctx.lineTo(0,22);for(let y=-12;y<17;y+=7){ctx.moveTo(0,y);ctx.lineTo(10,y-7);ctx.moveTo(0,y);ctx.lineTo(-10,y-7);}ctx.stroke();ctx.restore();}
 const tex=new B.DynamicTexture('leaf-veins',c,scene,true);tex.hasAlpha=true;tex.update(false);
 const leaves=new B.PBRMaterial('leaf-cutouts',scene);leaves.albedoTexture=tex;leaves.useAlphaFromAlbedoTexture=true;leaves.transparencyMode=B.PBRMaterial.PBRMATERIAL_ALPHATEST;leaves.alphaCutOff=.35;leaves.backFaceCulling=false;leaves.twoSidedLighting=true;leaves.roughness=.95;leaves.metallic=0;
 const value={bark,leaves};cache.set(scene,value);return value;
}
export function detailedTree(scene,parent,pos,shadows,scale=1,variant=0){
 const materials=natureMaterials(scene),root=new B.TransformNode('detailed-tree',scene);root.parent=parent;root.position.copyFromFloats(...pos);root.scaling.setAll(scale);
 const branches=[],leaves=[];
 function branch(a,b,r1,r2){const p=new B.Vector3(...a),q=new B.Vector3(...b),d=q.subtract(p),m=B.MeshBuilder.CreateCylinder('branch',{height:d.length(),diameterBottom:r1*2,diameterTop:r2*2,tessellation:10},scene);m.position=p.add(q).scale(.5);m.rotationQuaternion=B.Quaternion.FromUnitVectorsToRef(B.Axis.Y,d.normalize(),new B.Quaternion());m.material=materials.bark;branches.push(m);}
 branch([0,0,0],[.10,3.5,0],.19,.075);
 for(let i=0;i<12;i++){
  const a=i*2.39996+variant,h=1.6+(i%5)*.35,r=1.05+(i%3)*.21,end=[Math.sin(a)*r,h+.8,Math.cos(a)*r];branch([0,h,0],end,.065,.014);
  for(let j=0;j<3;j++){const t=[end[0]+Math.sin(a+j)*.4,end[1]+.2+j*.16,end[2]+Math.cos(a+j)*.4];branch(end,t,.022,.006);
   for(let k=0;k<8;k++){const phi=k*2.4+j,radius=.18+(k%3)*.15,m=B.MeshBuilder.CreatePlane('leaf-spray',{size:.62+(k%3)*.10,sideOrientation:B.Mesh.DOUBLESIDE},scene);m.position.copyFromFloats(t[0]+Math.sin(phi)*radius,t[1]+Math.cos(phi)*.36,t[2]+Math.cos(phi)*radius);m.rotation.set(k*.83+j,k*1.7+variant,j*.8);m.material=materials.leaves;leaves.push(m);}
  }
 }
 for(const [pieces,name] of [[branches,'tree-branches'],[leaves,'tree-leaves']]){const merged=B.Mesh.MergeMeshes(pieces,true,true);merged.name=name;merged.parent=root;merged.isPickable=false;merged.receiveShadows=true;shadows.addShadowCaster(merged,false);}
 return root;
}
/** Pooled particles are evaluated from simulation age: pause/reset stay exact. */
export function detailedEffects(scene){
 const tex=new B.DynamicTexture('turbulent-smoke',smokeCanvas(),scene,true);tex.hasAlpha=true;tex.update(false);
 const particles=Array.from({length:148},(_,i)=>{
  const kind=i<72?'smoke':i<90?'fire':i<118?'spark':i<132?'debris':'dust';
  const m=kind==='debris'?B.MeshBuilder.CreateBox('blast-debris',{size:1},scene):B.MeshBuilder.CreatePlane('effect-'+kind,{size:1},scene);
  const mat=new B.StandardMaterial('effect-'+kind,scene);mat.disableLighting=true;mat.disableDepthWrite=kind!=='debris';mat.backFaceCulling=false;
  if(kind==='smoke'||kind==='fire'||kind==='dust'){mat.diffuseTexture=tex;mat.useAlphaFromDiffuseTexture=true;}
  mat.emissiveColor=B.Color3.FromHexString(kind==='fire'?'#ff9b35':kind==='spark'?'#ffe6a0':kind==='debris'?'#51483c':kind==='dust'?'#9b917d':'#85898a');
  if(kind==='spark'||kind==='fire')mat.alphaMode=B.Engine.ALPHA_ADD;
  m.material=mat;m.isPickable=false;if(kind!=='debris')m.billboardMode=B.Mesh.BILLBOARDMODE_ALL;m.setEnabled(false);return {m,kind};
 });
 const light=new B.PointLight('blast-flash',B.Vector3.Zero(),scene);light.diffuse=B.Color3.FromHexString('#ffad55');light.intensity=0;light.range=9;
 return {particles,update(event,origin=[2.5,.2,3],size=1){
  const age=event?.age??9,blast=event?.kind==='explosion';light.position.copyFromFloats(origin[0],origin[1]+1,origin[2]);light.intensity=blast?Math.max(0,1-age/.35)*7:0;
  particles.forEach(({m,kind},i)=>{const a=i*2.39996,delay=kind==='smoke'?(i%12)*.06:0,t=age-delay,lifetime=kind==='smoke'?7:kind==='fire'?.75:kind==='spark'?1.4:kind==='dust'?2.5:2.2;
   const enabled=!!event&&t>=0&&t<lifetime&&(blast||kind==='smoke');m.setEnabled(enabled);if(!enabled)return;
   let x,y,z,s,opacity;
   if(kind==='smoke'){const r=(.2+(i%9)*.10)*(1+t*.24),wind=t*.13;x=Math.cos(a)*r+wind;y=.22+t*(.24+(i%5)*.035)+(i%6)*.18;z=Math.sin(a)*r;s=.65+t*.28+(i%4)*.12;opacity=Math.min(1,t*3)*Math.pow(1-t/lifetime,1.3)*.62;m.material.emissiveColor.copyFromFloats(blast?.29:.57,blast?.30:.60,blast?.31:.62);}
   else if(kind==='dust'){const r=.4+t*2.3;x=Math.cos(a)*r;z=Math.sin(a)*r;y=.08;s=.6+t*.6;opacity=(1-t/lifetime)*.22;}
   else if(kind==='fire'){x=Math.cos(a)*t*1.5;y=.35+t*(.8+i%3*.3);z=Math.sin(a)*t*1.5;s=.5+Math.sin(t/lifetime*Math.PI)*1.5;opacity=(1-t/lifetime)*.85;}
   else{const speed=1.6+i%7*.38;x=Math.cos(a)*speed*t;z=Math.sin(a)*speed*t;y=Math.max(.03,.4+(1.7+i%5*.3)*t-2.7*t*t);s=kind==='spark'?.025:.05+(i%3)*.025;opacity=1-t/lifetime;}
   m.position.copyFromFloats(origin[0]+x*size,origin[1]+y*size,origin[2]+z*size);m.scaling.set(s*size,kind==='spark'?s*6*size:s*size,s*size);m.material.alpha=opacity;if(kind==='debris')m.rotation.set(t*3+i,t*2+i,t*4);
  });
 },dispose(){for(const {m} of particles){m.material.dispose(false,false);m.dispose();}tex.dispose();light.dispose();}};
}
