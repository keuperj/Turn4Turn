/** @fileoverview Build visual props, buildings, portals, and architectural details. */
import * as G from './rendering.js';
import {woodlandProp} from './woodland.js';
import {detailedProp,propFittings,profileFor,furnish} from './webgpu-scenery.js';

// Theme props share the footprints used by Python collision/pathfinding.
/** Add one scenery prop and its visual details to the battlefield. */
export function addProp(view, p, parent=view.terrain) {
  if(p.destroyed){view.box(parent,p.width*.8,.12,p.depth*.8,p.x+(p.width-1)/2,.06,p.y+(p.depth-1)/2,0x45443e);return;}
  const group=new G.Group();parent.add(group);
  const x=p.x+(p.width-1)/2,z=p.y+(p.depth-1)/2;
  group.position.set(x,0,z);
  if(['tree','tree_oak','tree_pine','tree_birch','bush','flowerbed','sign','lamp','trash','bench'].includes(p.kind))group.rotation.y=(p.variant||0)*Math.PI/2;
  if(p.quarter_turn)group.rotation.y=p.quarter_turn*Math.PI/2;
  const localProp=p.quarter_turn%2?{...p,width:p.depth,depth:p.width}:p;
  const enhancedProp=(p.woodland&&woodlandProp(view,p,group))||view.transport?.add(p,group)||(view.renderer==='webgpu'&&detailedProp(view,localProp,group));
  const box=(w,h,d,x,y,z,c)=>view.box(group,w,h,d,x,y,z,c);
  const color=p.color||'#91a5a1',metal=view.material(0x566164,'metal'),glass=view.material(0x294957,'glass'),rubber=view.material(0x202524,'rubber');
  const cylinder=(r,h,x,y,z,c,finish='paint')=>{const m=new G.Mesh(new G.CylinderGeometry(r,r,h,12),typeof c==='object'?c:view.material(c,finish));m.position.set(x,y,z);m.receiveShadow=true;if(r>.16&&h>.2)m.castShadow=true;group.add(m);return m;};
  const shape=(w,h,d,x,y,z,c,inset=.06,front=inset,back=inset)=>{const m=new G.Mesh(new G.BeveledBoxGeometry(w,h,d,inset,front,back),typeof c==='object'?c:view.material(c));m.position.set(x,y,z);m.castShadow=m.receiveShadow=true;group.add(m);return m;};
  const wheel=(x,z,r=.19)=>{const tire=cylinder(r,.14,x,r,z,rubber);tire.rotation.z=Math.PI/2;const hub=cylinder(r*.48,.151,x,r,z,metal);hub.rotation.z=Math.PI/2;};
  if(!enhancedProp)switch(p.kind){
    case 'cow': case 'sheep': case 'pig': {
      const cow=p.kind==='cow',pig=p.kind==='pig',coat=pig?0xc59283:cow?0xe4d9ba:0xd4cbb2;
      const length=cow?1.5:.7,height=cow?.7:.38;
      box(.38,height,length,0,height*.9,0,coat);
      box(.28,height*.65,.30,0,height*1.25,-length*.48,coat);
      for(const side of [-1,1])for(const end of [-1,1])box(.07,height*.65,.07,side*.13,height*.32,end*length*.32,0x635448);
      if(cow)box(.39,.3,.42,0,height,0,0x443e37);
      break;
    }
    case 'car': case 'truck': case 'ambulance': case 'tractor': {
      const truck=['truck','ambulance'].includes(p.kind),tractor=p.kind==='tractor';
      const body=view.material(color,'paint'),accent=view.material(((p.x*31+p.y*17)%2)?0xd7d0b4:0x596b6d,'paint');
      if(tractor){
        shape(.76,.38,.92,0,.30,-.02,body,.08,.12,.05);shape(.58,.48,.43,0,.62,-.20,body,.10,.08,.07);
        box(.08,.65,.08,.24,.83,.14,metal);box(.54,.06,.38,0,.70,.29,accent);
        for(const side of [-1,1]){wheel(side*.43,.25,.29);wheel(side*.40,-.39,.18);}
      }else{
        shape(.88,.38,1.86,0,.27,0,body,.07,.15,.11);
        if(truck){
          shape(.74,.53,.72,0,.57,-.47,body,.12,.17,.07);box(.78,.43,.78,0,.48,.49,accent);
          for(const side of [-1,1])box(.035,.26,.68,side*.405,.69,.49,metal);
        }else shape(.74,.50,.96,0,.56,-.02,body,.14,.20,.14);
        const front=truck?-.72:-.50,sideDepth=truck?.52:.70;
        box(.58,.27,.025,0,.69,front,glass);box(.025,.27,sideDepth,-.365,.69,-.06,glass);box(.025,.27,sideDepth,.365,.69,-.06,glass);
        if(!truck)box(.55,.24,.025,0,.68,.49,glass);
        for(const side of [-1,1])for(const end of [-1,1])wheel(side*.45,end*.60,.20);
        box(.64,.055,.10,0,.23,-.96,metal);box(.64,.055,.10,0,.23,.96,metal);
        for(const s of [-1,1]){box(.17,.085,.035,s*.27,.38,-.935,0xf4e0b3);box(.15,.075,.035,s*.27,.36,.935,0xa64035);}
        if((p.x+p.y)%2)for(const side of [-1,1])box(.025,.075,1.20,side*.446,.36,.05,accent);
      }
      if(view.renderer==='webgpu'){
        for(const side of [-1,1]){box(.15,.035,.035,side*.46,.75,-.35,metal);box(.055,.12,.10,side*.54,.79,-.35,metal);box(.03,.035,.14,side*.45,.52,.08,metal);}
        for(let i=0;i<7;i++)box(.045,.12,.02,-.21+i*.07,.36,-.945,rubber);
        for(const side of [-1,1])for(const end of [-1,1])for(let i=0;i<12;i++){const a=i*Math.PI/6;box(.15,.027,.027,side*.45,.20+Math.sin(a)*.196,end*.60+Math.cos(a)*.196,rubber);}
      }
      break;
    }
    case 'bus': {
      box(2.5,1.9,6,0,1.4,0,view.material(color));
      box(2.5,.18,6,0,2.42,0,metal);
      for(const side of [-1,1]){
        for(let z=-2.3;z<=2.3;z+=.75)box(.025,.65,.58,side*1.26,1.8,z,glass);
        for(const z of [-1.9,1.9])wheel(side*1.14,z,.42);
      }
      box(2.2,.75,.03,0,1.8,-3.01,glass);break;
    }
    case 'train': {
      box(1.65,.36,4.7,0,.45,0,metal);box(1.65,1.7,4.55,0,1.35,0,view.material(color,'metal'));
      box(1.58,.18,4.6,0,2.24,0,0xc5c9bd);
      for(let i=-1.5;i<=1.5;i+=.75)for(const s of [-1,1])box(.025,.55,.48,s*.84,1.62,i,glass);
      box(1.3,.6,.025,0,1.65,-2.29,glass);
      for(const s of [-1,1])for(const z of [-1.65,1.65])wheel(s*.74,z,.30);
      for(const z of [-2.4,2.4])box(.35,.2,.25,0,.5,z,metal);
      break;
    }
    case 'aircraft': {
      const fuselage=new G.Mesh(new G.CapsuleGeometry(.34,2.7,6,12),view.material(0xcbd1c9));fuselage.rotation.x=Math.PI/2;fuselage.position.y=.72;fuselage.castShadow=true;group.add(fuselage);
      box(2.85,.10,.70,0,.7,.25,0xbcc7c5);box(1.35,.07,.45,0,.85,1.5,0xbcc7c5);
      box(.08,.8,.6,0,1.1,1.4,0x667e83);box(.36,.18,.60,0,.96,-.9,glass);
      for(const s of [-1,1]){const engine=cylinder(.15,.6,s*.8,.5,.15,metal);engine.rotation.x=Math.PI/2;wheel(s*.7,.5,.14);}wheel(0,-1.05,.13);
      break;
    }
    case 'container':
      box(.94,1.7,2.9,0,.85,0,view.material(color,'metal'));
      for(let z=-1.35;z<1.5;z+=.25)for(const s of [-1,1])box(.025,1.6,.045,s*.48,.85,z,0x687d79);
      break;
    case 'tank': case 'silo':
      cylinder(.45,p.kind==='silo'?3.4:1.5,0,p.kind==='silo'?1.7:.75,0,0xa4aba4);
      {const cap=new G.Mesh(new G.ConeGeometry(.48,.4,16),view.material(0x89978e));cap.position.y=p.kind==='silo'?3.6:1.7;group.add(cap);}break;
    case 'pipes':
      for(let i=0;i<3;i++){const c=cylinder(.13,1.8,-.26+i*.26,.22,0,metal);c.rotation.x=Math.PI/2;}break;
    case 'hay':
      {const hay=cylinder(.40,.8,0,.42,0,0xc3a658);hay.rotation.z=Math.PI/2;}break;
    case 'bench': {
      const timber=view.material((p.variant||0)%2?0x79583f:0x93734f,'wood');
      for(const offset of [-.14,0,.14])box(.84,.055,.10,0,.46,offset,timber);
      for(const offset of [.52,.68])box(.84,.055,.09,0,offset,.21,timber);
      for(const s of [-1,1])box(.065,.40,.34,s*.32,.20,0,metal);break;
    }
    case 'tree': case 'tree_oak': {
      cylinder(.10,1.9,0,.95,0,(p.variant||0)%2?0x73563a:0x67513a,'wood');
      for(let j=0;j<6;j++){const m=new G.Mesh(new G.IcosahedronGeometry(.42+(j%3)*.09,1),view.material([0x3f5735,0x526b3e,0x6d7d47][(j+(p.variant||0))%3]));m.position.set(Math.sin(j*2.4)*.28,1.65+(j%3)*.19,Math.cos(j*2.4)*.28);m.castShadow=true;group.add(m);}break;
    }
    case 'tree_pine':
      cylinder(.085,2.5,0,1.25,0,0x5e4933,'wood');
      for(let j=0;j<4;j++){const crown=new G.Mesh(new G.ConeGeometry(.62-j*.09,1.15,10),view.material([0x304c35,0x3c5a3c,0x486746][j%3]));crown.position.y=1.25+j*.48;crown.castShadow=true;group.add(crown);}break;
    case 'tree_birch':
      cylinder(.075,2.25,0,1.12,0,0xd4d0b6,'wood');
      for(let j=0;j<4;j++){const crown=new G.Mesh(new G.IcosahedronGeometry(.34+(j%2)*.08,1),view.material([0x70834a,0x8b9457,0x5f7845][j%3]));crown.position.set(Math.sin(j*1.9)*.18,1.75+j*.18,Math.cos(j*1.9)*.18);group.add(crown);}break;
    case 'bush':
      for(let j=0;j<4;j++){const shrub=new G.Mesh(new G.IcosahedronGeometry(.24+(j%2)*.08,1),view.material([0x3f603c,0x587446,0x6e8150][(j+(p.variant||0))%3]));shrub.position.set(Math.sin(j*1.8)*.22,.25+(j%2)*.13,Math.cos(j*1.8)*.20);group.add(shrub);}break;
    case 'flowerbed':
      box(.92,.12,.48,0,.06,0,view.material(0x725d3f,'soil'));for(let j=0;j<7;j++){const flower=new G.Mesh(new G.SphereGeometry(.035,8,6),view.material([0xd7c66a,0xa96058,0xc6c0dc][j%3]));flower.position.set(-.36+j*.12,.18,(j%2-.5)*.20);group.add(flower);}break;
    case 'sign': {
      cylinder(.035,1.35,0,.67,0,metal);
      if(p.sign){
        if(p.sign==='STOP'){
          const plate=new G.Mesh(new G.CylinderGeometry(.33,.33,.05,8),view.material(0xae4035));plate.rotation.x=Math.PI/2;plate.position.y=1.3;group.add(plate);
        }else box(.50,.56,.055,0,1.3,0,view.material(0x35618e));
        const text=view.label(p.sign,'#fff5df',p.sign==='STOP'?.48:.30);text.position.set(0,1.3,-.055);group.add(text);
      }else{box(.72,.42,.055,0,1.22,0,view.material(p.color,'paint'));box(.58,.035,.06,0,1.22,.032,view.material(0xe1dbc4));}
      break;
    }
    case 'lamp':
      cylinder(.035,2.5,0,1.25,0,metal);box(.42,.035,.035,.18,2.42,0,metal);{const lamp=new G.Mesh(new G.SphereGeometry(.12,10,8),view.material(0xe9dca8));lamp.position.set(.36,2.35,0);group.add(lamp);}break;
    case 'traffic_light':
      cylinder(.045,2.8,0,1.4,0,metal);
      box(.26,.72,.20,0,2.48,0,0x24302e);
      for(let i=0;i<3;i++){
        const light=new G.Mesh(new G.SphereGeometry(.075,10,8),view.material([0xd34c3f,0xe1b74c,0x62ad80][i]));
        light.position.set(0,2.71-i*.22,-.11);group.add(light);
        box(.21,.025,.13,0,2.80-i*.22,-.13,metal);
      }
      break;
    case 'cafe_table': {
      const timber=view.material(0xb99a6c,'wood');
      cylinder(.23,.055,0,.69,0,timber);cylinder(.035,.66,0,.34,0,metal);
      cylinder(.13,.035,0,.03,0,metal);
      for(const side of [-1,1]){
        box(.21,.045,.20,side*.35,.38,0,timber);
        box(.035,.25,.22,side*.44,.51,0,timber);
        for(const dz of [-.07,.07])box(.025,.36,.025,side*.35,.18,dz,metal);
      }
      cylinder(.025,.055,.06,.745,.03,0xe5dec7);
      break;
    }
    case 'ticket_counter': {
      box(1.8,.95,.75,0,.475,0,0x657b78);box(1.95,.08,.85,0,.99,0,view.material(0xc6ad85,'wood'));
      box(.4,.32,.08,.5,1.18,0,glass);box(.12,.15,.12,.5,1.03,0,metal);
      const sign=view.label('TICKETS','#f1e6cb',1.5);sign.position.set(0,1.55,0);group.add(sign);break;
    }
    case 'trash':
      cylinder(.25,.58,0,.29,0,view.material((p.variant||0)%2?0x4e615e:0x59605c,'metal'));{const lid=new G.Mesh(new G.CylinderGeometry(.27,.27,.045,12),metal);lid.position.y=.60;group.add(lid);}break;
  }
  if(view.renderer==='webgpu'&&!enhancedProp)propFittings(view,p,group);
  const base={cow:[1,2],sheep:[1,1],pig:[1,1],car:[1,2],truck:[1,2],ambulance:[1,2],bus:[3,7],tractor:[1,1],aircraft:[3,4],train:[2,5],container:[1,3],tank:[1,1],silo:[1,1],pipes:[1,2],bench:[1,1],hay:[1,1],flowerbed:[2,1],ticket_counter:[2,1]}[p.kind]||[1,1];
  if(!enhancedProp)group.scale.set(localProp.width/base[0],p.kind==='car'?1.3:p.kind==='aircraft'?2:p.kind==='train'?1.5:1,localProp.depth/base[1]);
  if(p.growth)group.scale.set(group.scale.x*1.25,group.scale.y*p.growth,group.scale.z*1.25);
  group.traverse(o=>{if(o.isMesh){o.userData.structure=p.id;view.pickables.push(o);}});
  const labelY={aircraft:3,train:4,tree:3,tree_oak:3.2,tree_pine:3.7,tree_birch:3.1,bush:1.2,flowerbed:.9,sign:2,lamp:3,traffic_light:3.1,cafe_table:1.1,trash:1.1}[p.kind]||2.6;
  const health=view.healthLabel(p.kind.replaceAll('_',' '),p.hp,p.max_hp,'#d8c99c',Math.min(3,p.width+1));health.position.set(x,group.userData.transportHeight?group.userData.transportHeight+.45:labelY*(p.growth||1),z);health.userData.structure=p.id;parent.add(health);view.pickables.push(health);
  return group;
}

/** Add one building, its floors, portals, and details to the battlefield. */
export function addBuilding(view,b,state){
  const parent=view.terrain,start=parent.children.length;
  if(b.destroyed){view.box(parent,b.width,.14,b.depth,b.x+(b.width-1)/2,.07,b.y+(b.depth-1)/2,0x66625b);return;}
  if(b.station){const hall=view.label('WAITING HALL','#e7dfc7',Math.min(4,b.width-1));hall.position.set(b.x+(b.width-1)/2,.10,b.y+2);hall.rotation.x=-Math.PI/2;parent.add(hall);}
  const timber=b.facade==='timber'||(!b.facade&&['woods','farm'].includes(state.theme));
  const finish=timber?'wood':b.facade==='metal'?'metal':b.facade==='brick'?'brick':b.facade==='concrete'?'concrete':'paint';
  const wallMaterial=view.material(b.color||state.scenery.wall,view.renderer==='webgpu'?(finish==='paint'?profileFor(state.theme).finish:finish==='metal'?'cladding':finish):finish),trim=b.accent|| (state.theme==='airport'?0x708f9a:state.theme==='factory'?0x69817e:0xbab6a1);
  const limit=view.buildingLevel(b),cx=b.x+(b.width-1)/2,cy=b.y+(b.depth-1)/2;
  for(let level=0;level<=Math.min(limit,b.level);level++){
    view.box(parent,b.width,.10,b.depth,cx,level*3-.055,cy,level===b.level?view.concreteMat:view.material(level?0x888474:0x958c78,view.renderer==='webgpu'?(['woods','farm','urban','streets'].includes(state.theme)?'wood':'concrete'):'paint'));
    if(level<b.level){
      if(view.renderer==='webgpu'){
        furnish(view,b,level,state.theme,parent);
        const timber=view.material(0xb5a18b,'wood'),metal=view.material(0x4b5859,'metal'),x=b.x+.15,z=b.y+.9;
        view.box(parent,.38,.06,.40,x,level*3+.45,z,timber);
        view.box(parent,.38,.36,.055,x,level*3+.66,z+.18,timber);
        for(const dx of [-.14,.14])for(const dz of [-.14,.14])view.box(parent,.025,.40,.025,x+dx,level*3+.22,z+dz,metal);
        for(let k=0;k<3;k++){view.box(parent,.32,.045,.75,b.x+b.width-.67,level*3+.25+k*.43,b.y+.4,timber);for(let j=0;j<4;j++)view.box(parent,.22,.22,.10,b.x+b.width-.67,level*3+.38+k*.43,b.y+.1+j*.17,view.material(j%2?0x667c72:0xb1a288));}
      }
      // Furniture is kept on the edge of floor tiles, leaving traversable centers.
      view.box(parent,.65,.7,.32,b.x+.03,level*3+.35,b.y+.03,0x7c6b51);
      view.box(parent,.68,.05,.36,b.x+.03,level*3+.72,b.y+.03,0xb1a389);
      if(state.theme==='factory')view.box(parent,.45,1.3,.35,b.x+.03,level*3+.65,b.y+b.depth-1.25,0x667c7c);
    }
  }
  // Keep the discovered facade intact even before individual portals are seen.
  // Unobserved openings are closed, opaque and have no portal interaction IDs.
  const walls=state.walls.filter(w=>w.building===b.id),edge=(a,b)=>[a.join(','),b.join(',')].sort().join('|'),known=new Set(walls.map(w=>edge(w.a,w.b)));
  for(const opening of b.exterior_openings||[]){
    const key=edge(opening.a,opening.b);if(known.has(key))continue;
    walls.push({...opening,building:b.id,open:false,facadeOnly:true});known.add(key);
  }
  for(let level=0;level<b.level;level++){
    const pairs=[];for(let x=b.x;x<b.x+b.width;x++)pairs.push([[x,b.y,level],[x,b.y-1,level]],[[x,b.y+b.depth-1,level],[x,b.y+b.depth,level]]);
    for(let y=b.y;y<b.y+b.depth;y++)pairs.push([[b.x,y,level],[b.x-1,y,level]],[[b.x+b.width-1,y,level],[b.x+b.width,y,level]]);
    for(const [a,other] of pairs)if(!known.has(edge(a,other)))walls.push({a,b:other,kind:'wall',open:false,building:b.id});
  }
  for(const wall of walls){
    const [ax,ay,az]=wall.a,[bx,by]=wall.b;
    if(az>limit)continue;
    const cut=limit<b.level&&az===limit;
    const x=(ax+bx)/2,z=(ay+by)/2,vertical=ax!==bx;
    const seg=(length,height,base,offset=0,mat=wallMaterial)=>view.box(parent,vertical?.09:length,height,vertical?length:.09,x+(vertical?0:offset),az*3+base+height/2,z+(vertical?offset:0),mat);
    if(wall.kind==='wall'){seg(1,cut?.38:3,0);if(timber&&!cut)for(let h=.20;h<3;h+=.30)seg(.99,.025,h,0,view.material(0x5d4d3b));
      if(state.theme==='factory'&&!cut)for(let o=-.35;o<.5;o+=.23)seg(.025,3,0,o,view.material(trim));}
    else{
      const double=!!(wall.door_group||wall.double_door),flip=wall.door_leaf===1?-1:1;
      if(!double||flip===1)seg(double?.075:.15,cut?.38:3,0,double?-.4625:-.425);
      if(!double||flip===-1)seg(double?.075:.15,cut?.38:3,0,double?.4625:.425);
      if(!cut)seg(double?1:.7,double?.25:wall.kind==='door'?.5:.6,double?2.75:wall.kind==='door'?2.5:2.4);
      if(wall.kind==='window')seg(.7,cut?.38:.85,0);
      if((view.renderer==='webgpu'||state.theme==='train_station')&&!cut&&!double){
        const frame=view.material(trim,'metal'),sill=view.material(0xbdb8a5,'concrete');
        seg(.82,.075,wall.kind==='window'?.84:2.5,0,sill);
        for(const offset of [-.36,.36])seg(.045,wall.kind==='window'?1.55:2.5,wall.kind==='window'?.87:0,offset,frame);
        if(wall.kind==='window'){seg(.76,.045,2.42,0,frame);seg(.035,1.5,.89,0,frame);}
      }
      const span=double?.925:.7,offset=double?-.425*flip:-.35;
      const hinge=new G.Group();hinge.position.set(x+(vertical?0:offset),az*3,z+(vertical?offset:0));hinge.userData.swingSign=double?flip:1;
      const height=double?2.72:wall.kind==='door'?2.45:1.4,base=wall.kind==='door'?0:.9;
      const leaf=view.box(hinge,vertical?.065:span,height,vertical?span:.065,vertical?0:span/2*flip,base+height/2,vertical?span/2*flip:0,wall.kind==='door'?double?0x8badae:0x6d7c74:0x5b8793);
      if(wall.kind==='window'){leaf.material=new G.MeshStandardMaterial({color:0x5b8793,roughness:.18,metalness:.1});leaf.material.transparent=true;leaf.material.opacity=wall.facadeOnly?1:wall.open?.30:.65;}
      leaf.native.name=double?'station-double-door':wall.kind==='door'?'building-door':'building-window';
      leaf.userData.facadeOnly=!!wall.facadeOnly;
      if(wall.id)leaf.userData.portal=wall.id;
      if(wall.kind==='door'){
        view.box(hinge,.045,double?.4:.035,.11,vertical?.08:(span-.1)*flip,1.15,vertical?(span-.1)*flip:.08,0xd4bd82);
        if(double){for(const h of [.12,.85,2.62])view.box(hinge,vertical?.085:span,.08,vertical?span:.085,vertical?0:span/2*flip,h,vertical?span/2*flip:0,0xd0c8ae);}
      }
      hinge.rotation.y=wall.open?Math.PI*.48*hinge.userData.swingSign:0;parent.add(hinge);
      if(!wall.id)continue;
      view.portalModels.set(wall.id,hinge);view.pickables.push(leaf);
      hinge.traverse(o=>{if(o.isMesh)o.userData.portal=wall.id;});
      const icon=view.hoverLabel(`${wall.open?'OPEN':'CLOSED'} ${wall.kind.toUpperCase()}`,`portal:${wall.id}`,wall.open?'#a4eacb':'#eed29b',1.0);icon.position.set(x,az*3+(wall.kind==='door'?2.65:2.5),z);parent.add(icon);
    }
  }
  if(limit>=b.level){
    const roofY=b.level*3;
    for(const offset of [-1,1])view.box(parent,b.width+.12,.13,.10,cx,roofY+.04,cy+offset*b.depth/2,trim);
    if(['urban','train_station'].includes(state.theme)){
      view.box(parent,1.6,.08,.60,b.x+1,2.58,b.y+b.depth-.26,state.theme==='train_station'?0x6e8a82:0x9b6652);
    }
    if(b.station){
      const edge=b.x+b.width-.5;
      view.box(parent,2.7,.16,b.depth,edge+1.3,3.25,cy,0x667f7b);
      const sign=view.label('CENTRAL STATION','#eee5cb',Math.min(6,b.width));sign.position.set(cx,3.65,cy);parent.add(sign);
    }
    if(state.theme==='airport'&&b.id==='b2'){
      // Glazed upper control-room facade; real operable window stays in its wall slot.
      for(const side of [-1,1])view.box(parent,b.width-.12,.52,.015,cx,roofY-.8,cy+side*b.depth/2,0x4c7687);
    }
    const roofMat=view.material(b.accent||0x696d67,b.roof==='sawtooth'?'metal':'paint');
    if(b.roof==='gable'){
      for(const side of [-1,1]){const slope=view.box(parent,b.width+.25,.10,b.depth*.57,cx,roofY+.43,cy+side*b.depth*.26,roofMat);slope.rotation.x=side*.34;}
    }else if(b.roof==='sawtooth'){
      for(let x=b.x+.55;x<b.x+b.width;x+=1.25){const slope=view.box(parent,1.2,.08,b.depth-.2,x,roofY+.28,cy,roofMat);slope.rotation.z=.30;}
    }else if(b.roof==='dome'){
      const dome=new G.Mesh(new G.SphereGeometry(Math.min(b.width,b.depth)*.28,14,10),roofMat);dome.scale.y=.48;dome.position.set(cx,roofY+.22,cy);parent.add(dome);
    }else if(b.roof==='terrace'){
      for(const side of [-1,1]){view.box(parent,.12,.48,b.depth+.1,b.x+(side>0?b.width-.5:-.5),roofY+.24,cy,roofMat);view.box(parent,b.width+.1,.48,.12,cx,roofY+.24,b.y+(side>0?b.depth-.5:-.5),roofMat);}
    }else if(b.roof==='vented'){
      for(let i=0;i<Math.max(1,Math.floor(b.width/3));i++){view.box(parent,.65,.42,.55,b.x+.8+i*2,roofY+.21,cy,view.material(0x65716f,'metal'));const vent=new G.Mesh(new G.CylinderGeometry(.11,.13,.75,10),view.material(0x596361,'metal'));vent.position.set(b.x+1.35+i*2,roofY+.37,cy);parent.add(vent);}
    }
  }
  const front=b.front||'south',horizontal=front==='north'||front==='south',direction=front==='north'?-1:front==='south'?1:front==='west'?-1:1;
  if(b.archetype==='commercial'){
    const awning=view.box(parent,horizontal?Math.min(3,b.width-.3):.72,.16,horizontal?.72:Math.min(3,b.depth-.3),horizontal?cx:b.x+(direction>0?b.width-.15:-.15),2.48,horizontal?b.y+(direction>0?b.depth-.15:-.15):cy,view.material(trim,'paint'));
    if(horizontal)awning.rotation.x=direction*.12;else awning.rotation.z=-direction*.12;
    if(state.theme==='urban'){
      const sx=horizontal?cx:b.x+(direction>0?b.width-.45:-.55),sz=horizontal?b.y+(direction>0?b.depth-.45:-.55):cy;
      const fascia=view.box(parent,horizontal?b.width-.3:.08,.38,horizontal?.08:b.depth-.3,sx,2.85,sz,view.material(b.name==='CAFE'?0x34685f:0x885743));
      fascia.native.name=b.name==='CAFE'?'urban-cafe-front':'urban-shop-front';
      const lettering=view.label(b.name==="CAFE"?'CAFÉ · COFFEE':b.name,'#fff1cd',Math.min(2.1,horizontal?b.width-1:b.depth-1));
      lettering.position.set(sx+(horizontal?0:direction*.13),2.86,sz+(horizontal?direction*.13:0));parent.add(lettering);
    }
  }else if(b.archetype==='residential'&&b.level>1&&state.theme!=='streets'){
    for(let level=1;level<b.level&&level<=limit;level++){const balcony=view.box(parent,horizontal?Math.min(2.3,b.width-.4):.55,.10,horizontal?.55:Math.min(2.3,b.depth-.4),horizontal?cx:b.x+(direction>0?b.width-.22:-.22),level*3+.18,horizontal?b.y+(direction>0?b.depth-.22:-.22):cy,view.material(trim,'metal'));for(const side of [-1,1])view.box(parent,.04,.72,.04,balcony.position.x+(horizontal?side*.8:0),level*3+.52,balcony.position.z+(horizontal?0:side*.8),view.material(trim,'metal'));}
  }else if(b.archetype==='civic'){
    for(const side of [-1,1])view.box(parent,.16,2.55,.16,horizontal?cx+side*.72:b.x+(direction>0?b.width-.18:-.18),1.27,horizontal?b.y+(direction>0?b.depth-.18:-.18):cy+side*.72,view.material(trim,'concrete'));
  }
  if(state.theme==='streets'){
    const px=horizontal?cx:b.x+(direction>0?b.width-.25:-.75),pz=horizontal?b.y+(direction>0?b.depth-.25:-.75):cy;
    const canopy=view.box(parent,horizontal?Math.min(1.8,b.width-.4):.75,.10,horizontal?.75:Math.min(1.8,b.depth-.4),px,2.48,pz,view.material(trim,'wood'));canopy.native.name='suburban-porch';
    if(limit>=b.level){const chimney=view.box(parent,.38,.85,.38,b.x+.5,b.level*3+.7,b.y+.5,view.material(0x946e58,'brick'));chimney.native.name='suburban-chimney';}
  }
  if(view.renderer==='webgpu'){
    for(let level=0;level<Math.min(b.level,limit+1);level++)for(const x of [b.x-.48,b.x+b.width-.52]){
      view.box(parent,.065,level===limit&&limit<b.level?.32:2.9,.065,x,level*3+(level===limit&&limit<b.level?.16:1.45),b.y-.57,view.material(0x596660,'metal'));
      for(let i=0;i<(level===limit&&limit<b.level?1:7);i++)view.box(parent,.24,.16,.16,x,level*3+.16+i*.42,b.y-.48,trim);
    }
    if(limit>=b.level&&['flat','terrace','vented'].includes(b.roof)){
      view.box(parent,.95,.45,.65,cx,b.level*3+.25,cy,view.material(0x79827c,'metal'));
      for(let i=0;i<8;i++)view.box(parent,.78,.022,.02,cx,b.level*3+.08+i*.045,cy+.335,0x333e3c);
    }
  }
  for(const child of parent.children.slice(start))child.traverse(o=>{if(o.isMesh){o.userData.structure=b.id;view.pickables.push(o);}});
  const sign=view.healthLabel(b.name,b.hp,b.max_hp,'#eee4c6',2.5);sign.userData.structure=b.id;view.pickables.push(sign);sign.position.set(cx,Math.min(b.level,limit)*3+.35,b.y-.6);parent.add(sign);
  for(const [a,d] of state.stairs.filter(([a])=>a[0]>=b.x&&a[0]<b.x+b.width&&a[1]>=b.y&&a[1]<b.y+b.depth)){
    if(a[2]>limit)continue;
    const id=`stairs:${a.join(',')}:${d.join(',')}`,link={transition:id,ends:[a,d],x:a[0],y:a[1],z:a[2]};
    const sign=view.hoverLabel('STAIRS ↕',id,'#f6d495',.9);sign.position.set(a[0],a[2]*3+.7,a[1]);parent.add(sign);
    // Keep an exposed flight in a cutaway instead of only a floating text marker.
    for(let i=0;i<9;i++){const step=view.box(parent,.72,(i+1)/3,.095,a[0],a[2]*3+(i+1)/6,a[1]-.4+i*.095,0xb1afa0);step.userData={...link};view.pickables.push(step);}
  }
}
