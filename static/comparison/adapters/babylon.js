/** @fileoverview Render the comparison scene through Babylon.js. */
/** Create and initialize this renderer adapter. */
export async function create(canvas){
 const B=window.BABYLON,engine=new B.Engine(canvas,true,{preserveDrawingBuffer:true,stencil:true});engine.setHardwareScalingLevel(1);
 const scene=new B.Scene(engine);scene.useRightHandedSystem=true;scene.clearColor=B.Color4.FromHexString('#9aaeb8ff');
 scene.imageProcessingConfiguration.toneMappingEnabled=true;scene.imageProcessingConfiguration.toneMappingType=B.ImageProcessingConfiguration.TONEMAPPING_ACES;
 const camera=new B.FreeCamera('camera',new B.Vector3(15,12,19),scene);camera.minZ=.1;camera.maxZ=120;camera.fov=Math.PI/4;
 const hemi=new B.HemisphericLight('sky',new B.Vector3(0,1,0),scene);hemi.intensity=.85;hemi.diffuse=B.Color3.FromHexString('#dbeaff');hemi.groundColor=B.Color3.FromHexString('#8e8773');
 const sun=new B.DirectionalLight('sun',new B.Vector3(6,-12,-8),scene);sun.position=new B.Vector3(-6,12,8);sun.intensity=3;sun.diffuse=B.Color3.FromHexString('#fff1db');sun.shadowMinZ=1;sun.shadowMaxZ=45;
 const shadows=new B.ShadowGenerator(2048,sun);shadows.usePercentageCloserFiltering=true;shadows.filteringQuality=B.ShadowGenerator.QUALITY_MEDIUM;shadows.normalBias=.025;
 const [env,person,vehicle]=await Promise.all(['courtyard','character','CesiumMilkTruck'].map(n=>B.SceneLoader.LoadAssetContainerAsync('assets/',n+'.glb',scene)));
 for(const asset of [env,person,vehicle]){asset.addAllToScene();for(const m of asset.meshes){m.receiveShadows=true;if(m.getTotalVertices())shadows.addShadowCaster(m);}}
 /** Normalize loaded scene materials and mesh settings. */
 function normalize(asset,height){const root=asset.rootNodes[0];root.computeWorldMatrix(true);const {min,max}=root.getHierarchyBoundingVectors(true),scale=height/(max.y-min.y);const wrap=new B.TransformNode('placement',scene);root.parent=wrap;root.scaling.scaleInPlace(scale);root.position=new B.Vector3(-(min.x+max.x)/2*scale,-min.y*scale,-(min.z+max.z)/2*scale);return wrap;}
 const actor=normalize(person,1.8),truck=normalize(vehicle,2.4);truck.position=new B.Vector3(5,0,-.2);truck.rotation.y=-Math.PI/2;
 const clips=person.animationGroups;clips.forEach(g=>g.stop());let active=null,blend=1,previous=null;
 const effects=Array.from({length:42},(_,i)=>{const m=B.MeshBuilder.CreateSphere('fx',{segments:8,diameter:2},scene),mat=new B.StandardMaterial('fxmat',scene);mat.diffuseColor=B.Color3.FromHexString(i<10?'#ff992e':'#5b6266');mat.specularColor=B.Color3.Black();mat.disableDepthWrite=true;m.material=mat;m.setEnabled(false);return m;});
 return {version:B.Engine.Version,clips:clips.map(c=>c.name),
 /** Resize rendering resources to their displayed dimensions. */
 resize(w,h){engine.setSize(w,h);},camera(eye,target){camera.position.copyFromFloats(...eye);camera.setTarget(new B.Vector3(...target));},
 /** Apply the selected building cutaway level. */
 cutaway(mode){for(const n of env.transformNodes){if(n.name==='roof')n.setEnabled(mode==='exterior');if(n.name==='level_1')n.setEnabled(mode!=='ground');if(n.name==='near_0')n.setEnabled(mode!=='ground');if(n.name==='near_1')n.setEnabled(mode==='exterior');}},
 /** Select and blend the requested character animation. */
 motion(name){const next=clips.find(c=>c.name.toLowerCase().split('|').pop()===name)||clips[0];if(next&&next!==active){previous?.stop();previous=active;active=next;active.start(true);active.setWeightForAllAnimatables(0);blend=0;}},
 /** Advance this component for the current animation frame. */
 update(dt,pos,yaw,fx){engine.beginFrame();scene.animationsEnabled=dt>0;scene.animationTimeScale=1;actor.position.copyFromFloats(...pos);actor.rotation.y=yaw;if(active){blend=Math.min(1,blend+dt*4);active.setWeightForAllAnimatables(blend);previous?.setWeightForAllAnimatables(1-blend);if(blend===1){previous?.stop();previous=null;}}effects.forEach((m,i)=>{const p=fx[i];m.setEnabled(!!p);if(p){m.position.copyFromFloats(...p.pos);m.scaling.setAll(p.scale);m.material.alpha=p.opacity;m.material.emissiveColor=B.Color3.FromHexString(p.fire?'#e55d12':'#000000');}});scene.render();engine.endFrame();},
 /** Return a concise equipment-statistics label. */
 stats(){return {draws:engine._drawCalls?.current,triangles:scene.getActiveIndices()/3};},capture(){return canvas.toDataURL('image/png');}
 };
}
