import {B} from './rendering.js';

// One local glTF source, independent skeletons and animation groups per fighter.
export class CharacterAssets {
  constructor(view){this.view=view;this.instances=new Map();}
  async load(){
    this.source=await B.SceneLoader.LoadAssetContainerAsync('/assets/models/','soldier.glb',this.view.nativeScene);
    this.source.animationGroups.forEach(g=>g.stop());
    const root=this.source.rootNodes[0];root.computeWorldMatrix(true);
    const {min,max}=root.getHierarchyBoundingVectors(true);
    this.scale=1.62/(max.y-min.y);this.bottom=min.y;
  }
  apply(model,unit,weapon){
    if(!this.source)return;
    const rig=model.userData.rig,body=rig.body;
    // Keep the equipment and tactical markers; replace the procedural person.
    for(const part of [...body.children])if(part!==weapon){part.dispose();}
    const instance=this.source.instantiateModelsToScene(name=>`${unit.id}:${name}`,true,{doNotInstantiate:true});
    const root=instance.rootNodes[0];root.parent=body.native;root.scaling.scaleInPlace(this.scale);root.position.y=-this.bottom*this.scale;root.rotationQuaternion=B.Quaternion.RotationAxis(B.Axis.Y,Math.PI);
    const meshes=root.getChildMeshes(),tinted=new Set();for(const m of meshes){m.metadata={pickOwner:model};m.isPickable=!unit.corpse;m.receiveShadows=true;this.view.shadows.addShadowCaster(m,false);
      if(unit.team!=='soldier'&&m.material?.albedoColor&&!tinted.has(m.material)){tinted.add(m.material);const c=m.material.albedoColor;if(c.g>c.r*1.1&&c.g>c.b*1.1)m.material.albedoColor=unit.team==='alien'?new B.Color3(.25,.07,.045):new B.Color3(.045,.13,.28);}
    }
    const all=[root,...root.getDescendants()],hand=all.find(n=>n.name.endsWith(':FistR'));
    const bones=new Map(all.map(n=>[n.name.split(':').at(-1),n]));
    instance.animationGroups.forEach(g=>g.stop());
    const entry={model,unit,instance,root,weapon,hand,bones,materials:new Set(meshes.map(m=>m.material).filter(Boolean)),current:null,previous:null,blend:1,stance:unit.stance};this.instances.set(model,entry);model.userData.animated=true;
    // The source character has no authored crawl/kneel clip. Apply a static knee
    // pose to its skeleton; the prone pose uses the body's existing ground tilt.
    this.motion(model,'idle');
    if(unit.corpse){entry.current?.pause();entry.current?.goToFrame(0);entry.dead=true;}
    if(unit.team==='civilian')weapon.visible=false;
    model.userData.rig.legs=[];model.userData.rig.arms=[];
  }
  motion(model,action){
    const e=this.instances.get(model);if(!e||e.dead)return;
    let wanted=action==='walk'?'Walk_Carry':action==='climb'?'Walk':'Idle';
    if(e.stance==='prone')wanted='Walk_Carry';
    const next=e.instance.animationGroups.find(g=>g.name.endsWith('|'+wanted))||e.instance.animationGroups[0];
    if(next!==e.current){e.previous?.stop();e.previous=e.current;e.current=next;e.blend=0;next.start(true,action==='climb'?.65:1);next.setWeightForAllAnimatables(0);}
    if(e.stance==='prone'){next.pause();next.goToFrame(next.from+(next.to-next.from)*.3);}
  }
  update(dt){for(const e of this.instances.values()){
    if(e.dead)continue;
    e.blend=Math.min(1,e.blend+dt*5);e.current?.setWeightForAllAnimatables(e.blend);e.previous?.setWeightForAllAnimatables(1-e.blend);if(e.blend===1){e.previous?.stop();e.previous=null;}
  }}
  afterAnimations(){for(const e of this.instances.values()){
    if(e.stance==='kneeling'&&!e.dead){
      for(const [name,angle] of [['UpperLegL',-.85],['LowerLegL',1.55],['UpperLegR',-.25],['LowerLegR',1.6]]){const n=e.bones.get(name);if(n){n.rotationQuaternion=B.Quaternion.RotationAxis(B.Axis.X,angle);}}
      e.root.position.y=-this.bottom*this.scale-.35;
    }
    if(e.hand&&e.weapon.visible){e.hand.computeWorldMatrix(true);const inverse=e.model.userData.rig.body.native.computeWorldMatrix(true).clone().invert();const p=B.Vector3.TransformCoordinates(e.hand.getAbsolutePosition(),inverse);e.weapon.position.set(p.x,p.y,p.z-.06);}
  }}
  release(model){const e=this.instances.get(model);if(!e)return;for(const m of e.root.getChildMeshes())this.view.shadows.removeShadowCaster(m,false);e.instance.dispose();for(const m of e.materials)m.dispose(false,false);this.instances.delete(model);}
}
