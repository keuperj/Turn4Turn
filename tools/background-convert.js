/** Convert original Quaternius scenery into compact, grounded PBR GLBs. */
import * as T from 'three';
import {FBXLoader} from '/comparison/vendor/loaders/FBXLoader.js';
import {GLTFExporter} from '/comparison/vendor/exporters/GLTFExporter.js';
import {mergeGroups} from '/comparison/vendor/utils/BufferGeometryUtils.js';
export async function convertBackground(entry){
 const manager=new T.LoadingManager();
 manager.setURLModifier(url=>/\.(png|jpg)$/i.test(url)?'/source/'+url.split(/[\\/]/).at(-1):url);
 const loaded=new Promise(resolve=>manager.onLoad=resolve);
 const source=await new FBXLoader(manager).loadAsync('/source/'+entry.id+'.fbx');await loaded;
 const atlas=entry.texture?await new T.TextureLoader().loadAsync('/source/'+entry.texture):null;
 if(atlas){atlas.colorSpace=T.SRGBColorSpace;atlas.magFilter=T.NearestFilter;atlas.minFilter=T.LinearMipmapLinearFilter;}
 const materials=new Map();
 source.traverse(o=>{if(!o.isMesh)return;
  const convert=m=>{
   if(!materials.has(m)){
    if(m.map)m.map.colorSpace=T.SRGBColorSpace;
    materials.set(m,new T.MeshStandardMaterial({name:m.name,color:m.map||atlas?new T.Color(1,1,1):m.color.clone().convertLinearToSRGB(),map:m.map||atlas,roughness:.9,metalness:0}));
   }
   return materials.get(m);
  };
  o.material=Array.isArray(o.material)?o.material.map(convert):convert(o.material);
  if(o.geometry.groups.length)mergeGroups(o.geometry);
 });
 const oriented=new T.Group();oriented.add(source);oriented.rotation.set(...entry.rotation.map(v=>v*Math.PI/180));
 const bounds=new T.Box3().setFromObject(oriented),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3()),scale=entry.height/size.y;
 const grounded=new T.Group();grounded.name=entry.id;grounded.add(oriented);
 oriented.scale.setScalar(scale);oriented.position.set(-center.x*scale,-bounds.min.y*scale,-center.z*scale);
 const data=await new GLTFExporter().parseAsync(grounded,{binary:true});
 return {dimensions:size.multiplyScalar(scale).toArray(),materials:[...materials.values()].map(m=>({name:m.name,color:m.color.toArray(),texture:m.map?.image?.src})),data:await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(new Blob([data]));})};
}
