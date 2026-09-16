/** Scenario dressing is visual only; authoritative footprints and fog stay in environment.js. */
import * as G from './rendering.js';
import {detailedCar} from './webgpu-vehicles.js';
import {detailedTree} from './webgpu-nature.js';
const B=window.BABYLON;
export const profiles={
 urban:{finish:'brick',color:0xb8a18e,roof:0x64716f,kind:'apartments'},
 streets:{finish:'brick',color:0xc2ae95,roof:0x686d70,kind:'shops'},
 factory:{finish:'cladding',color:0x91a49d,roof:0x616e6b,kind:'works'},
 train_station:{finish:'brick',color:0xbea285,roof:0x637777,kind:'depot'},
 airport:{finish:'cladding',color:0xc0ccca,roof:0x75989d,kind:'hangars'},
 woods:{finish:'wood',color:0x9b896c,roof:0x53644c,kind:'cabins'},
 farm:{finish:'wood',color:0xb79271,roof:0x826955,kind:'barns'},
};
export function profileFor(theme){return profiles[theme]||profiles.urban;}
function context(view,root){
 const scene=view.nativeScene,maps=view.qualityMaps;
 const mat=(name,color,roughness=.7,metallic=0)=>{const m=view.material(color,metallic>.4?'metal':'paint').native;return m;};
 const mesh=(m,pos,material,parent=root)=>{m.parent=parent;m.position.copyFromFloats(...pos);m.material=material;m.isPickable=false;m.receiveShadows=true;view.shadows.addShadowCaster(m,false);return m;};
 const box=(name,size,pos,material,parent=root)=>mesh(B.MeshBuilder.CreateBox(name,{width:size[0],height:size[1],depth:size[2]},scene),pos,material,parent);
 const cyl=(name,r,h,pos,material,parent=root)=>mesh(B.MeshBuilder.CreateCylinder(name,{diameter:r*2,height:h,tessellation:20},scene),pos,material,parent);
 // Per-model paint must not mutate the game's cached materials.
 const paint=(name,color,roughness=.7,metallic=0)=>{const key='vehicle:'+name;let m=view.detailMaterials?.get(key);if(!m){view.detailMaterials??=new Map();m=new B.PBRMaterial(key,scene);m.albedoColor=B.Color3.FromHexString(color);m.roughness=roughness;m.metallic=metallic;view.detailMaterials.set(key,m);}return m;};
 return {scene,root,box,cyl,mesh,mat:paint,maps,rubber:view.material(0x222827,'rubber').native,chrome:mat('alloy',0xb5bdba,.25,.8),glass:view.material(0x284551,'paint').native,cream:mat('linen',0xd2cbbb),steel:mat('steel',0x586865,.4,.8),lamp:mat('lens',0xeee0b0),tail:mat('tail',0xac3327)};
}
/** Return true when the low-detail primitive is replaced entirely. */
export function detailedProp(view,p,group){
 if(p.kind==='car'){
  const ctx=context(view,group.native),estate=(p.variant||0)%2===1;
  const native=detailedCar(ctx,estate?'blue-estate':'red-hatchback',estate,[0,0,0],0,estate?ctx.maps.carBlue:ctx.maps.carRed);
  // Normalize the actual geometry, mirrors included, into the server footprint.
  native.computeWorldMatrix(true);const bounds=native.getHierarchyBoundingVectors(true),span=bounds.max.subtract(bounds.min);
  native.scaling.set(p.width*.94/span.x,1,p.depth*.94/span.z);
  for(const m of native.getChildMeshes()){m.metadata={pickOwner:group};m.isPickable=true;}
  group.userData.structure=p.id;view.pickables.push(group);return true;
 }
 if(['tree','tree_oak','tree_birch','tree_pine','bush'].includes(p.kind)){
  const detail=detailedTree(view.nativeScene,null,[0,0,0],view.shadows,1,p.variant||0,p.kind),owner=new G.Group(detail);group.add(owner);
  owner.scale.setScalar(p.kind==='bush'?.20:.6);owner.userData.structure=p.id;view.pickables.push(owner);
  for(const m of detail.getChildMeshes()){m.metadata={pickOwner:owner};m.isPickable=m.name==='tree-branches';}
  return true;
 }
 return false;
}
/** Additional fittings use the original models' local coordinates before footprint scaling. */
export function propFittings(view,p,group){
 const metal=view.material(0xa3aaa3,'metal'),dark=view.material(0x293633,'rubber'),wood=view.material(0xb4a083,'wood'),paint=view.material(p.color||0x899990,'metal');
 const box=(name,w,h,d,x,y,z,mat=metal)=>{const m=view.box(group,w,h,d,x,y,z,mat);m.native.name=name;return m;};
 if(['truck','tractor'].includes(p.kind)){
  for(const side of [-1,1]){box('cab-step',.13,.07,.35,side*.46,.25,-.15);box('door-handle',.025,.035,.13,side*.38,.66,-.32);}
  if(p.kind==='truck'){
   for(let j=0;j<6;j++)for(const side of [-1,1])box('cargo-slats',.028,.055,.76,side*.405,.47+j*.06,.49,wood);
   for(let j=0;j<3;j++){box('cargo-crate',.22,.28,.22,(j%2-.5)*.29,.85,.33+Math.floor(j/2)*.28,wood);box('crate-strap',.23,.29,.018,(j%2-.5)*.29,.85,.33+Math.floor(j/2)*.28,dark);}
  }else{box('tractor-exhaust',.045,.66,.045,.19,1.0,-.32,dark);box('tractor-seat',.33,.10,.27,0,.72,.22,dark);for(let j=0;j<8;j++)box('engine-louver',.03,.22,.018,-.23+j*.065,.56,-.465,dark);}
 }
 if(p.kind==='train'){
  // A service locomotive variant has a distinct bonnet; passenger stock retains its cab.
  if((p.variant||0)%2){box('locomotive-bonnet',1.30,.60,.25,0,.92,-2.29,paint);for(let k=0;k<9;k++)box('locomotive-grille',.035,.35,.025,-.48+k*.12,1.0,-2.43,dark);}
  box('train-coupler',.20,.14,.18,0,.48,-2.39,dark);
  for(const side of [-1,1]){box('cab-handrail',.035,1.15,.035,side*.74,1.17,-2.34);box('cab-step',.40,.055,.16,side*.56,.53,-2.36);}

  box('train-stripe',1.69,.10,4.5,0,1.05,0,view.material(0xc2a04b,'metal'));
  for(const side of [-1,1])for(const z of [-1.65,1.65]){
   box('train-door',.035,1.43,.43,side*.848,1.3,z,paint);box('door-window',.04,.49,.30,side*.87,1.61,z,view.material(0x294751));
   box('bogie',.22,.19,.82,side*.68,.43,z,dark);
   for(let k=0;k<5;k++)box('suspension-spring',.035,.13,.028,side*.82,.44,z-.15+k*.075);
  }
  for(let z=-1.5;z<2;z+=1.25){box('roof-vent',1.05,.17,.62,0,2.39,z,paint);for(let i=0;i<7;i++)box('vent-grille',.8,.018,.027,0,2.49,z-.22+i*.07,dark);}
  for(const side of [-1,1]){box('headlamp',.22,.17,.035,side*.53,.97,-2.30,view.material(0xe6d8a1));box('windscreen-wiper',.018,.37,.04,side*.35,1.63,-2.315,dark);}
 }
 if(p.kind==='aircraft'){
  for(const side of [-1,1])for(let j=0;j<9;j++)box('cabin-window',.02,.10,.10,side*.336,.85,-.65+j*.21,view.material(0x294955));
  for(const side of [-1,1]){box('wing-stripe',.30,.012,.55,side*1.25,.758,.25,paint);box('flap-seam',.85,.012,.015,side*.94,.76,.49,dark);box('landing-strut',.028,.34,.028,side*.70,.3,.5);}
  box('aircraft-door',.025,.31,.18,.345,.72,-.90,paint);
 }
 if(['tank','silo','container','pipes'].includes(p.kind)){
  const h=p.kind==='silo'?3.2:1.4;
  for(let y=.2;y<h;y+=.25)box('access-ladder-rung',.30,.025,.05,0,y,p.kind==='container'?1.47:.47);
  for(const side of [-1,1])box('ladder-rail',.025,h,.04,side*.17,h/2,p.kind==='container'?1.47:.47);
  if(p.kind==='container')for(const side of [-1,1]){box('locking-bar',.03,1.45,.035,side*.24,.86,-1.465);box('locking-handle',.15,.03,.04,side*.24,.76,-1.485);}
 }
 if(p.kind==='hay')for(const x of [-.25,.25])box('bale-binding',.035,.72,.70,x,.42,0,wood);
 if(p.kind==='trash'){box('bin-lid',.39,.045,.39,0,.64,0);box('bin-handle',.16,.03,.035,0,.68,0,dark);}
}
export function background(view,state){
 const profile=profileFor(state.theme),n=state.size,c=(n-1)/2,natural=['woods','farm'].includes(state.theme);
 const parent=new G.Group();view.terrain.add(parent);parent.native.name='scenario-background-'+state.theme;
 view.box(parent,n+70,.25,n+70,c,-.72,c,natural?view.groundMat:view.pavedGroundMat).native.name='background-ground';
 const wall=view.material(profile.color,profile.finish),roof=view.material(profile.roof,'cladding'),glass=view.material(0x36535d,'paint'),wood=view.material(0x9b896e,'wood');
 for(let i=0;i<12;i++){
  // All silhouettes remain outside the playable square, on two sides.
  const x=i<8?-7+i*(n+14)/7:n+8+(i%2)*4,z=i<8?-9-(i%3)*3:(i-8)*(n+5)/3;
  if(state.theme==='woods'||(natural&&i%2===0)){detailedTree(view.nativeScene,parent.native,[x,0,z],view.shadows,.85,i,i%3===0?'tree_pine':'tree_oak');continue;}
  const w=profile.kind==='hangars'?6:4,d=4,h=natural?3:['works','depot','hangars'].includes(profile.kind)?4:4+(i%3)*2;
  view.box(parent,w,h,d,x,h/2-.5,z,wall);view.box(parent,w+.18,.18,d+.18,x,h-.4,z,roof);
  if(natural){for(const side of [-1,1]){const slope=view.box(parent,w+.25,.15,d*.6,x,h-.04,z+side*d*.24,roof);slope.rotation.x=side*.4;}view.box(parent,1.4,2.2,.045,x,.65,z+d/2+.03,wood);}
  else if(['works','hangars','depot'].includes(profile.kind)){
   view.box(parent,w*.65,2.8,.05,x,1,z+d/2+.03,roof);
   for(let k=0;k<10;k++)view.box(parent,w*.65,.025,.035,x,-.25+k*.28,z+d/2+.07,glass);
   view.box(parent,.7,1,.6,x+w*.25,h+.1,z,roof);
   if(state.theme==='factory')view.box(parent,.5,3,.5,x-w*.3,h+1,z,wall);
  }else for(let y=1;y<h-.6;y+=1.5)for(const dx of [-1.3,0,1.3]){
   view.box(parent,.70,.90,.05,x+dx,y,z+d/2+.03,glass);view.box(parent,.84,.08,.20,x+dx,y-.48,z+d/2+.08,roof);
  }
  view.box(parent,.08,h,.08,x-w/2+.15,h/2-.5,z+d/2+.1,roof);
  // Yard freight, hay and utility cabinets match the scenario's architecture.
  if(i%2===0){const cargo=view.box(parent,1.1,.85,1.1,x+w/2+1,.02,z, natural?wood:roof);cargo.native.name='background-'+profile.kind+'-cargo';for(let k=0;k<5;k++)view.box(parent,1.12,.055,1.12,x+w/2+1,-.3+k*.15,z,wood);}
 }
}
/** Small edge furnishings follow visible floors and never create gameplay blockers. */
export function furnish(view,b,level,theme,parent){
 const profile=profileFor(theme),y=level*3,x=b.x+.12,z=b.y+b.depth-1.15;
 const wood=view.material(0xb9a68b,'wood'),metal=view.material(profile.roof,'metal'),cloth=view.material(0x60786d),paper=view.material(0xd8d2bd);
 const box=(name,w,h,d,dx,dy,dz,mat)=>{const m=view.box(parent,w,h,d,x+dx,y+dy,z+dz,mat);m.native.name=name;return m;};
 if(['factory','airport','train_station'].includes(theme)){
  box('workbench',.48,.08,.95,0,.82,0,metal);for(const dz of [-.39,.39])box('bench-leg',.06,.76,.06,0,.4,dz,metal);
  for(let j=0;j<4;j++){box('toolbox',.31,.16,.15,0,.94,-.30+j*.2,wood);box('toolbox-handle',.12,.035,.035,0,1.04,-.30+j*.2,metal);}
  box('control-console',.38,.30,.26,0,1.0,.6,metal);box('console-display',.025,.17,.19,.20,1.03,.6,cloth);
 }else{
  box('upholstered-seat',.52,.28,.9,0,.32,0,cloth);box('seat-back',.10,.48,.94,-.24,.61,0,wood);
  for(const dz of [-.23,.23])box('seat-cushion',.42,.10,.41,.04,.51,dz,paper);
  box('side-table',.42,.06,.35,0,.62,.85,wood);for(const dx of [-.15,.15])box('table-leg',.035,.57,.035,dx,.31,.85,metal);
  for(let j=0;j<3;j++)box('stacked-books',.27,.035,.22,0,.67+j*.04,.85,j%2?cloth:paper);
 }
}
