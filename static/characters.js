/** @fileoverview Load, instance, animate, and release Babylon character models. */
import {B} from './rendering.js';
import {dressCharacter} from './webgpu-quality.js';

const CIVILIANS=['Casual_Female','Casual_Male','Casual2_Female','Casual2_Male','OldClassy_Female','Worker_Male'];

// Local glTF sources; every person owns an independent skeleton and animations.
/** Manage loaded character containers and animated instances. */
export class CharacterAssets {
  /** Initialize this instance. */
  constructor(view){this.view=view;this.instances=new Map();}
  /** Load assets required by this component. */
  async load(){
    this.sources=new Map();
    const camo=new B.Texture('/assets/camouflage.png',this.view.nativeScene,false,false);
    camo.wrapU=camo.wrapV=B.Texture.WRAP_ADDRESSMODE;camo.anisotropicFilteringLevel=8;
    await Promise.all(['soldier','Ninja_Male',...CIVILIANS].map(async name=>{
      const container=await B.SceneLoader.LoadAssetContainerAsync('/assets/models/',name+'.glb',this.view.nativeScene);
      container.animationGroups.forEach(g=>g.stop());
      const root=container.rootNodes[0];root.computeWorldMatrix(true);
      const {min,max}=root.getHierarchyBoundingVectors(true);
      const scale=1.62/(max.y-min.y),bottom=min.y;
      if(name==='soldier')for(const mesh of container.meshes){
        const material=mesh.material,c=material?.albedoColor;
        if(!c||(material.albedoTexture!==camo&&(c.g<=c.r*1.1||c.g<=c.b*1.1)))continue;
        // The original FBX has no UVs. Project the rest-pose coordinates onto
        // each surface's dominant plane; skinning keeps the fabric on the body.
        const positions=mesh.getVerticesData(B.VertexBuffer.PositionKind),normals=mesh.getVerticesData(B.VertexBuffer.NormalKind);
        if(!positions||!normals)continue;
        const uv=[],ys=positions.filter((_,i)=>i%3===1),repeat=3/(Math.max(...ys)-Math.min(...ys)||1);
        for(let i=0;i<positions.length;i+=3){
          const [x,y,z]=positions.slice(i,i+3),[nx,ny,nz]=normals.slice(i,i+3).map(Math.abs);
          uv.push((nx>nz?z:x)*repeat,(ny>nx&&ny>nz?z:y)*repeat);
        }
        mesh.setVerticesData(B.VertexBuffer.UVKind,uv);
        material.albedoTexture=camo;material.albedoColor=B.Color3.White();material.roughness=.95;
      }
      this.sources.set(name,{container,scale,bottom});
    }));
  }
  /** Select a reproducible civilian appearance from the mission and unit ID. */
  variant(unit){
    if(unit.team==='soldier')return 'soldier';
    if(unit.team!=='civilian')return 'Ninja_Male';
    let hash=2166136261;
    for(const c of `${this.view.state?.seed??0}:${unit.id}`)hash=Math.imul(hash^c.charCodeAt(0),16777619);
    return CIVILIANS[(hash>>>0)%CIVILIANS.length];
  }

  /** Apply the supplied comparison state to renderer and camera controls. */
  apply(model,unit,weapon){
    const variant=this.variant(unit),source=this.sources?.get(variant);if(!source)return;
    const {container,scale,bottom}=source;
    const rig=model.userData.rig,body=rig.body;
    // Keep the equipment and tactical markers; replace the procedural person.
    for(const part of [...body.children])if(part!==weapon){part.dispose();}
    const existingTextures=new Set(this.view.nativeScene.textures);
    const instance=container.instantiateModelsToScene(name=>`${unit.id}:${name}`,true,{doNotInstantiate:true});
    // Babylon clones material textures too. Own only the new texture wrappers,
    // never source atlases or the shared WebGPU detail maps added below.
    const textures=this.view.nativeScene.textures.filter(t=>!existingTextures.has(t));
    const root=instance.rootNodes[0];root.parent=body.native;root.scaling.scaleInPlace(scale);root.position.y=-bottom*scale;root.rotationQuaternion=B.Quaternion.RotationAxis(B.Axis.Y,Math.PI);
    if(this.view.renderer==='webgpu'&&unit.team==='soldier')dressCharacter(this.view.nativeScene,root,this.view.shadows);
    const meshes=root.getChildMeshes();for(const m of meshes){m.metadata={pickOwner:model};m.isPickable=!unit.corpse;m.receiveShadows=true;this.view.shadows.addShadowCaster(m,false);}
    const all=[root,...root.getDescendants()],hand=all.find(n=>n.name.endsWith(':FistR'));
    const bones=new Map(all.map(n=>[n.name.split(':').at(-1),n]));
    instance.animationGroups.forEach(g=>g.stop());
    const entry={model,unit,variant,scale,bottom,instance,root,weapon,hand,bones,textures,materials:new Set(meshes.map(m=>m.material).filter(Boolean)),current:null,previous:null,blend:1,stance:unit.stance};this.instances.set(model,entry);model.userData.animated=true;
    // The source character has no authored crawl/kneel clip. Apply a static knee
    // pose to its skeleton; the prone pose uses the body's existing ground tilt.
    this.motion(model,'idle');
    if(unit.corpse){entry.current?.pause();entry.current?.goToFrame(0);entry.dead=true;}
    if(unit.team==='civilian')weapon.visible=false;
    model.userData.rig.legs=[];model.userData.rig.arms=[];
  }
  /** Select and blend the requested character animation. */
  motion(model,action){
    const e=this.instances.get(model);if(!e||e.dead)return;
    let wanted=action==='walk'?'Walk_Carry':action==='climb'?'Walk':'Idle';
    if(e.stance==='prone')wanted='Walk_Carry';
    const next=e.instance.animationGroups.find(g=>g.name.endsWith('|'+wanted))||e.instance.animationGroups[0];
    if(next!==e.current){e.previous?.stop();e.previous=e.current;e.current=next;e.blend=0;next.start(true,action==='climb'?.65:1);next.setWeightForAllAnimatables(0);}
    if(e.stance==='prone'){next.pause();next.goToFrame(next.from+(next.to-next.from)*.3);}
  }
  /** Advance this component for the current animation frame. */
  update(dt){for(const e of this.instances.values()){
    if(e.dead)continue;
    e.blend=Math.min(1,e.blend+dt*5);e.current?.setWeightForAllAnimatables(e.blend);e.previous?.setWeightForAllAnimatables(1-e.blend);if(e.blend===1){e.previous?.stop();e.previous=null;}
  }}
  /** Apply post-animation pose corrections to active characters. */
  afterAnimations(){for(const e of this.instances.values()){
    if(e.stance==='kneeling'&&!e.dead){
      for(const [name,angle] of [['UpperLegL',-.85],['LowerLegL',1.55],['UpperLegR',-.25],['LowerLegR',1.6]]){const n=e.bones.get(name);if(n){n.rotationQuaternion=B.Quaternion.RotationAxis(B.Axis.X,angle);}}
      e.root.position.y=-e.bottom*e.scale-.35;
    }
    if(e.hand&&e.weapon.visible){e.hand.computeWorldMatrix(true);const inverse=e.model.userData.rig.body.native.computeWorldMatrix(true).clone().invert();const p=B.Vector3.TransformCoordinates(e.hand.getAbsolutePosition(),inverse);e.weapon.position.set(p.x,p.y,p.z-.06);}
  }}
  /** Dispose one character instance and its owned materials. */
  release(model){const e=this.instances.get(model);if(!e)return;for(const m of e.root.getChildMeshes())this.view.shadows.removeShadowCaster(m,false);e.instance.dispose();for(const m of e.materials)m.dispose(false,false);for(const t of e.textures)t.dispose();this.instances.delete(model);}
}
