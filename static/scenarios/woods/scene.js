/** Forest floor, dirt trails and batched grass tufts shared by both renderers. */
import * as G from '../../rendering.js';
export function woodlandGround(view,state){
 const n=state.size,positions=[],indices=[],normals=[],uvs=[];
 for(const [type,color] of [['forest_path',0x9b8764],['meadow',0x819955]]){
  const cells=[];for(let y=0;y<n;y++)for(let x=0;x<n;x++)if(state.tiles[y][x]===type)cells.push({x,y:.018,z:y});
  const material=view.material(color,'soil');view.tiles(view.terrain,cells,material,1);
 }
 for(let z=0;z<n;z++)for(let x=0;x<n;x++){
  const type=state.tiles[z][x],hash=((x*73856093)^(z*19349663)^state.seed)>>>0;
  if(type!=='meadow'&&(type!=='forest'||hash%4))continue;
  for(let tuft=0;tuft<(type==='meadow'?4:2);tuft++){
   const px=x+Math.sin(hash+tuft*7)*.35,pz=z+Math.cos(hash+tuft*11)*.35,h=.13+(hash%5)*.035;
   for(let blade=0;blade<3;blade++){
    const angle=blade*Math.PI/3,dx=Math.cos(angle)*.09,dz=Math.sin(angle)*.09,i=positions.length/3;
    positions.push(px-dx,.025,pz-dz,px+dx,.025,pz+dz,px+dx*.6,h,pz+dz*.6);
    normals.push(0,1,0,0,1,0,0,1,0);uvs.push(0,0,1,0,.5,1);indices.push(i,i+1,i+2);
   }
  }
 }
 const mesh=new G.B.Mesh('woodland-undergrowth',view.nativeScene),data=new G.B.VertexData();Object.assign(data,{positions,indices,normals,uvs});data.applyToMesh(mesh);
 const owner=new G.Group(mesh);owner.isMesh=true;owner.material=view.material(0x687f3d,'soil');mesh.material=owner.material.native;mesh.material.backFaceCulling=false;mesh.isPickable=false;mesh.receiveShadows=true;view.terrain.add(owner);
}

