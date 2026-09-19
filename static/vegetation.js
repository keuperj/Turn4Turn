import * as G from './rendering.js';
/** Reuse the loaded nature models and materials for canopy continuity. */
export function vegetationProp(view,p,group){
 if(!p.woodland)return false;
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
