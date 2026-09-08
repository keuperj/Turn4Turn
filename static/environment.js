import * as THREE from 'three';

// Theme props share the footprints used by Python collision/pathfinding.
export function addProp(view, p, parent=view.terrain) {
  if(p.destroyed){view.box(parent,p.width*.8,.12,p.depth*.8,p.x+(p.width-1)/2,.06,p.y+(p.depth-1)/2,0x45443e);return;}
  const group=new THREE.Group();parent.add(group);
  const x=p.x+(p.width-1)/2,z=p.y+(p.depth-1)/2;
  group.position.set(x,0,z);
  const box=(w,h,d,x,y,z,c)=>view.box(group,w,h,d,x,y,z,c);
  const color=p.color||'#91a5a1',metal=0x424c4e,glass=0x344e5b;
  const cylinder=(r,h,x,y,z,c)=>{const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,14),view.material(c));m.position.set(x,y,z);m.castShadow=m.receiveShadow=true;group.add(m);return m;};
  const wheel=(x,z,r=.19)=>{const w=cylinder(r,.13,x,r,z,0x242927);w.rotation.z=Math.PI/2;};
  switch(p.kind){
    case 'car': case 'truck': case 'tractor': {
      const truck=p.kind==='truck',tractor=p.kind==='tractor';
      box(.82,.33,tractor?.85:1.8,0,.43,0,color);
      box(.70,.46,truck?.60:.85,0,.80,truck?-.48:0,color);
      box(.62,.31,.03,0,.86,truck?-.80:-.44,glass);
      box(.03,.29,.62,-.36,.87,0,glass);box(.03,.29,.62,.36,.87,0,glass);
      if(truck)box(.77,.55,.9,0,.83,.44,0xa6a494);
      for(const side of [-1,1])for(const end of [-1,1])wheel(side*.43,end*(tractor?.33:.56),tractor?.25:.19);
      for(const s of [-1,1]){box(.15,.08,.04,s*.26,.48,-.92,0xf4e0b3);box(.13,.07,.04,s*.26,.47,.91,0xb15442);}
      break;
    }
    case 'train': {
      box(1.65,.36,4.7,0,.45,0,metal);box(1.65,1.7,4.55,0,1.35,0,color);
      box(1.58,.18,4.6,0,2.24,0,0xc5c9bd);
      for(let i=-1.5;i<=1.5;i+=.75)for(const s of [-1,1])box(.025,.55,.48,s*.84,1.62,i,glass);
      box(1.3,.6,.025,0,1.65,-2.29,glass);
      for(const s of [-1,1])for(const z of [-1.65,1.65])wheel(s*.74,z,.30);
      for(const z of [-2.4,2.4])box(.35,.2,.25,0,.5,z,metal);
      break;
    }
    case 'aircraft': {
      const fuselage=new THREE.Mesh(new THREE.CapsuleGeometry(.34,2.7,6,12),view.material(0xcbd1c9));fuselage.rotation.x=Math.PI/2;fuselage.position.y=.72;fuselage.castShadow=true;group.add(fuselage);
      box(2.85,.10,.70,0,.7,.25,0xbcc7c5);box(1.35,.07,.45,0,.85,1.5,0xbcc7c5);
      box(.08,.8,.6,0,1.1,1.4,0x667e83);box(.36,.18,.60,0,.96,-.9,glass);
      for(const s of [-1,1]){const engine=cylinder(.15,.6,s*.8,.5,.15,metal);engine.rotation.x=Math.PI/2;wheel(s*.7,.5,.14);}wheel(0,-1.05,.13);
      break;
    }
    case 'container':
      box(.94,1.7,2.9,0,.85,0,color);
      for(let z=-1.35;z<1.5;z+=.25)for(const s of [-1,1])box(.025,1.6,.045,s*.48,.85,z,0x687d79);
      break;
    case 'tank': case 'silo':
      cylinder(.45,p.kind==='silo'?3.4:1.5,0,p.kind==='silo'?1.7:.75,0,0xa4aba4);
      {const cap=new THREE.Mesh(new THREE.ConeGeometry(.48,.4,16),view.material(0x89978e));cap.position.y=p.kind==='silo'?3.6:1.7;group.add(cap);}break;
    case 'pipes':
      for(let i=0;i<3;i++){const c=cylinder(.13,1.8,-.26+i*.26,.22,0,metal);c.rotation.x=Math.PI/2;}break;
    case 'hay':
      {const hay=cylinder(.40,.8,0,.42,0,0xc3a658);hay.rotation.z=Math.PI/2;}break;
    case 'bench':
      box(.84,.12,.38,0,.45,0,0x93734f);box(.84,.35,.08,0,.68,.19,0x93734f);
      for(const s of [-1,1])box(.065,.40,.34,s*.32,.20,0,metal);break;
    case 'tree':
      cylinder(.09,1.8,0,.9,0,0x67513a);
      for(let j=0;j<5;j++){const m=new THREE.Mesh(new THREE.IcosahedronGeometry(.48+(j%2)*.1,1),view.material([0x485a38,0x5c7043,0x748357][j%3]));m.position.set(Math.sin(j*2.4)*.24,1.6+j*.15,Math.cos(j*2.4)*.24);m.castShadow=true;group.add(m);}break;
  }
  const base={car:[1,2],truck:[1,2],tractor:[1,1],aircraft:[3,4],train:[2,5],container:[1,3],tank:[1,1],silo:[1,1],pipes:[1,2],bench:[1,1],hay:[1,1],tree:[1,1]}[p.kind]||[1,1];
  group.scale.set(p.width/base[0],p.kind==='car'?1.3:p.kind==='aircraft'?2:p.kind==='train'?1.5:1,p.depth/base[1]);
  group.traverse(o=>{if(o.isMesh){o.userData.structure=p.id;view.pickables.push(o);}});
  const health=view.healthLabel(p.kind,p.hp,p.max_hp,'#d8c99c',Math.min(3,p.width+1));health.position.set(x,p.kind==='aircraft'?3:p.kind==='train'?4:2.6,z);health.userData.structure=p.id;parent.add(health);view.pickables.push(health);
  return group;
}

export function addBuilding(view,b,state){
  const parent=view.terrain,start=parent.children.length;
  if(b.destroyed){view.box(parent,b.width,.14,b.depth,b.x+(b.width-1)/2,.07,b.y+(b.depth-1)/2,0x66625b);return;}
  const timber=['woods','farm'].includes(state.theme);
  const wallMaterial=timber?view.material(state.theme==='farm'&&b.id==='b1'?0x905342:0x897053,'wood'):['urban','streets','train_station'].includes(state.theme)?view.material(state.scenery.wall,'brick'):view.concreteMat;
  const trim=state.theme==='airport'?0x708f9a:state.theme==='factory'?0x69817e:0xbab6a1;
  const limit=view.buildingLevel(b),cx=b.x+(b.width-1)/2,cy=b.y+(b.depth-1)/2;
  for(let level=0;level<=Math.min(limit,b.level);level++){
    view.box(parent,b.width,.10,b.depth,cx,level*3-.055,cy,level===b.level?view.concreteMat:view.material(level?0x888474:0x958c78));
    if(level<b.level){
      // Furniture is kept on the edge of floor tiles, leaving traversable centers.
      view.box(parent,.65,.7,.32,b.x+.03,level*3+.35,b.y+.03,0x7c6b51);
      view.box(parent,.68,.05,.36,b.x+.03,level*3+.72,b.y+.03,0xb1a389);
      if(state.theme==='factory')view.box(parent,.45,1.3,.35,b.x+.03,level*3+.65,b.y+b.depth-1.25,0x667c7c);
    }
  }
  // A known building retains a solid exterior even before every wall/portal is observed.
  // Unknown openings remain opaque; their actual state comes only from the server.
  const walls=state.walls.filter(w=>w.building===b.id),edge=(a,b)=>[a.join(','),b.join(',')].sort().join('|'),known=new Set(walls.map(w=>edge(w.a,w.b)));
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
      seg(.15,cut?.38:3,0,-.425);seg(.15,cut?.38:3,0,.425);
      if(!cut)seg(.7,wall.kind==='door'?.5:.6,wall.kind==='door'?2.5:2.4);
      if(wall.kind==='window')seg(.7,cut?.38:.85,0);
      const hinge=new THREE.Group();hinge.position.set(x+(vertical?0:-.35),az*3,z+(vertical?-.35:0));
      const height=wall.kind==='door'?2.45:1.4,base=wall.kind==='door'?0:.9;
      const leaf=view.box(hinge,vertical?.065:.7,height,vertical?.7:.065,vertical?0:.35,base+height/2,vertical?.35:0,wall.kind==='door'?0x6d7c74:0x5b8793);
      if(wall.kind==='window'){leaf.material.transparent=true;leaf.material.opacity=wall.open?.30:.65;}
      leaf.userData.portal=wall.id;
      if(wall.kind==='door')view.box(hinge,.035,.035,.11,vertical?.08:.6,1.15,vertical?.6:.08,0xd4bd82);
      hinge.rotation.y=wall.open?Math.PI*.48:0;parent.add(hinge);view.portalModels.set(wall.id,hinge);view.pickables.push(leaf);
      if(cut||wall.kind==='door'){const icon=view.label(`${wall.open?'OPEN':'CLOSED'} ${wall.kind==='door'?'DOOR':'WINDOW'}`,wall.open?'#a4eacb':'#eed29b',1.0);icon.position.set(x,az*3+(wall.kind==='door'?2.65:2.5),z);parent.add(icon);}
    }
  }
  if(limit>=b.level){
    const roofY=b.level*3;
    for(const offset of [-1,1])view.box(parent,b.width+.12,.13,.10,cx,roofY+.04,cy+offset*b.depth/2,trim);
    if(['urban','streets','train_station'].includes(state.theme)){
      view.box(parent,1.6,.08,.60,b.x+1,2.58,b.y+b.depth-.26,state.theme==='train_station'?0x6e8a82:0x9b6652);
    }
    if(state.theme==='airport'&&b.id==='b2'){
      // Glazed upper control-room facade; real operable window stays in its wall slot.
      for(const side of [-1,1])view.box(parent,b.width-.12,.52,.015,cx,roofY-.8,cy+side*b.depth/2,0x4c7687);
    }
  }
  for(const child of parent.children.slice(start))child.traverse(o=>{if(o.isMesh){o.userData.structure=b.id;view.pickables.push(o);}});
  const sign=view.healthLabel(b.name,b.hp,b.max_hp,'#eee4c6',2.5);sign.userData.structure=b.id;view.pickables.push(sign);sign.position.set(cx,Math.min(b.level,limit)*3+.35,b.y-.6);parent.add(sign);
  for(const [a,d] of state.stairs.filter(([a])=>a[0]===b.x+b.width-1&&a[1]===b.y)){
    if(a[2]>limit)continue;
    if(a[2]===limit){const sign=view.label('STAIRS ↑','#f6d495',.9);sign.position.set(a[0],a[2]*3+.2,a[1]);parent.add(sign);}
    else for(let i=0;i<9;i++)view.box(parent,.72,(i+1)/3,.095,a[0],a[2]*3+(i+1)/6,a[1]-.4+i*.095,0xb1afa0);
  }
}
