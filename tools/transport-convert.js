/** Offline conversion: FBX axes/materials to grounded, metre-scale PBR GLB. */
import * as T from 'three';
import {FBXLoader} from '/comparison/vendor/loaders/FBXLoader.js';
import {GLTFExporter} from '/comparison/vendor/exporters/GLTFExporter.js';
export async function convertTransport(entry){
 const source=await new FBXLoader().loadAsync('/source/'+entry.id+'.fbx');
 const atlas=entry.pack==='zombie'?await new T.TextureLoader().loadAsync('/source/Zombie_Atlas.png'):null;
 if(atlas)atlas.colorSpace=T.SRGBColorSpace;
 // The 2017 public transport FBX exports retain material slots, but all their
 // diffuse colors are white. Restore a readable palette using those slots.
 const palette={Yellow:'#e0b13e',Wheel:'#252c30',Black:'#252c30',Outside:'#668e91',Windows:'#243e4b',Window:'#243e4b',Bottom:entry.id==='SchoolBus'?'#daa62c':'#517f89',Top:entry.id==='SchoolBus'?'#e0b13e':'#e1ded1',Details:'#47515a',Bumper:'#3c4246',Lights:'#fff0b6',Material:'#252c30',Red:'#b33332',White:'#e4e1d9'};
 source.traverse(o=>{if(!o.isMesh)return;
  const convert=m=>{
   let color=m.color.clone();
   if(entry.pack==='public')color.set(palette[m.name]||(/wheel|tire/i.test(o.name)?'#252c30':/window|glass/i.test(m.name)?'#243e4b':/red|cross/i.test(m.name)?'#b33332':'#c4cccd'));
   const map=m.name==='Atlas'?atlas:null;
   if(map)color.set('#ffffff');
   if(m.name==='BrakeLight')color.set('#b33332');
   return new T.MeshStandardMaterial({name:m.name,color,map,vertexColors:m.vertexColors,roughness:.78,metalness:.05});
  };
  o.material=Array.isArray(o.material)?o.material.map(convert):convert(o.material);
 });
 const oriented=new T.Group();oriented.add(source);oriented.rotation.set(...entry.rotation.map(v=>v*Math.PI/180));
 const bounds=new T.Box3().setFromObject(oriented),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3());
 const scale=Math.min(entry.width/size.x,entry.length/size.z);
 // Put the authored origin on the ground at the footprint center. One uniform
 // scale preserves wheels and body proportions, including mirrors/couplers.
 const grounded=new T.Group();grounded.name=entry.id;grounded.add(oriented);
 oriented.scale.setScalar(scale);oriented.position.set(-center.x*scale,-bounds.min.y*scale,-center.z*scale);
 const dimensions=size.multiplyScalar(scale).toArray();
 const glb=await new GLTFExporter().parseAsync(grounded,{binary:true,onlyVisible:true});
 return {dimensions,data:btoa(Array.from(new Uint8Array(glb),x=>String.fromCharCode(x)).join(''))};
}
