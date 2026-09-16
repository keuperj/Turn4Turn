import {detailedCar} from '../../webgpu-vehicles.js';
/** Authored furniture, street props and two different vehicle meshes for the HQ scene. */
export function setDress({scene,root,groups,box,cyl,mesh,mat,maps,wood,steel,rubber,trim}){
 const B=window.BABYLON,cream=mat('linen','#c4bba5'),fabric=mat('upholstery','#4e6864'),paper=mat('paper','#d9d2b8'),red=mat('painted-red','#8b3325');
 const glass=mat('car-glass','#294653',.16,.3),chrome=mat('wheel-alloy','#aeb7b6',.22,.85),lamp=mat('lamp-lens','#e3d7a6',.2),tail=mat('tail-lens','#952b23',.3);
 wood.albedoTexture=maps.timber;wood.albedoColor=B.Color3.White();wood.bumpTexture=maps.normal;
 for(let level=0;level<2;level++){
  const parent=groups['level_'+level],y=level*3.2;
  box('woven-rug',[2.25,.018,1.5],[-4.4,y+.13,-1],fabric,parent);
  for(let i=0;i<12;i++)box('rug-stripe',[.025,.004,1.42],[-5.42+i*.19,y+.142,-1],cream,parent);
  // Shelving, individual books and storage boxes against the west wall.
  for(const z of [-3.0,-1.7])box('bookcase-upright',[.36,1.85,.06],[-5.70,y+1.07,z],wood,parent);
  for(let k=0;k<4;k++){box('bookcase-shelf',[.40,.05,1.36],[-5.70,y+.25+k*.52,-2.35],wood,parent);for(let j=0;j<7;j++)box('book-spine',[.27,.22+(j%3)*.04,.085],[-5.67,y+.39+k*.52,-2.89+j*.16],j%3===0?red:j%3===1?fabric:cream,parent);}
  const chair=(x,z)=>{box('chair-seat',[.48,.10,.46],[x,y+.51,z],fabric,parent);box('chair-back',[.48,.47,.075],[x,y+.79,z+.22],fabric,parent);for(const dx of [-.19,.19])for(const dz of [-.17,.17])cyl('chair-leg',.024,.43,[x+dx,y+.29,z+dz],steel,parent);};
  chair(-4.3,-2.9);chair(-.8,-3.2);
  box('keyboard',[.36,.025,.13],[-4.3,y+.937,-3.58],rubber,parent);
  for(let i=0;i<3;i++)box('desk-paper',[.22,.004,.28],[-4.86+i*.015,y+.924+i*.006,-3.8],paper,parent);
  cyl('coffee-mug',.055,.10,[-3.78,y+.97,-3.75],cream,parent);
  cyl('desk-lamp-base',.09,.025,[-4.98,y+.94,-4],steel,parent);cyl('desk-lamp-stem',.018,.30,[-4.98,y+1.1,-4],steel,parent);cyl('desk-lamp-shade',.11,.08,[-4.95,y+1.25,-4],cream,parent);
  if(level===0){
   box('sofa-base',[1.72,.28,.70],[-4.45,y+.34,.30],fabric,parent);box('sofa-back',[1.75,.60,.15],[-4.45,y+.66,.62],fabric,parent);
   for(const x of [-5.26,-3.64])box('sofa-arm',[.17,.43,.70],[x,y+.50,.30],fabric,parent);
   for(const x of [-4.87,-4.03])box('sofa-cushion',[.77,.12,.54],[x,y+.53,.24],cream,parent);
   box('coffee-table',[1.15,.065,.52],[-4.4,y+.43,-.8],wood,parent);for(const x of [-4.85,-3.95])for(const z of [-.98,-.62])cyl('coffee-table-leg',.026,.28,[x,y+.26,z],steel,parent);
  }else{
   box('bed-frame',[1.65,.28,1.2],[-4.4,y+.32,.14],wood,parent);box('bed-mattress',[1.57,.19,1.12],[-4.4,y+.55,.14],cream,parent);box('folded-blanket',[.7,.035,1.1],[-4.8,y+.67,.14],fabric,parent);box('pillow',[.36,.13,.72],[-3.87,y+.70,.14],paper,parent);
  }
  box('kitchen-worktop',[1.25,.10,.58],[-.78,y+.88,-4.5],wood,parent);box('kitchen-cabinet',[1.17,.70,.53],[-.78,y+.47,-4.5],cream,parent);
  for(const x of [-1.07,-.49]){box('cabinet-door',[.55,.62,.025],[x,y+.48,-4.22],wood,parent);box('cabinet-handle',[.025,.13,.03],[x+.16,y+.59,-4.19],steel,parent);}
  box('table-top',[1.03,.065,.62],[-.86,y+.8,-2.55],wood,parent);for(const dx of [-.42,.42])for(const dz of [-.23,.23])cyl('table-leg',.025,.64,[-.86+dx,y+.46,-2.55+dz],steel,parent);
  box('wall-map',[.018,.67,1.02],[-2.08,y+1.8,-4],paper,parent);
  for(let i=0;i<6;i++)box('map-marking',[.02,.025,.8-i*.1],[-2.095,y+1.55+i*.08,-4],fabric,parent);
  cyl('indoor-planter',.16,.29,[-2.6,y+.29,-.2],red,parent);
  for(let i=0;i<7;i++){const stem=cyl('houseplant',.014,.55,[-2.6+Math.sin(i)*.1,y+.68,-.2+Math.cos(i)*.1],fabric,parent);stem.rotation.z=Math.sin(i)*.3;}
 }
 // Street objects: bins, pallets, drain gratings, barriers and a bicycle.
 box('dumpster',[1.35,.95,.80],[-8.3,.56,-3.2],fabric);box('dumpster-lid',[1.43,.08,.87],[-8.3,1.08,-3.2],steel);
 for(const x of [-8.85,-7.75])for(const z of [-3.48,-2.92])cyl('bin-caster',.085,.07,[x,.13,z],rubber).rotation.z=Math.PI/2;
 for(let p=0;p<3;p++)for(let j=0;j<5;j++)box('pallet-slat',[1.15,.045,.14],[-7.7,.10+p*.13,-5+j*.19],wood);
 for(const z of [-6,2,7]){box('drain-surround',[.38,.025,.75],[8,.016,z],steel);for(let i=0;i<8;i++)box('drain-slot',[.30,.006,.045],[8,.031,z-.3+i*.085],rubber);}
 cyl('hydrant',.13,.65,[8.5,.35,2.5],red);cyl('hydrant-cap',.17,.08,[8.5,.72,2.5],red);const nozzle=cyl('hydrant-nozzle',.08,.43,[8.5,.52,2.5],steel);nozzle.rotation.z=Math.PI/2;
 for(let i=0;i<4;i++){const x=3+i*.5;box('barrier-foot',[.30,.10,.60],[x,.10,-8],rubber);cyl('barrier-post',.035,.90,[x,.55,-8],steel);}
 box('barrier-rail',[1.65,.14,.10],[3.75,.96,-8],cream);
 const bike=new B.TransformNode('bicycle',scene);bike.parent=root;bike.position.set(-6.7,.05,2.3);bike.rotation.y=.2;
 for(const z of [-.53,.53]){const wheel=mesh(B.MeshBuilder.CreateTorus('bicycle-wheel',{diameter:.62,thickness:.045,tessellation:24},scene),[0,.34,z],rubber,bike);wheel.rotation.z=Math.PI/2;for(let k=0;k<8;k++){const spoke=box('bicycle-spoke',[.014,.59,.014],[0,.34,z],chrome,bike);spoke.rotation.x=k*Math.PI/4;}}
 for(const [z,tilt] of [[-.25,-.7],[.22,.7],[.05,-.3]]){const tube=cyl('bicycle-frame',.025,.75,[0,.56,z],red,bike);tube.rotation.x=tilt;}
 box('bicycle-saddle',[.20,.06,.27],[0,.94,.18],rubber,bike);box('bicycle-handlebar',[.48,.025,.035],[0,1.0,-.42],steel,bike);
 const car=(...args)=>detailedCar({scene,root,box,cyl,mesh,mat,maps,rubber,chrome,glass,cream,steel,lamp,tail},...args);
 car('red-hatchback',false,[-3.8,0,6.6],-.22,maps.carRed);
 car('blue-estate',true,[7,0,-5.1],.14,maps.carBlue);
}
