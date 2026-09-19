/** Batched soil, crop rows and connecting farmyard paths for both renderers. */
import * as G from './rendering.js';
import {surfaceBatch} from './street-crossing.js';
export function farmGround(view,state){
 const soil=[],rows=[],paths=[],positions=[],indices=[];
 for(let z=0;z<state.size;z++)for(let x=0;x<state.size;x++){
  const type=state.tiles[z][x];
  if(type==='farm_path')paths.push({x,z,w:1,d:1});
  // Low grass adds pasture texture without blocking tactical paths or picking.
  if(type==='grass'){
   const hash=((x*73856093)^(z*19349663)^state.seed)>>>0;
   for(let tuft=0;tuft<3;tuft++){
    const px=x+Math.sin(hash+tuft*7)*.35,pz=z+Math.cos(hash+tuft*11)*.35,h=.12+(hash%5)*.025;
    for(let blade=0;blade<3;blade++){
     const angle=blade*Math.PI/3,dx=Math.cos(angle)*.09,dz=Math.sin(angle)*.09,i=positions.length/3;
     positions.push(px-dx,.025,pz-dz,px+dx,.025,pz+dz,px,h,pz);indices.push(i,i+1,i+2);
    }
   }
  }
  if(type!=='crops')continue;
  soil.push({x,z,w:1,d:1});
  for(const off of [-.3,0,.3])rows.push({x:x+off,z,w:.12,d:1});
 }
 surfaceBatch(view,view.terrain,'farm-soil',soil,view.material(0x79603f,'soil'),.014);
 surfaceBatch(view,view.terrain,'farm-crop-rows',rows,view.material(0xa5a05c,'soil'),.065);
 surfaceBatch(view,view.terrain,'farm-paths',paths,view.material(state.scenery.road,'soil'),.018);
 const mesh=new G.B.Mesh('farm-pasture-grass',view.nativeScene),data=new G.B.VertexData(),normals=[];
 G.B.VertexData.ComputeNormals(positions,indices,normals);Object.assign(data,{positions,indices,normals});data.applyToMesh(mesh);
 const owner=new G.Group(mesh);owner.isMesh=true;owner.material=view.material(0x687f3d,'soil');mesh.material=owner.material.native;
 mesh.material.backFaceCulling=false;mesh.isPickable=false;mesh.receiveShadows=true;view.terrain.add(owner);
}
