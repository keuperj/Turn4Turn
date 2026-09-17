/** Shared CC0 transport assets for both Babylon WebGL and WebGPU renderers. */
import {B} from './rendering.js';

export class TransportAssets {
 constructor(view){this.view=view;this.sources=new Map();this.models=[];this.failures=[];}
 async load(){
  try{
   const response=await fetch('/assets/models/transport/manifest.json');
   if(!response.ok)throw new Error(`Transport manifest: HTTP ${response.status}`);
   this.models=(await response.json()).models;
   await Promise.all(this.models.map(async entry=>{
    try{
     const source=await B.SceneLoader.LoadAssetContainerAsync('/assets/models/transport/',entry.file,this.view.nativeScene);
     source.animationGroups.forEach(g=>g.stop());
     this.sources.set(entry.id,source);
    }catch(error){this.failures.push(entry.id);console.warn(`Transport ${entry.id} unavailable; using procedural fallback.`,error);}
   }));
  }catch(error){this.failures.push('manifest');console.warn('Transport assets unavailable; using procedural fallback.',error);}
 }
 add(prop,owner){
  const candidates=this.models.filter(e=>e.kind===prop.kind);
  const entry=candidates.find(e=>e.id===prop.model)||candidates[(prop.variant||0)%candidates.length];
  const source=entry&&this.sources.get(entry.id);
  if(!source)return false;
  // Assets already use Y-up and a centered, grounded metre-scale origin.
  // This guard also keeps older/smaller saved footprints safe without distortion.
  const scale=Math.min(1,prop.width*.94/entry.dimensions[0],prop.depth*.94/entry.dimensions[2]);
  const instance=source.instantiateModelsToScene(name=>`${prop.id}:${name}`,false,{doNotInstantiate:false});
  for(const root of instance.rootNodes){
   root.parent=owner.native;root.scaling.scaleInPlace(scale);
   if(prop.kind==='train')root.position.y+=.085;
   for(const mesh of root.getChildMeshes()){
    mesh.metadata={pickOwner:owner};mesh.isPickable=true;mesh.receiveShadows=true;
    this.view.shadows.addShadowCaster(mesh,false);
   }
  }
  Object.assign(owner.userData,{structure:prop.id,transport:entry.id,transportHeight:entry.dimensions[1]*scale+(prop.kind==='train'?.085:0)});
  this.view.pickables.push(owner);
  return true;
 }
}
