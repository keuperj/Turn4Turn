/** Forest floor, dirt trails and batched grass tufts shared by both renderers. */
import * as G from './rendering.js';
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

/** Reuse the loaded nature models and materials for canopy continuity. */
export function woodlandProp(view,p,group){
 if(p.kind==='tree_pine'){
  group.userData.structure=p.id;view.pickables.push(group);
  const part=(name,options,y,color)=>{
   const mesh=G.B.MeshBuilder.CreateCylinder(name,options,view.nativeScene);mesh.parent=group.native;mesh.position.y=y;
   mesh.material=view.background.material('woodland-'+color,color);mesh.metadata={pickOwner:group};mesh.isPickable=true;mesh.receiveShadows=true;view.shadows.addShadowCaster(mesh,false);
  };
  part('woodland-pine-trunk',{height:2.8,diameter:.16,tessellation:8},1.4,'#725339');
  for(let i=0;i<4;i++)part('woodland-pine-crown',{height:1.15,diameterTop:0,diameterBottom:1.4-i*.20,tessellation:9},1.3+i*.48,['#386344','#4c7650','#62834e'][(i+p.variant)%3]);
  return true;
 }
 const variants={tree_oak:['CommonTree_1','CommonTree_3'],tree_birch:['BirchTree_1','BirchTree_3'],bush:['Bush_1','BushBerries_1']};
 const ids=variants[p.kind];if(!ids)return false;
 const source=view.background?.sources.get(ids[(p.variant||0)%ids.length]);if(!source)return false;
 const instance=source.instantiateModelsToScene(name=>'woodland:'+p.id+':'+name,false,{doNotInstantiate:false});
 group.userData.structure=p.id;view.pickables.push(group);
 for(const root of instance.rootNodes){
  root.parent=group.native;root.scaling.scaleInPlace(p.kind==='bush'?.55:.5);
  for(const mesh of root.getChildMeshes()){
   mesh.metadata={pickOwner:group};mesh.isPickable=true;mesh.receiveShadows=true;view.shadows.addShadowCaster(mesh,false);
  }
 }
 return true;
}
