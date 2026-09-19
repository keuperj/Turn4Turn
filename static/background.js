/** Seeded decorative scenery outside the tactical grid, shared by both renderers. */
import {B} from './rendering.js';
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
  const scenario=this.view.scenarios.get(state.theme),p=scenario.profile,n=state.size,c=(n-1)/2,rng=randomFor(state.seed+state.theme.length*797);
  this.plane('background-ground',c,c,900,900,this.material(state.theme+'-ground',p.color,p.texture,90),p.height??-.025);
  scenario.background?.call(this,state,rng);
 }
 atmosphere(){
  if(!this.state)return;
  const scene=this.view.nativeScene,p=this.view.scenarios.get(this.state.theme).profile,night=this.state.lighting==='night';
  const color=B.Color3.FromHexString(night?'#101b29':p.sky);scene.fogColor=color;scene.clearColor=new B.Color4(color.r,color.g,color.b,1);scene.fogMode=B.Scene.FOGMODE_LINEAR;
  // Move the clear zone with zoom: soften the distant surround without hiding
  // the tactical board when the camera is pulled back to a full-map view.
  const distance=B.Vector3.Distance(this.view.camera.native.position,this.view.controls.target);
  scene.fogStart=Math.max(30,distance+this.state.size*.35);scene.fogEnd=scene.fogStart+(night?50:75);
 }
}
