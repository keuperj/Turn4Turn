import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {addProp,addBuilding} from './environment.js';
import {actionAudio} from './audio.js';

// Geometry is genuinely three-dimensional; Python supplies all walkable surfaces.
export class Battlefield {
  constructor(canvas, onPick, onHover) {
    this.canvas=canvas;this.onPick=onPick;this.onHover=onHover;
    this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#202c30');
    this.scene.fog=new THREE.Fog('#202c30',100,350);
    this.renderer=new THREE.WebGLRenderer({canvas,antialias:true});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));
    this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.08;
    this.camera=new THREE.PerspectiveCamera(42,1,.1,500);
    this.camera.position.set(26,27,32);
    this.controls=new OrbitControls(this.camera,canvas);this.controls.target.set(8.5,0,8.5);
    this.controls.enableDamping=true;this.controls.minDistance=2;this.controls.maxDistance=220;
    this.controls.maxPolarAngle=Math.PI*.46;
    this.controls.mouseButtons={LEFT:THREE.MOUSE.PAN,MIDDLE:THREE.MOUSE.DOLLY,RIGHT:THREE.MOUSE.ROTATE};
    this.scene.add(new THREE.HemisphereLight('#dbeaf0','#53635d',1.8));
    const sun=new THREE.DirectionalLight('#fff1db',2.6);sun.position.set(-12,28,12);sun.castShadow=true;
    sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-40,right:40,top:40,bottom:-40,far:80});sun.shadow.bias=-.0003;sun.shadow.normalBias=.025;this.scene.add(sun);
    this.terrain=new THREE.Group();this.actors=new THREE.Group();this.overlay=new THREE.Group();this.fx=new THREE.Group();
    this.scene.add(this.terrain,this.actors,this.overlay,this.fx);this.models=new Map();this.pickables=[];this.portalModels=new Map();this.viewMode='auto';
    this.loader=new THREE.TextureLoader();
    this.ground=this.texture('/assets/ground.png',4);this.camo=this.texture('/assets/camouflage.png',1);
    this.concrete=this.texture('/assets/concrete.png',1);
    this.surfaceMaps={paint:this.surfaceTexture('paint'),wood:this.surfaceTexture('wood'),brick:this.surfaceTexture('brick')};
    this.concreteMat=new THREE.MeshStandardMaterial({map:this.concrete,bumpMap:this.concrete,bumpScale:.07,roughness:.97});
    this.groundMat=new THREE.MeshStandardMaterial({map:this.ground,bumpMap:this.ground,bumpScale:.12,roughness:1});
    this.uniform=new THREE.MeshStandardMaterial({map:this.camo,bumpMap:this.camo,bumpScale:.025,color:0xc8c8b7,roughness:1});
    this.ray=new THREE.Raycaster();this.pointer=new THREE.Vector2();
    canvas.addEventListener('contextmenu',e=>e.preventDefault());
    canvas.addEventListener('pointerdown',e=>{this.down={x:e.clientX,y:e.clientY,button:e.button};});
    canvas.addEventListener('pointerup',e=>{if(this.down?.button===0&&Math.hypot(e.clientX-this.down.x,e.clientY-this.down.y)<5){const hit=this.pick(e);if(hit)this.onPick(hit,false);}this.down=null;});
    canvas.addEventListener('dblclick',e=>{e.preventDefault();const hit=this.pick(e);if(hit)this.onPick(hit,true);});
    canvas.addEventListener('pointermove',e=>{this.hoverPointer={clientX:e.clientX,clientY:e.clientY};this.updateHover();});
    canvas.addEventListener('pointerleave',()=>{this.hoverPointer=null;this.updateHover();});
    this.controls.addEventListener('change',()=>this.updateHover());
    new ResizeObserver(()=>this.resize()).observe(canvas.parentElement);this.resize();
    this.renderer.setAnimationLoop(time=>{if(time-(this.lastFrame||0)<16)return;this.lastFrame=time;this.controls.update();for(const m of this.models.values()){if(m.userData.rig&&!m.userData.walking){const r=m.userData.rig;r.body.position.y=r.baseY+Math.sin(performance.now()*.002+m.position.x)*.012;}}this.renderer.render(this.scene,this.camera);});
  }
  texture(url,repeat){const t=this.loader.load(url);t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(repeat,repeat);t.anisotropy=this.renderer.capabilities.getMaxAnisotropy();return t;}
  surfaceTexture(kind){const c=document.createElement('canvas');c.width=c.height=256;const ctx=c.getContext('2d');ctx.fillStyle='#d1d0ca';ctx.fillRect(0,0,256,256);let seed=17;const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};for(let i=0;i<4500;i++){const v=Math.floor(125+random()*95);ctx.fillStyle=`rgba(${v},${v},${v},.2)`;ctx.fillRect(random()*256,random()*256,kind==='wood'?25:2,1);}ctx.strokeStyle='#777c7855';ctx.lineWidth=2;if(kind==='wood'){for(let x=0;x<256;x+=32){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,256);ctx.stroke();}}else if(kind==='brick'){for(let y=0;y<256;y+=24){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(256,y);ctx.stroke();for(let x=(y/24%2)*32;x<256;x+=64){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x,y+24);ctx.stroke();}}}else{for(let i=0;i<20;i++){ctx.fillStyle='#727e7840';ctx.fillRect(random()*256,random()*256,5+random()*16,1);}}const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;}
  resize(){const w=this.canvas.parentElement.clientWidth,h=this.canvas.parentElement.clientHeight;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
  material(color,finish='paint'){const map=finish==='skin'?null:this.surfaceMaps?.[finish]||this.concrete;return new THREE.MeshStandardMaterial({color,map,bumpMap:map,bumpScale:finish==='wood'?.025:.008,roughness:finish==='skin'?.82:finish==='paint'?.48:.9,metalness:finish==='paint'?.18:0});}
  box(parent,w,h,d,x,y,z,mat){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),typeof mat==='object'?mat:this.material(mat));m.position.set(x,y,z);m.castShadow=m.receiveShadow=true;parent.add(m);return m;}
  clear(group){for(const child of [...group.children]){child.traverse(o=>{o.geometry?.dispose();if(o.material&&!Object.values(this).includes(o.material)){const ms=Array.isArray(o.material)?o.material:[o.material];ms.forEach(m=>{if(m.userData.label)m.map?.dispose();m.dispose();});}});group.remove(child);}}
  buildingLevel(b){
    if(this.viewMode==='exterior')return b.level;
    if(this.viewMode!=='auto')return Math.min(Number(this.viewMode),b.level);
    const u=this.state?.units.find(u=>u.id===this.selected);
    if(u&&u.x>=b.x&&u.x<b.x+b.width&&u.y>=b.y&&u.y<b.y+b.depth)return u.z;
    const contact=this.state?.units.find(v=>v.team!=='soldier'&&v.hp>0&&v.x>=b.x&&v.x<b.x+b.width&&v.y>=b.y&&v.y<b.y+b.depth&&v.z<b.level);if(contact)return contact.z;
    if(this.state?.portals.some(p=>p.building===b.id&&p.kind==='door'&&p.open))return 0;
    return b.level;
  }
  surfaceVisible(x,y,z){
    const b=this.state.buildings.find(b=>x>=b.x&&x<b.x+b.width&&y>=b.y&&y<b.y+b.depth);
    return b ? z===this.buildingLevel(b) : z===0;
  }
  actorVisible(u){
    if(!this.surfaceVisible(u.x,u.y,u.z))return false;
    return !u.evacuated;
  }
  setView(mode){this.viewMode=mode;this.signature=null;}
  build(state){
    this.clear(this.terrain);this.pickables=[];this.portalModels.clear();
    const theme=state.scenery;
    this.groundMat.color.set(theme.ground);
    const n=state.size,c=(n-1)/2;
    this.box(this.terrain,n+2,.4,n+2,c,-.4,c,0x18282b);
    const ground=new THREE.Mesh(new THREE.PlaneGeometry(state.size,state.size),this.groundMat);ground.rotation.x=-Math.PI/2;ground.position.set(c,-.01,c);ground.receiveShadow=true;this.terrain.add(ground);
    for(const [x,y,z] of state.surfaces){
      if(!this.surfaceVisible(x,y,z))continue;
      const surface=new THREE.Mesh(new THREE.PlaneGeometry(.98,.98),new THREE.MeshBasicMaterial({visible:false}));surface.rotation.x=-Math.PI/2;surface.position.set(x,z*3+.04,y);surface.userData={x,y,z};this.terrain.add(surface);this.pickables.push(surface);
    }
    for(let y=0;y<n;y++)for(let x=0;x<n;x++){
      const t=state.tiles[y][x];
      if(t==='road')this.box(this.terrain,1,.025,1,x,0,y,theme.road);
      if(t==='road'&&x===theme.road_x&&y%2===0&&state.theme!=='train_station')this.box(this.terrain,.05,.03,.55,x,.025,y,0xc8bd86);
      if(t==='crops')for(let k=0;k<3;k++)this.box(this.terrain,.055,.3,.85,x-.3+k*.3,.15,y,0x849052);
      if(t==='low'){this.box(this.terrain,.88,.55,.7,x,.275,y,0x817c61);for(let k=0;k<3;k++)this.box(this.terrain,.26,.2,.76,x-.29+k*.29,.65,y,0xa69d7b);}
      if(t==='high'){this.box(this.terrain,.84,2.2,.72,x,1.1,y,this.concreteMat);for(let k=0;k<4;k++)this.box(this.terrain,.88,.035,.76,x,.3+k*.5,y,0x93968a);}
      if(t==='rubble')for(let i=0;i<4;i++){const m=this.box(this.terrain,.2,.15,.3,x+(i%2-.5)*.45,.075,y+(Math.floor(i/2)-.5)*.4,0x6e6a5a);m.rotation.y=i;}
    }
    for(const b of state.buildings)addBuilding(this,b,state);
    for(const [a,b] of state.ladders){const h=b[2]*3,x=(a[0]+b[0])/2,z=(a[1]+b[1])/2;
      for(const offset of [-.23,.23])this.box(this.terrain,.055,h+.4,.055,x,h/2+.15,z+offset,0xc3ac64);
      for(let r=.2;r<h+.4;r+=.3)this.box(this.terrain,.06,.04,.5,x,r,z,0xc3ac64);
      const icon=this.label('LADDER ↑','#f9d58a',1);icon.position.set(a[0],.25,a[1]);this.terrain.add(icon);
    }
    for(const prop of state.props)addProp(this,prop);
    if(state.theme==='train_station'){
      for(const x of [theme.road_x-.8,theme.road_x+.8]){this.box(this.terrain,.055,.065,n,x,.05,c,0x99a3a0);}
      for(let y=0;y<n;y+=.5)this.box(this.terrain,2.2,.04,.12,theme.road_x,.025,y,0x5e5445);

    }
    if(state.theme==='airport'){
      for(let i=0;i<8;i++)this.box(this.terrain,.14,.04,1.6,theme.road_x-2+i*.6,.05,n-6,0xeee9d5);
    }

    const evac=this.label('CIVILIAN EVACUATION →','#ace9c0',4);evac.position.set(c,.12,n-.3);this.terrain.add(evac);
    const grid=new THREE.GridHelper(n,n,0x9aaca3,0x6e8074);grid.position.set(c,.035,c);grid.material.transparent=true;grid.material.opacity=.16;this.terrain.add(grid);
    const explored=new Set(state.fog.explored.map(p=>p.join(','))),visible=new Set(state.fog.visible.map(p=>p.join(',')));
    for(let y=0;y<n;y++)for(let x=0;x<n;x++){const b=state.buildings.find(b=>x>=b.x&&x<b.x+b.width&&y>=b.y&&y<b.y+b.depth);const z=b?this.buildingLevel(b):0,key=`${x},${y},${z}`;if(visible.has(key))continue;const fog=new THREE.Mesh(new THREE.PlaneGeometry(1.015,1.015),new THREE.MeshBasicMaterial({color:0x0c1a23,transparent:explored.has(key),opacity:explored.has(key)?.62:1,depthWrite:!explored.has(key)}));fog.rotation.x=-Math.PI/2;fog.position.set(x,z*3+.17,y);this.terrain.add(fog);}
  }
  label(text,color='#ffffff',width=1.3){const c=document.createElement('canvas');c.width=256;c.height=64;const ctx=c.getContext('2d');ctx.fillStyle='rgba(12,22,25,.8)';ctx.fillRect(0,0,256,64);ctx.fillStyle=color;ctx.font='bold 27px monospace';ctx.textAlign='center';ctx.fillText(text,128,43,244);const map=new THREE.CanvasTexture(c),mat=new THREE.SpriteMaterial({map,depthTest:false});mat.userData.label=true;const s=new THREE.Sprite(mat);s.scale.set(width,width/4,1);return s;}
  limb(parent,a,b,r,mat){const m=new THREE.Mesh(new THREE.CylinderGeometry(r*.85,r,1,8),mat);m.castShadow=true;parent.add(m);this.placeLimb(m,a,b);return m;}
  placeLimb(m,a,b){const av=new THREE.Vector3(...a),bv=new THREE.Vector3(...b),delta=bv.clone().sub(av);m.position.copy(av.add(bv).multiplyScalar(.5));m.scale.y=delta.length();m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());}
  figure(u){const root=new THREE.Group(),body=new THREE.Group();root.add(body);const friendly=u.team==='soldier',civilian=u.team==='civilian',cloth=friendly?this.uniform:this.material(civilian?0xa99b7b:0x67766b),vest=this.material(friendly?0x53533c:0x3e494e),skin=this.material(friendly?(u.id==='s1'?0x694735:0xb89a7e):0x98aaa0,'skin'),black=this.material(0x252c2a);
    const knee=u.stance==='kneeling',prone=u.stance==='prone',hip=knee?.52:.85,shoulder=hip+.43;
    this.box(body,.38,.47,.24,0,hip+.23,0,cloth);this.box(body,.4,.35,.1,0,hip+.24,-.14,vest);this.box(body,.29,.35,.16,0,hip+.25,.2,vest);
    for(let i=0;i<3;i++)this.box(body,.09,.13,.08,-.12+i*.12,hip+.16,-.22,vest);
    const head=new THREE.Mesh(new THREE.SphereGeometry(.14,12,10),skin);head.position.set(0,shoulder+.23,0);head.castShadow=true;body.add(head);
    const helmet=new THREE.Mesh(new THREE.SphereGeometry(.16,12,8,0,Math.PI*2,0,Math.PI*.6),cloth);helmet.position.set(0,shoulder+.27,0);helmet.castShadow=true;body.add(helmet);
    this.box(body,.23,.055,.08,0,shoulder+.25,-.13,black);
    // Face, comms, straps and protection remain inexpensive low-poly geometry.
    this.box(body,.05,.07,.05,0,shoulder+.20,-.145,skin);
    for(const side of [-1,1]){this.box(body,.04,.085,.035,side*.14,shoulder+.20,0,skin);this.box(body,.045,.045,.035,side*.065,shoulder+.25,-.178,0x8aa6aa);this.box(body,.035,.36,.025,side*.145,hip+.27,-.20,black);this.box(body,.09,.12,.12,side*.13,knee?.19:.43,knee?.25:-.045,vest);this.box(body,.095,.08,.09,side*.1,shoulder-.15,-.4,skin);}
    this.box(body,.075,.11,.06,-.17,shoulder+.23,.02,black);
    if(u.weapon==='M24 sniper'||u.weapon==='M110')this.box(body,.075,.07,.26,.10,shoulder-.055,-.46,black);
    const legs=[],arms=[];
    for(const side of [-1,1]){const hx=side*.13,ky=knee?.16:.43,kz=knee?(side===1?-.3:.3):.025;
      const upper=this.limb(body,[hx,hip,0],[hx,ky,kz],.10,cloth),lower=this.limb(body,[hx,ky,kz],[hx,.11,knee?.25:.04],.085,cloth),foot=this.box(body,.17,.14,.29,hx,.08,knee?.17:-.04,black);legs.push({side,upper,lower,foot});
      const upperArm=this.limb(body,[side*.23,shoulder,0],[side*.29,shoulder-.21,-.17],.075,cloth),lowerArm=this.limb(body,[side*.29,shoulder-.21,-.17],[side*.1,shoulder-.15,-.4],.065,cloth);arms.push({side,upper:upperArm,lower:lowerArm});
    }
    const gun=new THREE.Group();gun.position.set(.10,shoulder-.15,-.36);body.add(gun);
    if(u.weapon==='RPG-7'){
      const tube=new THREE.Mesh(new THREE.CylinderGeometry(.065,.065,.85,10),vest);tube.rotation.x=Math.PI/2;gun.add(tube);const tip=new THREE.Mesh(new THREE.ConeGeometry(.1,.25,10),vest);tip.rotation.x=-Math.PI/2;tip.position.z=-.53;gun.add(tip);
    }else if(['Frag grenade','Smoke grenade','Demolition charge','Medikit'].includes(u.weapon)){
      if(u.weapon==='Demolition charge'||u.weapon==='Medikit'){this.box(gun,.22,.14,.18,0,0,0,vest);this.box(gun,.09,.025,.07,0,.08,0,black);}else{const frag=new THREE.Mesh(u.weapon==='Smoke grenade'?new THREE.CylinderGeometry(.06,.06,.17,12):new THREE.SphereGeometry(.075,12,10),vest);gun.add(frag);}
    }else{const pistol=u.weapon==='M9';this.box(gun,.065,.10,pistol?.2:.48,0,0,-.1,black);this.box(gun,.035,.035,pistol?.13:.35,0,.02,pistol?-.2:-.48,black);this.box(gun,.055,.16,.08,0,-.1,0,black);if(!pistol)this.box(gun,.08,.11,.19,0,0,.2,vest);}
    if(u.weapon==='Shotgun'){this.box(gun,.09,.09,.24,0,-.015,-.36,vest);this.box(gun,.045,.04,.38,0,-.045,-.4,black);}
    if(u.weapon==='Medikit'){this.box(gun,.10,.025,.03,0,.097,0,0xe8f0de);this.box(gun,.03,.025,.10,0,.098,0,0xe8f0de);}
    if(prone){body.rotation.x=-Math.PI/2;body.position.set(0,.28,.6);}
    if(civilian){gun.visible=false;helmet.visible=false;}
    root.position.set(u.x,u.z*3,u.y);root.rotation.y=u.facing??(friendly?0:Math.PI);
    root.userData.rig={body,legs,arms,hip,shoulder,stance:u.stance,civilian,baseY:body.position.y,baseZ:body.position.z};
    root.userData.unit=u.id;root.traverse(o=>o.userData.unit=u.id);
    const ring=new THREE.Mesh(new THREE.RingGeometry(.34,.40,32),new THREE.MeshBasicMaterial({color:civilian?0x8fe5ad:friendly?0x69cddd:0xec8567,side:THREE.DoubleSide,transparent:true,opacity:.85}));ring.rotation.x=-Math.PI/2;ring.position.y=.04;root.add(ring);
    const direction=new THREE.Mesh(new THREE.ConeGeometry(.10,.22,3),new THREE.MeshBasicMaterial({color:friendly?0x92e5ed:0xe9ac91}));direction.rotation.x=-Math.PI/2;direction.position.set(0,.06,-.58);direction.userData.unit=u.id;root.add(direction);
    const tag=this.healthLabel(u.name,u.hp,u.max_hp,civilian?'#bcebc6':friendly?'#b8edf2':'#ffc0a6',1.35);tag.userData.unit=u.id;tag.position.y=prone?.8:knee?1.5:1.95;root.add(tag);
    return root;
  }
  sync(state,selected,target,mode,aim){
    this.mode=mode;
    const first=!this.state||this.state.seed!==state.seed;this.state=state;this.selected=selected;
    if(first){this.home();const u=state.units.find(u=>u.id===selected);if(u){this.focus(u);this.camera.position.copy(this.controls.target).add(new THREE.Vector3(17,23,22));}}
    const signature=JSON.stringify([state.seed,state.theme,state.tiles,state.portals.map(p=>p.open),this.viewMode,state.fog.visible,state.fog.explored,state.buildings.map(b=>[this.buildingLevel(b),b.hp]),state.props.map(p=>[p.id,p.hp])]);if(this.signature!==signature){this.build(state);this.signature=signature;}
    this.clear(this.actors);this.models.clear();
    for(const u of state.units){if(!this.actorVisible(u))continue;if(u.hp<=0){this.corpse(u);continue;}const model=this.figure(u);this.actors.add(model);this.models.set(u.id,model);}
    for(const m of state.last_seen||[]){if(!this.surfaceVisible(m.x,m.y,m.z))continue;const ghost=new THREE.Group(),mat=new THREE.MeshBasicMaterial({color:0x9ba3a8,transparent:true,opacity:.42,depthWrite:false});const body=new THREE.Mesh(new THREE.CapsuleGeometry(.19,.65,4,8),mat);body.position.y=.7;ghost.add(body);const head=new THREE.Mesh(new THREE.SphereGeometry(.14,8,6),mat);head.position.y=1.3;ghost.add(head);const tag=this.label(`LAST SEEN · R${m.round}`,'#adb5ba',1.65);tag.position.y=1.65;ghost.add(tag);ghost.position.set(m.x,m.z*3,m.y);ghost.traverse(o=>o.userData.memory=m.id);this.actors.add(ghost);}
    this.updateHover(true);
    this.lastSeed=state.seed;
    this.clear(this.overlay);
    const points=mode==='attack'?[]:state.movement[selected]||[];
    if(state.status==='active')for(const p of points){if(!this.surfaceVisible(p.x,p.y,p.z))continue;const mat=new THREE.MeshBasicMaterial({color:mode==='attack'?0xed9862:p.cost===1?0x68d1e5:0xe9c677,transparent:true,opacity:.23,side:THREE.DoubleSide,depthWrite:false});const m=new THREE.Mesh(new THREE.PlaneGeometry(.91,.91),mat);m.rotation.x=-Math.PI/2;m.position.set(p.x,p.z*3+.05,p.y);this.overlay.add(m);}
    for(const smoke of state.smoke||[]){for(let i=0;i<9;i++){const m=new THREE.Mesh(new THREE.IcosahedronGeometry(smoke.radius*.53,1),new THREE.MeshBasicMaterial({color:0xaab0ad,transparent:true,opacity:.35,depthWrite:false}));m.position.set(smoke.x+Math.sin(i*2.4)*smoke.radius*.6,smoke.z*3+.6+(i%3)*.4,smoke.y+Math.cos(i*2.4)*smoke.radius*.6);this.overlay.add(m);}const label=this.label(`SMOKE ${smoke.turns}`,'#e2e5e2',1.5);label.position.set(smoke.x,smoke.z*3+2.3,smoke.y);this.overlay.add(label);}
    for(const charge of state.charges||[]){this.box(this.overlay,.35,.18,.28,charge.x,charge.z*3+.1,charge.y,0x605746);const label=this.label(`CHARGE · ${charge.turns} PHASES`,'#ffb27d',1.7);label.position.set(charge.x,charge.z*3+.6,charge.y);this.overlay.add(label);}
    const u=state.units.find(u=>u.id===selected&&u.hp>0);
    if(u&&this.actorVisible(u)){const m=new THREE.Mesh(new THREE.RingGeometry(.45,.49,40),new THREE.MeshBasicMaterial({color:0xd6fdff,side:THREE.DoubleSide}));m.rotation.x=-Math.PI/2;m.position.set(u.x,u.z*3+.065,u.y);this.overlay.add(m);}
    if(aim&&u&&mode==='attack'&&state.weapons[u.weapon].radius){const radius=state.weapons[u.weapon].radius;const m=new THREE.Mesh(new THREE.RingGeometry(radius-.04,radius+.04,64),new THREE.MeshBasicMaterial({color:0xffad68,side:THREE.DoubleSide,depthTest:false}));m.rotation.x=-Math.PI/2;m.position.set(aim.x,aim.z*3+.08,aim.y);this.overlay.add(m);}
    const t=state.units.find(u=>u.id===target&&u.hp>0);if(u&&t&&this.actorVisible(u)&&this.actorVisible(t)&&mode!=='attack'){const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(u.x,u.z*3+1,u.y),new THREE.Vector3(t.x,t.z*3+1,t.y)]),new THREE.LineDashedMaterial({color:0xf3bc87,dashSize:.15,gapSize:.12}));line.computeLineDistances();this.overlay.add(line);}
  }
  pick(e){this.scene.updateMatrixWorld(true);this.camera.updateMatrixWorld();const r=this.canvas.getBoundingClientRect();this.pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.ray.setFromCamera(this.pointer,this.camera);const hits=this.ray.intersectObjects([...this.actors.children,...this.pickables],true);const hit=hits.find(h=>!h.object.userData.health&&h.object.visible&&h.object.parent?.visible&&(h.object.userData.memory||h.object.userData.portal||h.object.userData.unit||h.object.userData.structure||h.object.userData.x!==undefined));if(!hit)return null;const data={...hit.object.userData};if(data.unit||data.memory)return data;let structure=this.state.buildings.concat(this.state.props).find(p=>p.id===data.structure);if(structure){data.x=Math.max(structure.x,Math.min(structure.x+structure.width-1,Math.round(hit.point.x)));data.y=Math.max(structure.y,Math.min(structure.y+structure.depth-1,Math.round(hit.point.z)));data.z=Math.max(0,Math.min(structure.level||0,Math.floor((hit.point.y+.05)/3)));}else if(this.mode==='attack'&&data.x!==undefined){structure=this.state.buildings.find(b=>!b.destroyed&&data.z===b.level&&data.x>=b.x&&data.x<b.x+b.width&&data.y>=b.y&&data.y<b.y+b.depth);if(structure)data.structure=structure.id;}return data;}
  updateHover(force=false){
    if(!this.state||!this.ray)return;
    const hit=this.hoverPointer?this.pick(this.hoverPointer):null;
    const key=hit?.unit?`unit:${hit.unit}`:hit?.structure?`structure:${hit.structure}`:null;
    if(force||key!==this.hoverKey){this.hoverKey=key;for(const group of [this.terrain,this.actors])group.traverse(o=>{if(o.userData.health)o.visible=!!key&&key===(o.userData.unit?`unit:${o.userData.unit}`:`structure:${o.userData.structure}`);});}
    this.onHover?.(hit);
  }
  healthLabel(name,hp,max,color='#d9cfac',width=2.3){const c=document.createElement('canvas');c.width=384;c.height=96;const ctx=c.getContext('2d');ctx.fillStyle='#0b1b25de';ctx.fillRect(0,0,384,96);ctx.fillStyle=color;ctx.font='bold 23px system-ui';ctx.textAlign='center';ctx.fillText(name.toUpperCase(),192,29,370);ctx.font='19px monospace';ctx.fillText(`${hp} / ${max} HP`,192,55);ctx.fillStyle='#3b484b';ctx.fillRect(14,68,356,10);ctx.fillStyle=color;ctx.fillRect(14,68,356*Math.max(0,hp/max),10);const map=new THREE.CanvasTexture(c),mat=new THREE.SpriteMaterial({map,depthTest:false});mat.userData.label=true;const sprite=new THREE.Sprite(mat);sprite.scale.set(width,width/4,1);sprite.userData.health=true;sprite.visible=false;return sprite;}
  showPreview(preview){if(!preview)return;const u=this.state.units.find(u=>u.id===this.selected);if(!u)return;const points=preview.via?[[u.x,u.y,u.z],[preview.via.x,preview.via.y,preview.via.z],[preview.x,preview.y,preview.z]]:preview.path?[[u.x,u.y,u.z],...preview.path]:preview.x!==undefined?[[u.x,u.y,u.z],[preview.x,preview.y,preview.z]]:[];if(!points.length)return;const color=preview.action==='move'?0x8fe9ee:0xffc28b;const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(p[0],p[2]*3+.2,p[1]))),new THREE.LineDashedMaterial({color,dashSize:.2,gapSize:.12,depthTest:false}));line.computeLineDistances();this.overlay.add(line);const p=points.at(-1);const marker=new THREE.Mesh(new THREE.RingGeometry(.32,.40,40),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide,depthTest:false}));marker.rotation.x=-Math.PI/2;marker.position.set(p[0],p[2]*3+.1,p[1]);this.overlay.add(marker);}
  focus(u){if(!u)return;const delta=new THREE.Vector3(u.x,u.z*3,u.y).sub(this.controls.target);this.controls.target.add(delta);this.camera.position.add(delta);this.controls.update();this.camera.updateMatrixWorld();this.updateHover();}
  home(){const c=((this.state?.size||30)-1)/2;this.camera.position.set(c+this.state.size*.85,this.state.size*1.1,c+this.state.size);this.controls.target.set(c,0,c);}
  corpse(u){
    const model=this.figure({...u,stance:'standing'}),body=model.children[0];
    model.traverse(o=>{delete o.userData.unit;Object.assign(o.userData,{x:u.x,y:u.y,z:u.z});});
    for(const child of [...model.children].slice(1)){child.geometry?.dispose();child.material?.map?.dispose();child.material?.dispose();model.remove(child);}
    body.rotation.set(-Math.PI/2,0,.2);body.position.set(0,.18,.60);model.rotation.y=(u.x+u.y)*.7;this.actors.add(model);
    for(let i=0;i<5;i++){const blood=new THREE.Mesh(new THREE.CircleGeometry(i? .12:.5,12),new THREE.MeshBasicMaterial({color:i?0x8d2526:0x591419,transparent:true,opacity:.85,depthWrite:false}));blood.rotation.x=-Math.PI/2;blood.scale.y=.7;blood.position.set(u.x+Math.sin(i*2.4)*.48,u.z*3+.055,u.y+Math.cos(i*2.4)*.48);this.actors.add(blood);}
  }
  async burst(point,color,radius,duration){const particles=[];for(let i=0;i<12;i++){const m=new THREE.Mesh(new THREE.IcosahedronGeometry(color===0x73766d?.22:.04,0),new THREE.MeshBasicMaterial({color,transparent:true}));m.position.copy(point);this.fx.add(m);particles.push({m,v:new THREE.Vector3(Math.sin(i*2.4)*radius,.25+(i%4)*.2,Math.cos(i*2.4)*radius)});}await this.tween(duration,t=>{for(const {m,v} of particles){m.position.copy(point).addScaledVector(v,t);m.position.y-=t*t*.3;m.material.opacity=1-t;if(color===0x73766d)m.scale.setScalar(1+t*4);}});}
  gait(model,phase,climbing=false){
    const r=model.userData.rig;if(!r)return;
    const prone=r.stance==='prone',crouch=r.stance==='kneeling';
    const amplitude=prone?.13:crouch?.19:.30;
    r.body.position.y=r.baseY+(prone?0:Math.abs(Math.sin(phase))*.035);
    for(const leg of r.legs){
      const wave=Math.sin(phase+(leg.side>0?0:Math.PI)),lift=Math.max(0,Math.cos(phase+(leg.side>0?0:Math.PI)));
      const hx=leg.side*.13,knee=[hx,climbing?.55:r.hip*.52,-wave*amplitude*.6];
      const ankle=[hx,.11+lift*(climbing?.25:.12),wave*amplitude];
      this.placeLimb(leg.upper,[hx,r.hip,0],knee);this.placeLimb(leg.lower,knee,ankle);
      leg.foot.position.set(hx,ankle[1]-.03,ankle[2]-.05);leg.foot.rotation.x=wave*.15;
    }
    if(r.civilian){for(const arm of r.arms){const wave=Math.sin(phase+(arm.side>0?0:Math.PI));const elbow=[arm.side*.25,r.shoulder-.25,wave*.10],hand=[arm.side*.26,r.shoulder-.50,wave*.23];this.placeLimb(arm.upper,[arm.side*.23,r.shoulder,0],elbow);this.placeLimb(arm.lower,elbow,hand);}}
    if(prone||climbing)for(const arm of r.arms){const wave=Math.sin(phase+arm.side*Math.PI/2);const elbow=[arm.side*.28,r.shoulder-.1+wave*.12,-.22],hand=[arm.side*.18,r.shoulder+(climbing?.2:-.12),-.35+wave*.12];this.placeLimb(arm.upper,[arm.side*.23,r.shoulder,0],elbow);this.placeLimb(arm.lower,elbow,hand);}
  }
  async animate(events,followEnemies=false){
    for(const e of events||[]){
      const actor=e.actor||this.state.units.find(u=>u.id===e.unit);
      const follow=followEnemies&&actor?.team==='alien'&&e.type!=='hide';
      if(follow){
        const p=e.origin||(e.x!==undefined?[e.x,e.y,e.z]:null)||[actor.x,actor.y,actor.z];
        const from=this.controls.target.clone(),to=new THREE.Vector3(p[0],p[2]*3,p[1]);
        if(from.distanceTo(to)>.1)await this.tween(220,t=>{const v=from.clone().lerp(to,t);this.focus({x:v.x,y:v.z,z:v.y/3});});
      }
      if(e.type!=='impact')actionAudio.play(e);
      if(e.type==='hide'){const m=this.models.get(e.unit);if(m)m.visible=false;continue;}
      if(e.type==='move'){
        let model=this.models.get(e.unit);
        if(!model){const u=e.actor||this.state.units.find(u=>u.id===e.unit);if(!u)continue;model=this.figure(u);this.actors.add(model);this.models.set(e.unit,model);}
        model.visible=true;
        if(e.origin)model.position.set(e.origin[0],e.origin[2]*3,e.origin[1]);
        const start=model.position.clone(),end=new THREE.Vector3(e.x,e.z*3,e.y),climbing=Math.abs(start.y-end.y)>.1;
        const fromYaw=model.rotation.y,toYaw=(start.x!==end.x||start.z!==end.z)?Math.atan2(start.x-end.x,start.z-end.z):fromYaw;const yawDelta=Math.atan2(Math.sin(toYaw-fromYaw),Math.cos(toYaw-fromYaw));
        model.userData.walking=true;
        const duration=climbing?650:model.userData.rig.stance==='prone'?340:220;
        await this.tween(duration,t=>{model.position.lerpVectors(start,end,t);if(follow)this.focus({x:model.position.x,y:model.position.z,z:model.position.y/3});model.rotation.y=fromYaw+yawDelta*Math.min(1,t*4);this.gait(model,t*Math.PI*2,climbing);});
        model.userData.walking=false;
      }
      if(e.type==='face'){const model=this.models.get(e.unit);if(model){const from=model.rotation.y,delta=Math.atan2(Math.sin(e.facing-from),Math.cos(e.facing-from));await this.tween(150,t=>model.rotation.y=from+delta*t);}}
      if(e.type==='peek_out'||e.type==='peek_return'){const model=this.models.get(e.unit);if(model){const from=model.position.clone(),to=new THREE.Vector3(e.point[0],e.point[2]*3,e.point[1]);await this.tween(220,t=>model.position.lerpVectors(from,to,t));}if(e.contacts){for(const u of e.contacts){if(!this.models.has(u.id)){const m=this.figure(u);this.actors.add(m);this.models.set(u.id,m);}}await this.tween(280,()=>{});}}
      if(e.type==='heal'){const p=new THREE.Vector3(e.point[0],e.point[2]*3+1,e.point[1]);await this.burst(p,0x80f3b4,.5,400);this.clear(this.fx);}
      if(e.type==='rocket_launch'&&e.target){const from=new THREE.Vector3(e.point[0],e.point[2]*3+1,e.point[1]),to=new THREE.Vector3(e.target[0],e.target[2]*3+.4,e.target[1]),rocket=new THREE.Mesh(new THREE.SphereGeometry(.1,8,6),new THREE.MeshBasicMaterial({color:0xffdb9a}));this.fx.add(rocket);await this.tween(250,t=>rocket.position.lerpVectors(from,to,t));this.clear(this.fx);}
      if(e.type==='throw'){const points=[e.origin,...(e.via?[e.via]:[]),e.point].map(p=>new THREE.Vector3(p[0],p[2]*3+1,p[1])),ball=new THREE.Mesh(new THREE.SphereGeometry(.09,8,6),this.material(0x718268));this.fx.add(ball);for(let i=1;i<points.length;i++)await this.tween(i===1&&e.via?130:350,t=>{ball.position.lerpVectors(points[i-1],points[i],t);ball.position.y+=Math.sin(t*Math.PI)*(i===1&&e.via?.15:1);});this.clear(this.fx);}
      if(e.type==='portal'){const model=this.portalModels.get(e.id);if(model){const from=model.rotation.y,to=e.open?Math.PI*.48:0;await this.tween(240,t=>model.rotation.y=from+(to-from)*t);}}
      if(e.type==='shot'||e.type==='impact'){
        const point=new THREE.Vector3(e.point[0]+(e.hit||e.structure?0:.45),e.point[2]*3+(e.structure?1:e.hit?.8:.12),e.point[1]+(e.hit||e.structure?0:.3));
        if(e.origin){const origin=new THREE.Vector3(e.origin[0],e.origin[2]*3+1.1,e.origin[1]);const bullet=new THREE.Mesh(new THREE.SphereGeometry(.07,6,4),new THREE.MeshBasicMaterial({color:0xffe8b2}));this.fx.add(bullet);await this.tween(e.burst?35:100,t=>bullet.position.lerpVectors(origin,point,t));this.clear(this.fx);}
        actionAudio.play({type:'impact',point:e.point});await this.burst(point,e.hit&&!e.structure?0xb52a2c:0xffd18a,.7,e.burst?65:240);this.clear(this.fx);
      }
      if(e.type==='blast'){
        const point=new THREE.Vector3(e.x,e.z*3+.35,e.y);
        const fire=new THREE.Mesh(new THREE.SphereGeometry(.7,12,8),new THREE.MeshBasicMaterial({color:0xffa044,transparent:true,opacity:.95}));fire.position.copy(point);this.fx.add(fire);
        const ring=new THREE.Mesh(new THREE.RingGeometry(.8,1,32),new THREE.MeshBasicMaterial({color:0xfac881,transparent:true,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.copy(point);ring.position.y=e.z*3+.20;this.fx.add(ring);
        await this.tween(350,t=>{fire.scale.setScalar(.3+t*e.radius*1.5);fire.material.opacity=1-t;ring.scale.setScalar(.2+t*e.radius*1.8);ring.material.opacity=1-t;});this.clear(this.fx);
        await this.burst(point,0x73766d,e.radius*1.5,450);this.clear(this.fx);
      }
      if(e.type==='evacuate'){const m=this.models.get(e.unit);if(m)m.visible=false;}
    }
  }
  tween(ms,fn){return new Promise(resolve=>{const start=performance.now();const tick=now=>{const t=Math.max(0,Math.min(1,(now-start)/ms));fn(t);if(t<1)requestAnimationFrame(tick);else resolve();};requestAnimationFrame(tick);});}
}
