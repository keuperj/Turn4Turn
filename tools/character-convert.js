/** Offline conversion of the original Quaternius animated FBX characters. */
import * as T from 'three';
import {FBXLoader} from '/comparison/vendor/loaders/FBXLoader.js';
import {GLTFExporter} from '/comparison/vendor/exporters/GLTFExporter.js';
export async function convertCharacter(entry){
 const root=await new FBXLoader().loadAsync('/source/'+entry.id+'.fbx');
 root.traverse(o=>{if(!o.isMesh)return;
  const convert=m=>new T.MeshStandardMaterial({name:m.name,color:m.color.clone().multiplyScalar(m.color.g<.1?25:1),roughness:.8});
  o.material=Array.isArray(o.material)?o.material.map(convert):convert(o.material);
 });
 const data=await new GLTFExporter().parseAsync(root,{binary:true,animations:root.animations});
 return {data:await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(new Blob([data]));})};
}
