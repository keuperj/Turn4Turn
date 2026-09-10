import * as T from 'three';
import {RoundedBoxGeometry} from './vendor/geometries/RoundedBoxGeometry.js';
import {GLTFExporter} from './vendor/exporters/GLTFExporter.js';
const scene=new T.Scene(),loader=new T.TextureLoader();
const concrete=await loader.loadAsync('/assets/concrete.png'),ground=await loader.loadAsync('/assets/ground.png');
for(const t of [concrete,ground]){t.colorSpace=T.SRGBColorSpace;t.wrapS=t.wrapT=T.RepeatWrapping;}
const stone=new T.MeshStandardMaterial({map:concrete,color:'#c5b5a0',roughness:.88}),paving=new T.MeshStandardMaterial({map:concrete,color:'#707d80',roughness:.92});
const dirt=new T.MeshStandardMaterial({map:ground,color:'#8e9278',roughness:1});
const metal=new T.MeshStandardMaterial({color:'#34474b',metalness:.7,roughness:.3}),brass=new T.MeshStandardMaterial({color:'#bd8d48',metalness:.7,roughness:.35});
const plaster=new T.MeshStandardMaterial({map:concrete,color:'#e2d1ad',roughness:.85});
const wood=new T.MeshStandardMaterial({color:'#795139',map:concrete,roughness:.65});
const glass=new T.MeshStandardMaterial({color:'#80b7c6',metalness:.25,roughness:.15,transparent:true,opacity:.42});
function group(name,parent=scene){const g=new T.Group();g.name=name;parent.add(g);return g;}
function box(parent,name,size,pos,mat,r=.035){const m=new T.Mesh(new RoundedBoxGeometry(...size,2,Math.min(r,...size.map(v=>v/3))),mat);m.name=name;m.position.set(...pos);parent.add(m);return m;}
function cylinder(parent,name,r,h,pos,mat){const m=new T.Mesh(new T.CylinderGeometry(r,r,h,24),mat);m.name=name;m.position.set(...pos);parent.add(m);return m;}
const site=group('Site');box(site,'foundation',[23,.3,20],[0,-.25,0],dirt,.08);
for(let x=-10;x<=10;x+=2)for(let z=-8;z<=8;z+=2)box(site,'paving',[1.97,.09,1.97],[x,-.065,z],paving,.018);
for(let z=-8;z<=8;z+=2)box(site,'road_marking',[.09,.012,.85],[6,.001,z],new T.MeshStandardMaterial({color:'#cbbc8b',roughness:.8}),.005);
const groundFloor=group('level_0'),upper=group('level_1'),roof=group('roof');
for(let level=0;level<2;level++){
 const floor=level?upper:groundFloor,y=level*3.2,near=group('near_'+level,floor);
 box(floor,'floor_slab',[8,.18,6],[-2,y+.01,-2],plaster,.03);
 // Full rear and west walls; front and east are assembled around real openings.
 box(floor,'rear_wall',[8,2.95,.20],[-2,y+1.65,-5],stone);
 box(floor,'west_wall',[.20,2.95,6],[-6,y+1.65,-2],stone);
 for(const x of [-5.7,-3.3,-.7,1.7])box(near,'facade_pier',[.50,3.12,.38],[x,y+1.65,1],plaster,.065);
 for(const x of [-4.5,0.5]){
  box(near,'window_sill',[1.95,.13,.56],[x,y+.9,1],plaster);
  box(near,'window_apron',[1.95,.70,.22],[x,y+.5,1],stone);
  box(near,'window_header',[1.95,.42,.3],[x,y+2.96,1],plaster);
  box(near,'glazing',[1.82,1.65,.055],[x,y+1.8,1],glass,.008);
  for(const dx of [-.92,0,.92])box(near,'window_mullion',[.055,1.75,.11],[x+dx,y+1.8,1.02],metal,.008);
  box(near,'window_crossbar',[1.9,.05,.11],[x,y+1.8,1.02],metal,.008);
 }
 box(near,'door_lintel',[2.1,.48,.35],[-2,y+2.94,1],plaster);
 const door=group('door_'+level,near);door.position.set(-2.94,y+.16,1);
 box(door,'door_leaf',[1.84,2.49,.12],[.94,1.25,0],wood);
 for(const dx of [.45,1.4])for(const dy of [.62,1.75])box(door,'raised_panel',[.72,.88,.05],[dx,dy,.075],wood,.03);
 cylinder(door,'door_handle',.035,.28,[1.65,1.25,.17],brass);
 if(level)door.rotation.y=-.18;
 for(const z of [-4.8,-2.7,-.4,.8])box(near,'east_pier',[.38,3.1,.35],[2,y+1.65,z],plaster,.045);
 for(const z of [-3.75,-1.55]){
  box(near,'east_sill',[.46,.95,1.85],[2,y+.62,z],stone);
  box(near,'east_header',[.30,.48,1.85],[2,y+2.94,z],plaster);
  box(near,'east_glass',[.055,1.62,1.85],[2,y+1.88,z],glass);
  box(near,'east_mullion',[.10,1.7,.055],[2.03,y+1.88,z],metal,.008);
 }
 for(const z of [-5,1])box(floor,'cornice',[8.25,.17,.38],[-2,y+3.13,z],plaster);
 // An internal wall and an open doorway divide the two furnished rooms.
 for(const z of [-4,-.25])box(floor,'room_partition',[.13,2.9,z===-4?1.9:2.3],[-2,y+1.6,z],plaster);
 box(floor,'internal_door_lintel',[.15,.5,1.3],[-2,y+2.85,-2.45],wood);
 box(floor,'desk',[1.65,.13,.78],[-4.3,y+.85,-3.8],wood);
 for(const x of [-4.95,-3.65])for(const z of [-4.05,-3.55])cylinder(floor,'desk_leg',.035,.75,[x,y+.45,z],metal);
 box(floor,'cabinet',[1.2,1.35,.5],[.9,y+.80,-4.55],wood);
 for(let k=0;k<4;k++)box(floor,'drawer',[1.12,.26,.03],[.9,y+.35+k*.30,-4.28],plaster);
 for(let i=0;i<12;i++)box(floor,'stairs',[.95,(i+1)*.26,.22],[.85,y+(i+1)*.13,-2.9+i*.22],stone,.02);
}
box(roof,'roof_deck',[8.4,.22,6.4],[-2,6.52,-2],metal,.08);
for(const z of [-5.15,1.15])box(roof,'parapet',[8.3,.45,.15],[-2,6.8,z],plaster);
for(const x of [-6.15,2.15])box(roof,'parapet',[.15,.45,6.3],[x,6.8,-2],plaster);
for(const x of [-4,-3.4]){cylinder(roof,'vent',.19,.7,[x,6.98,-3.3],metal);cylinder(roof,'vent_cap',.27,.1,[x,7.36,-3.3],metal);}
const props=group('Site_details');
for(let i=0;i<3;i++){
 const x=-7.7+i*.1,z=3.4+i*.85;
 cylinder(props,'barrel',.34,.95,[x,.48,z],metal);
 for(const y of [.14,.8])cylinder(props,'barrel_rim',.355,.045,[x,y,z],brass);
}
for(const x of [-8,8]){
 cylinder(props,'bollard',.10,.8,[x,.4,6],metal);cylinder(props,'bollard_cap',.12,.1,[x,.84,6],brass);
}
for(const z of [-6,6]){
 const bench=group('Bench',props);for(let j=0;j<4;j++)box(bench,'bench_slat',[2,.07,.10],[3,.55,z+j*.13],wood);
 for(const x of [2.2,3.8])box(bench,'bench_leg',[.07,.5,.55],[x,.26,z+.2],metal);
}
window.exportScene=async()=>{
 const data=await new GLTFExporter().parseAsync(scene,{binary:true,onlyVisible:false});
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data]));a.download='courtyard.glb';a.click();return await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.readAsDataURL(new Blob([data]));});
};
window.exportCharacter=async()=>{
 const {FBXLoader}=await import('./vendor/loaders/FBXLoader.js');
 const root=await new FBXLoader().loadAsync('assets/Soldier_Male.fbx');
 console.log('Character clips',root.animations.map(c=>c.name));
 root.traverse(o=>{if(o.isMesh){const convert=m=>new T.MeshStandardMaterial({color:m.color.clone().multiplyScalar(m.color.g < .1 ? 25 : 1), map:m.map,roughness:.8});o.material=Array.isArray(o.material)?o.material.map(convert):convert(o.material);}});
 const data=await new GLTFExporter().parseAsync(root,{binary:true,animations:root.animations});
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data]));a.download='character.glb';a.click();return await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.readAsDataURL(new Blob([data]));});
};window.authorReady=true;
