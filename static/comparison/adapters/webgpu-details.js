/** Additional art for the WebGPU quality study; shared GLBs stay untouched. */
import {qualityMaterials,dressCharacter} from '../../webgpu-quality.js';
import {detailedTree} from '../../webgpu-nature.js';
import {setDress} from './webgpu-setdress.js';
export function addDetails(scene,env,person,truck,shadows){
 const B=window.BABYLON,maps=qualityMaterials(scene);
 const mat=(name,color,roughness=.8,metallic=0)=>{const m=new B.PBRMaterial(name,scene);m.albedoColor=B.Color3.FromHexString(color).toLinearSpace();m.roughness=roughness;m.metallic=metallic;return m;};
 const stone=mat('limestone','#d6ccba');stone.albedoTexture=maps.stone;stone.bumpTexture=maps.normal;
 const steel=mat('aged-steel','#546260',.38,.72);steel.albedoTexture=maps.metal;
 const trim=mat('cut-stone','#c3b79e'),wood=mat('timber','#715640'),rubber=mat('rubber','#24292a'),leaf=mat('foliage','#536847');
 const road=mat('asphalt','#69716e');road.albedoTexture=maps.ground;road.bumpTexture=maps.normal;
 const root=new B.TransformNode('webgpu-detail',scene),groups={};
 for(const n of env.transformNodes)if(['roof','near_0','near_1','level_0','level_1'].includes(n.name))groups[n.name]=n;
 function mesh(m,pos,material,parent=root){m.position.copyFromFloats(...pos);m.material=material;m.parent=parent;m.receiveShadows=true;m.isPickable=false;shadows.addShadowCaster(m,false);return m;}
 const box=(name,size,pos,material=steel,parent=root)=>mesh(B.MeshBuilder.CreateBox(name,{width:size[0],height:size[1],depth:size[2]},scene),pos,material,parent);
 const cyl=(name,r,h,pos,material=steel,parent=root)=>mesh(B.MeshBuilder.CreateCylinder(name,{diameter:2*r,height:h,tessellation:20},scene),pos,material,parent);
 const floorboards=mat('interior-oak-floor','#c5b494',.85);floorboards.albedoTexture=maps.timber.clone();floorboards.albedoTexture.uScale=6;floorboards.albedoTexture.vScale=2;floorboards.bumpTexture=maps.normal;
 for(const m of env.meshes){if(m.name==='floor_slab')m.material=floorboards;if(m.name==='cornice'&&m.position.z>0)m.parent=groups[m.position.y>4?'near_1':'near_0'];if(/rear_wall|west_wall|window_apron|east_sill/.test(m.name))m.material=stone;else if(m.material?.getClassName()==='PBRMaterial'&&m.material.roughness>.6)m.material.bumpTexture=maps.normal;}
 // Match each facade's existing cutaway parent so trim never floats over rooms.
 for(let level=0;level<2;level++){const y=level*3.2,parent=groups['near_'+level];
  for(const x of [-5.7,1.7])for(let i=0;i<8;i++)box('corner-quoin',[.57,.21,.44],[x,y+.24+i*.39,1.01],trim,parent);
  for(const x of [-4.5,.5]){for(const dx of [-1.04,1.04])box('window-architrave',[.12,1.95,.16],[x+dx,y+1.85,1.19],trim,parent);box('window-drip-cap',[2.24,.09,.22],[x,y+2.83,1.18],trim,parent);}
  for(const x of [-5.9,1.9]){cyl('rainwater-pipe',.045,3.16,[x,y+1.61,1.28],steel,parent);for(const h of [.4,1.6,2.8])cyl('pipe-collar',.061,.065,[x,y+h,1.28],steel,parent);}
  const floor=groups['level_'+level];
  box('desk-screen',[.55,.36,.045],[-4.3,y+1.12,-3.95],rubber,floor);box('screen-stand',[.18,.06,.19],[-4.3,y+.95,-3.9],steel,floor);
  for(let i=0;i<6;i++)box('archive-binder',[.10,.30,.22],[.45+i*.13,y+1.62,-4.5],i%2?wood:steel,floor);
 }
 const roof=groups.roof;
 box('roof-hvac',[1.45,.65,.95],[-.1,6.96,-3.4],steel,roof);
 for(let i=0;i<12;i++)box('hvac-louver',[1.25,.022,.055],[-.1,6.72+i*.043,-2.905],rubber,roof);
 for(const x of [-.52,.3]){cyl('fan-housing',.27,.08,[x,7.32,-3.4],rubber,roof);for(let j=0;j<4;j++){box('fan-grille',[.53,.012,.017],[x,7.365,-3.4+j*.09-.135],steel,roof);}}
 cyl('antenna',.026,2.1,[1.3,7.65,-4.3],steel,roof);
 for(const y of [7.8,8.15])box('antenna-crossbar',[1.1,.025,.025],[1.3,y,-4.3],steel,roof);
 // Street furniture and context extend the original plinth into a neighborhood.
 box('surrounding-ground',[110,.20,110],[0,-.48,0],road);
 const windowMat=mat('distant-glass','#496574',.23,.3),facades=[mat('ochre-plaster','#a29479'),mat('gray-plaster','#89938b'),mat('brick-plaster','#977c69')];
 facades.forEach((m,i)=>{m.albedoTexture=i===2?maps.brick:maps.stone;m.bumpTexture=maps.normal;});
 for(let i=0;i<11;i++){const x=-30+i*6,h=5+(i*7%5)*1.6,z=-19-(i%3)*3;
  const facade=mat('background-facade-'+i,'#ffffff');facade.albedoColor=facades[i%3].albedoColor.clone();facade.bumpTexture=maps.normal;facade.albedoTexture=facades[i%3].albedoTexture.clone();facade.albedoTexture.uScale=i%3===2?4:3;facade.albedoTexture.vScale=h/(i%3===2?1.6:3);
  box('background-building',[5,h,5],[x,h/2-.3,z],facade);box('background-coping',[5.2,.18,5.2],[x,h-.25,z],trim);
  for(let y=1.3;y<h-.5;y+=1.65){
   box('background-floor-band',[5.08,.08,.13],[x,y-.62,z+2.54],trim);
   for(const dx of [-1.6,0,1.6]){box('background-window',[.72,.94,.03],[x+dx,y,z+2.52],windowMat);box('background-sill',[.90,.07,.18],[x+dx,y-.50,z+2.60],trim);box('background-mullion',[.04,.94,.05],[x+dx,y,z+2.55],steel);}
  }
  box('background-door',[.86,1.65,.04],[x,.53,z+2.53],wood);
  cyl('background-downpipe',.045,h,[x+2.35,h/2-.3,z+2.6],steel);
  box('background-roof-plant',[1.1,.55,.80],[x+1,h,z],steel);
 }
 for(const [x,z] of [[-10,-6],[-10,1],[-10,7],[10,-7],[10,6],[-15,-11],[14,-12]]){
  detailedTree(scene,root,[x,0,z],shadows,1,(x+z)*.3);
  box('planter',[1.8,.3,1.8],[x,.1,z],trim);
 }
 for(const x of [-9,9]){cyl('streetlight',.055,4.8,[x,2.4,4],steel);box('lamp-arm',[.8,.06,.07],[x+.35,4.75,4],steel);box('lamp-head',[.45,.10,.24],[x+.65,4.7,4],trim);}
 for(let i=0;i<5;i++){box('supply-crate',[.65,.55,.6],[-8.3+(i%2)*.72,.3+Math.floor(i/2)*.55,-1],wood);for(const dz of [-.24,.24])box('crate-band',[.67,.56,.035],[-8.3+(i%2)*.72,.3+Math.floor(i/2)*.55,-1+dz],steel);}
 // Vehicle fittings use normalized truck coordinates, independent of source units.
 for(const side of [-1,1]){box('truck-mirror-arm',[.3,.035,.035],[side*.97,1.68,-.66],steel,truck);box('truck-mirror',[.07,.22,.17],[side*1.1,1.7,-.66],rubber,truck);box('truck-step',[.25,.08,.75],[side*.92,.40,-.25],steel,truck);}
 box('truck-roof-rack',[1.55,.07,1.1],[0,2.44,.6],steel,truck);
 for(const x of [-.7,.7])box('rack-rail',[.045,.17,1.15],[x,2.53,.6],steel,truck);
 setDress({scene,root,groups,box,cyl,mesh,mat,maps,wood,steel,rubber,trim});
 dressCharacter(scene,person.rootNodes[0],shadows);
 return {root,maps};
}
