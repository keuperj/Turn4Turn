/** WebGPU-only material and lighting quality. Never called by the WebGL path. */
const B=window.BABYLON;
const materialSets=new WeakMap();
export function qualityLighting(scene,camera,sun,shadows){
 if(!scene.getEngine().isWebGPU)throw Error('Quality profile requires WebGPU');
 shadows.getShadowMap().resize(4096);
 shadows.filteringQuality=B.ShadowGenerator.QUALITY_HIGH;
 shadows.normalBias=.012;
 const pipeline=new B.DefaultRenderingPipeline('webgpu-quality',true,scene,[camera]);
 pipeline.samples=4;pipeline.fxaaEnabled=true;
 pipeline.bloomEnabled=true;pipeline.bloomThreshold=1.5;pipeline.bloomWeight=.08;pipeline.bloomKernel=48;
 // Keep tactical silhouettes sharp: no depth of field or motion blur.
 scene.imageProcessingConfiguration.exposure=1.05;
 return pipeline;
}
export function qualityMaterials(scene){
 if(materialSets.has(scene))return materialSets.get(scene);
 const texture=(url,scale=1)=>{const t=new B.Texture(url,scene,false,false);t.wrapU=t.wrapV=B.Texture.WRAP_ADDRESSMODE;t.uScale=t.vScale=scale;t.anisotropicFilteringLevel=16;return t;};
 const stone=texture('/assets/limestone-webgpu-v1.png');
 const metal=texture('/assets/painted-metal-v2.webp');
 const ground=texture('/assets/terrain-mixed-v2.webp',8);
 // Deterministic micro-normal detail, independent of the generated albedo.
 const canvas=document.createElement('canvas');canvas.width=canvas.height=256;
 const ctx=canvas.getContext('2d'),pixels=ctx.createImageData(256,256);
 let seed=81731;const noise=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
 for(let y=0;y<256;y++)for(let x=0;x<256;x++){const i=(y*256+x)*4;pixels.data[i]=128+(noise()-.5)*12;pixels.data[i+1]=128+(noise()-.5)*12;pixels.data[i+2]=254;pixels.data[i+3]=255;}
 ctx.putImageData(pixels,0,0);const normal=new B.DynamicTexture('micro-normal',canvas,scene,true);normal.gammaSpace=false;normal.level=.2;normal.wrapU=normal.wrapV=B.Texture.WRAP_ADDRESSMODE;normal.uScale=normal.vScale=6;normal.update(false);
 const brick=texture('/assets/brick-webgpu-v2.png',2),timber=texture('/assets/timber-webgpu-v2.png'),bark=texture('/assets/bark-webgpu-v2.png'),carRed=texture('/assets/car-red-webgpu-v2.png'),carBlue=texture('/assets/car-blue-webgpu-v2.png');
 const maps={stone,metal,ground,normal,brick,timber,bark,carRed,carBlue};materialSets.set(scene,maps);return maps;
}
/** Add wearable equipment to existing animated transform bones, preserving the rig. */
export function dressCharacter(scene,root,shadows){
 const cloth=new B.PBRMaterial('webgpu-woven-gear',scene);cloth.albedoColor=B.Color3.FromHexString('#6e7654').toLinearSpace();cloth.roughness=.96;cloth.metallic=0;
 cloth.bumpTexture=qualityMaterials(scene).normal;
 for(const mesh of root.getChildMeshes()){const m=mesh.material;if(m?.albedoColor&&(m.albedoColor.g>m.albedoColor.r*1.1||m.albedoTexture?.url?.endsWith('/camouflage.png')))m.bumpTexture=cloth.bumpTexture;}
 const dark=new B.PBRMaterial('webgpu-straps',scene);dark.albedoColor=B.Color3.FromHexString('#303932').toLinearSpace();dark.roughness=.82;dark.metallic=.12;
 const nodes=[root,...root.getDescendants()];
 const bone=name=>nodes.find(n=>n.name.split(':').at(-1).split('|').at(-1)===name||n.name.endsWith(name));
 function part(name,parent,size,offset,mat){if(!parent)return;parent.computeWorldMatrix(true);const s=new B.Vector3(),q=new B.Quaternion(),p=new B.Vector3();parent.getWorldMatrix().decompose(s,q,p);const k=Math.abs(s.x)||1;const m=B.MeshBuilder.CreateBox(name,{width:size[0]/k,height:size[1]/k,depth:size[2]/k},scene);m.parent=parent;m.position.copyFromFloats(...offset.map(v=>v/k));m.material=mat;m.isPickable=false;m.receiveShadows=true;shadows.addShadowCaster(m,false);}
 const chest=bone('Torso')||bone('Spine2')||bone('Chest')||bone('Spine');
 for(const x of [-.115,0,.115]){part('ammo-pouch',chest,[.09,.14,.065],[x,.025,.15],cloth);part('pouch-flap',chest,[.095,.035,.075],[x,.083,.155],dark);}
 part('field-pack',chest,[.30,.34,.16],[0,.02,-.19],cloth);
 for(const x of [-.13,.13])part('shoulder-webbing',chest,[.035,.34,.025],[x,.10,.115],dark);
 for(const side of ['L','R']){part('knee-pad',bone('LowerLeg'+side),[.13,.14,.055],[0,.02,.075],dark);}
 return {chest:!!chest};
}
