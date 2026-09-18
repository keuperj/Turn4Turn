/** @fileoverview Build, synchronize, interact with, and animate the tactical battlefield. */
import * as G from './rendering.js';
import {B,OrbitControls} from './rendering.js';
import {CharacterAssets} from './characters.js';
import {TransportAssets} from './transport.js';
import {addProp,addBuilding} from './environment.js';
import {actionAudio} from './audio.js';
import {qualityLighting,qualityMaterials} from './webgpu-quality.js';
import {smokeCanvas,detailedEffects} from './webgpu-nature.js';

import {urbanStreets} from './urban.js';
import {streetCrossing} from './street-crossing.js';
import {BackgroundAssets} from './background.js';
import {woodlandGround} from './woodland.js';

// Geometry is genuinely three-dimensional; Python supplies all walkable surfaces.
/** Manage the Babylon battlefield and its WebGPU or WebGL engine. */
export class Battlefield {
  /**
   * Create the best renderer authorized by the completed capability test.
   *
   * WebGL is the default. WebGPU is attempted only after the shared diagnostic
   * has passed, and any Babylon initialization error returns to WebGL.
   *
   * @param {HTMLCanvasElement} canvas Battlefield output canvas.
   * @param {Function} onPick Pointer selection callback.
   * @param {Function} onHover Pointer hover callback.
   * @param {Object} gpuTest Result returned by testWebGPU.
   * @returns {Promise<Battlefield>} Initialized renderer facade.
   */
  static async create(canvas,onPick,onHover,gpuTest={ok:false,reason:'WebGPU test was not run.'}){
    const forcedWebGL=new URLSearchParams(location.search).get('renderer')==='webgl';
    let fallbackReason=forcedWebGL?'WebGL was explicitly selected.':'';
    if(!forcedWebGL&&gpuTest.ok&&navigator.gpu&&B.WebGPUEngine){
      for(let attempt=1;attempt<=3;attempt++){
        let engine;
        try{
          engine=new B.WebGPUEngine(canvas,{antialiasing:true,adaptToDeviceRatio:false});
          await engine.initAsync();
          const field=new Battlefield(canvas,onPick,onHover,engine,'webgpu');
          const info=engine._adapterInfo||engine._adapter?.info||{};
          field.gpuInfo={vendor:info.vendor||'',architecture:info.architecture||'',device:info.device||'',description:info.description||'',fallback:Boolean(info.isFallbackAdapter??engine._adapter?.isFallbackAdapter)};
          return field;
        }catch(error){
          engine?.dispose();fallbackReason=error?.message||(error?String(error):'WebGPU initialization failed.');
          if(attempt<3)await new Promise(resolve=>setTimeout(resolve,500));
        }
      }
    }else if(!forcedWebGL){
      fallbackReason=gpuTest.ok?'Babylon WebGPU is unavailable.':gpuTest.reason||'WebGPU capability test did not pass.';
    }
    console.info(`Using WebGL fallback: ${fallbackReason}`);
    return new Battlefield(canvas,onPick,onHover,new B.Engine(canvas,true,{preserveDrawingBuffer:true,stencil:true}),'webgl',fallbackReason);
  }
  /** Initialize this instance. */
  constructor(canvas,onPick,onHover,engine=null,renderer='webgl',fallbackReason='') {
    this.canvas=canvas;this.onPick=onPick;this.onHover=onHover;
    this.engine=engine||new B.Engine(canvas,true,{preserveDrawingBuffer:true,stencil:true});
    this.renderer=renderer;this.fallbackReason=fallbackReason;
    // A tactical camera does not benefit much from supersampling every foliage
    // edge. Cap pixel density and leave headroom for input and animation work.
    this.engine.setHardwareScalingLevel(1/Math.min(devicePixelRatio,1.25));
    this.nativeScene=new B.Scene(this.engine);this.nativeScene.useRightHandedSystem=true;
    this.nativeScene.clearColor=B.Color4.FromHexString('#26383fff');
    this.nativeScene.fogMode=B.Scene.FOGMODE_LINEAR;this.nativeScene.fogColor=B.Color3.FromHexString('#26383f');this.nativeScene.fogStart=100;this.nativeScene.fogEnd=350;
    const image=this.nativeScene.imageProcessingConfiguration;image.toneMappingEnabled=true;image.toneMappingType=B.ImageProcessingConfiguration.TONEMAPPING_ACES;image.exposure=1.08;
    const sky=new B.HemisphericLight('sky',new B.Vector3(0,1,0),this.nativeScene);this.sky=sky;sky.intensity=.85;sky.diffuse=B.Color3.FromHexString('#dbeaf0');sky.groundColor=B.Color3.FromHexString('#53635d');
    this.sun=new B.DirectionalLight('sun',new B.Vector3(.4,-1,-.4),this.nativeScene);this.sun.position.set(-12,28,12);this.sun.intensity=2.6;this.sun.diffuse=B.Color3.FromHexString('#fff1db');this.sun.shadowMinZ=1;this.sun.shadowMaxZ=120;
    this.shadows=new B.ShadowGenerator(1024,this.sun);this.shadows.usePercentageCloserFiltering=true;this.shadows.filteringQuality=B.ShadowGenerator.QUALITY_LOW;this.shadows.normalBias=.025;
    G.configure(this.nativeScene,this.shadows);this.scene=new G.Scene(this.nativeScene);
    this.camera=new G.PerspectiveCamera(42,1,.1,500);this.camera.position.set(26,27,32);
    this.controls=new OrbitControls(this.camera,canvas);this.controls.target.set(8.5,0,8.5);
    this.characters=new CharacterAssets(this);this.transport=new TransportAssets(this);this.background=new BackgroundAssets(this);this.ready=Promise.all([this.characters.load(),this.transport.load(),this.background.load()]);this.nativeScene.onAfterAnimationsObservable.add(()=>this.characters.afterAnimations());
    this.terrain=new G.Group();this.actors=new G.Group();this.overlay=new G.Group();this.fx=new G.Group();this.flames=[];this.elapsed=0;
    this.scene.add(this.terrain,this.actors,this.overlay,this.fx);this.models=new Map();this.pickables=[];this.portalModels=new Map();this.viewMode='auto';
    this.loader=new G.TextureLoader();
    this.ground=this.texture('/assets/terrain-mixed-v2.webp',6);this.camo=this.texture('/assets/camouflage.png',1);
    this.concrete=this.texture('/assets/concrete-weathered-v2.webp',4);this.paintedMetal=this.texture('/assets/painted-metal-v2.webp',2);this.smokeMap=this.cloudTexture();
    this.materialCache=new Map();this.surfaceMaps={paint:this.paintedMetal,metal:this.paintedMetal,wood:this.surfaceTexture('wood'),brick:this.surfaceTexture('brick')};
    this.concreteMat=new G.MeshStandardMaterial({map:this.concrete,bumpMap:this.concrete,bumpScale:.07,roughness:.97});
    this.groundMat=new G.MeshStandardMaterial({map:this.ground,bumpMap:this.ground,bumpScale:.12,roughness:1});
    this.pavedGroundMat=new G.MeshStandardMaterial({map:this.concrete,roughness:.96});
    this.groundAccentMat=new G.MeshStandardMaterial({map:this.ground,roughness:1});
    this.uniform=new G.MeshStandardMaterial({map:this.camo,bumpMap:this.camo,bumpScale:.025,color:0xc8c8b7,roughness:1});
    this.pickMaterial=new G.MeshBasicMaterial({visible:false});this.fogMaterials={explored:new G.MeshBasicMaterial({color:0x071016,transparent:true,opacity:.72,depthWrite:false}),unseen:new G.MeshBasicMaterial({color:0x000000})};this.moveMaterials=[1,2].map(cost=>new G.MeshBasicMaterial({color:cost===1?0x68d1e5:0xe9c677,transparent:true,opacity:.23,side:G.DoubleSide,depthWrite:false}));for(const m of [...Object.values(this.fogMaterials),...this.moveMaterials])m.userData.shared=true;
    if(this.renderer==='webgpu'){
      this.qualityPipeline=qualityLighting(this.nativeScene,this.camera.native,this.sun,this.shadows);
      this.qualityMaps=qualityMaterials(this.nativeScene);
      this.concreteMat.native.albedoTexture=this.qualityMaps.stone;
      for(const m of [this.concreteMat,this.groundMat,this.pavedGroundMat])m.native.bumpTexture=this.qualityMaps.normal;
    }
    this.ray=new G.Raycaster();this.pointer=new G.Vector2();
    canvas.addEventListener('contextmenu',e=>e.preventDefault());
    canvas.addEventListener('pointerdown',e=>{this.down={x:e.clientX,y:e.clientY,button:e.button};});
    canvas.addEventListener('pointerup',e=>{if(this.down?.button===0&&Math.hypot(e.clientX-this.down.x,e.clientY-this.down.y)<5){const hit=this.pick(e);if(hit)this.onPick(hit,false);}this.down=null;});
    canvas.addEventListener('dblclick',e=>{e.preventDefault();const hit=this.pick(e);if(hit)this.onPick(hit,true);});
    canvas.addEventListener('pointermove',e=>{this.hoverPointer={clientX:e.clientX,clientY:e.clientY};this.queueHover();});
    canvas.addEventListener('pointerleave',()=>{this.hoverPointer=null;this.queueHover();});
    this.controls.addEventListener('change',()=>this.queueHover());
    new ResizeObserver(()=>this.resize()).observe(canvas.parentElement);this.resize();
    this.engine.runRenderLoop(()=>{const dt=Math.min(this.engine.getDeltaTime()/1000,.1);this.elapsed+=dt;this.controls.update();this.background.atmosphere();this.characters.update(dt);for(const e of this.ambientEffects?.values()||[])e.effect.update({kind:e.kind,age:this.elapsed-e.start},e.origin,e.size);for(const f of this.flames){const pulse=.8+Math.sin(this.elapsed*7+f.phase)*.22;f.mesh.scale.set(pulse,pulse*(1.15+Math.sin(this.elapsed*5+f.phase)*.18),pulse);f.mesh.position.y=f.base+Math.sin(this.elapsed*6+f.phase)*.08;}this.nativeScene.render();});

  }
  /** Load and configure a repeating battlefield texture. */
  texture(url,repeat){const t=this.loader.load(url);t.colorSpace=G.SRGBColorSpace;t.wrapS=t.wrapT=G.RepeatWrapping;t.repeat.set(repeat,repeat);t.anisotropy=Math.min(8,this.engine.getCaps().maxAnisotropy);return t;}
  /** Generate a deterministic procedural material texture. */
  surfaceTexture(kind){const c=document.createElement('canvas');c.width=c.height=256;const ctx=c.getContext('2d'),base={wood:'#b7a585',brick:'#b58f7e',metal:'#aab3b1',asphalt:'#777d7d',soil:'#9b865f',paint:'#c5c7c1'}[kind];ctx.fillStyle=base;ctx.fillRect(0,0,256,256);let seed=17+kind.length*997;const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};for(let i=0;i<3200;i++){const v=Math.floor(80+random()*130),alpha=kind==='asphalt'?.16:.10;ctx.fillStyle=`rgba(${v},${v},${v},${alpha})`;const long=kind==='wood'||kind==='metal';ctx.fillRect(random()*256,random()*256,long?18+random()*28:1+random()*3,1+random()*1.5);}ctx.strokeStyle=kind==='metal'?'#e1e7e255':'#5e625b66';ctx.lineWidth=2;if(kind==='wood'){for(let x=0;x<256;x+=32){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,256);ctx.stroke();}}else if(kind==='brick'){for(let y=0;y<256;y+=24){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(256,y);ctx.stroke();for(let x=(y/24%2)*32;x<256;x+=64){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x,y+24);ctx.stroke();}}}else if(kind==='metal'){for(let x=0;x<256;x+=42){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,256);ctx.stroke();}}else if(kind==='asphalt'){for(let i=0;i<90;i++){ctx.fillStyle=i%3?'#d6d4c918':'#252b2c20';ctx.beginPath();ctx.arc(random()*256,random()*256,random()*2.2+.3,0,Math.PI*2);ctx.fill();}}else if(kind==='soil'){ctx.strokeStyle='#5e533638';for(let y=8;y<256;y+=16){ctx.beginPath();ctx.moveTo(0,y);ctx.bezierCurveTo(64,y+5,190,y-4,256,y+2);ctx.stroke();}}else{for(let i=0;i<20;i++){ctx.fillStyle='#727e7840';ctx.fillRect(random()*256,random()*256,5+random()*16,1);}}const t=new G.CanvasTexture(c);t.colorSpace=G.SRGBColorSpace;t.wrapS=t.wrapT=G.RepeatWrapping;t.repeat.set(2,2);return t;}
  /** Reconcile persistent GPU emitters without restarting them on UI selection changes. */
  syncAtmosphere(state){
    this.ambientEffects??=new Map();const live=new Set();
    for(const [kind,items] of [['continuous-smoke',state.smoke||[]],['continuous-fire',state.fires||[]]])for(const p of items){
      const key=[state.seed,kind,p.x,p.y,p.z].join(':');live.add(key);
      let entry=this.ambientEffects.get(key);
      if(!entry){entry={effect:detailedEffects(this.nativeScene,true),kind,start:this.elapsed};this.ambientEffects.set(key,entry);}
      entry.origin=[p.x,p.z*3+.1,p.y];entry.size=kind==='continuous-smoke'?Math.max(.4,p.radius*.7):.65;
      entry.effect.update({kind,age:this.elapsed-entry.start},entry.origin,entry.size);
    }
    for(const [key,entry] of this.ambientEffects)if(!live.has(key)){entry.effect.dispose();this.ambientEffects.delete(key);}
  }
  /** Generate the procedural texture used by smoke effects. */
  cloudTexture(){if(this.renderer==='webgpu')return new G.CanvasTexture(smokeCanvas());const c=document.createElement('canvas');c.width=c.height=128;const ctx=c.getContext('2d');for(let i=0;i<18;i++){const x=64+Math.sin(i*2.4)*27,y=64+Math.cos(i*2.4)*27,r=20+i%4*5,g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,'rgba(220,226,224,.25)');g.addColorStop(.45,'rgba(182,194,191,.14)');g.addColorStop(1,'rgba(170,184,180,0)');ctx.fillStyle=g;ctx.fillRect(0,0,128,128);}return new G.CanvasTexture(c);}
  /** Resize rendering resources to their displayed dimensions. */
  resize(){const w=this.canvas.parentElement.clientWidth,h=this.canvas.parentElement.clientHeight;this.engine.setSize(w,h);this.camera.updateProjectionMatrix();}
  /** Return a cached, finish-aware battlefield material. */
  material(color,finish='paint'){const key=String(color)+':'+finish;if(this.materialCache.has(key))return this.materialCache.get(key);const textured=!['skin','rubber','glass'].includes(finish);if(textured&&!this.surfaceMaps[finish]&&['metal','asphalt','soil'].includes(finish))this.surfaceMaps[finish]=this.surfaceTexture(finish);const map=textured?(this.surfaceMaps[finish]||this.concrete):null;const m=new G.MeshStandardMaterial({color,map,bumpMap:map,bumpScale:finish==='wood'?.025:.008,roughness:finish==='skin'?.82:finish==='glass'?.16:finish==='paint'?.48:finish==='metal'?.36:.9,metalness:finish==='paint'?.18:finish==='metal'?.65:0,transparent:finish==='glass',opacity:finish==='glass'?.68:1});if(this.renderer==='webgpu'&&this.qualityMaps&&textured){m.native.bumpTexture=this.qualityMaps.normal;if(finish==='metal'||finish==='cladding')m.native.albedoTexture=this.qualityMaps.metal;if(finish==='concrete')m.native.albedoTexture=this.qualityMaps.stone;if(finish==='brick')m.native.albedoTexture=this.qualityMaps.brick;if(finish==='wood')m.native.albedoTexture=this.qualityMaps.timber;}m.userData.shared=true;this.materialCache.set(key,m);return m;}

  /** Create and attach a box-shaped scene element. */
  box(parent,w,h,d,x,y,z,mat){const m=new G.Mesh(new G.BoxGeometry(w,h,d),typeof mat==='object'?mat:this.material(mat));m.position.set(x,y,z);m.receiveShadow=true;if(Math.max(w,h,d)>=.48&&w*h*d>.018)m.castShadow=true;parent.add(m);return m;}
  /** Create one batched mesh for a set of tactical tiles. */
  tiles(parent,points,mat,size=1,data=null){if(!points.length)return null;const m=new G.Mesh(new G.TileGeometry(points,size),mat);m.native.isPickable=!!data;if(data)m.userData=data;parent.add(m);return m;}
  /** Queue hover. */
  queueHover(){if(this.hoverFrame)return;this.hoverFrame=requestAnimationFrame(()=>{this.hoverFrame=0;this.updateHover();});}
  /** Dispose and remove every child of a scene group. */
  clear(group){
    for(const child of [...group.children])this.disposeObject(child);
    if(group===this.terrain){this.terrainState=null;this.terrainWorldKey=null;}
    if(group===this.actors)this.actorWorldKey=null;
  }
  /** Release nested character instances as well as geometry and private labels. */
  disposeObject(child){
    child.traverse(o=>this.characters?.release(o));
    const materials=new Set();child.traverse(o=>{if(o.material&&!o.material.userData?.shared&&!Object.values(this).includes(o.material))materials.add(o.material);});
    child.dispose();for(const m of materials){if(m.userData?.label)m.map?.dispose();m.dispose();}
  }

  /** Build ing level. */
  buildingLevel(b){
    if(this.viewMode==='exterior')return b.level;
    if(this.viewMode!=='auto')return Math.min(Number(this.viewMode),b.level);
    const u=this.state?.units.find(u=>u.id===this.selected);
    if(u&&u.x>=b.x&&u.x<b.x+b.width&&u.y>=b.y&&u.y<b.y+b.depth)return u.z;
    const contact=this.state?.units.find(v=>v.team!=='soldier'&&v.hp>0&&v.x>=b.x&&v.x<b.x+b.width&&v.y>=b.y&&v.y<b.y+b.depth&&v.z<b.level);if(contact)return contact.z;
    if(this.state?.portals.some(p=>p.building===b.id&&p.kind==='door'&&p.open))return 0;
    return b.level;
  }
  /** Return whether a floor surface is visible in the cutaway. */
  surfaceVisible(x,y,z){
    const b=this.state.buildings.find(b=>x>=b.x&&x<b.x+b.width&&y>=b.y&&y<b.y+b.depth);
    return b ? z===this.buildingLevel(b) : z===0;
  }
  /** Return whether an actor belongs in the current cutaway view. */
  actorVisible(u){
    if(!this.surfaceVisible(u.x,u.y,u.z))return false;
    return !u.evacuated;
  }
  /** Update view. */
  setView(mode){if(this.viewMode===mode)return;this.viewMode=mode;this.terrainState=null;}
  /** Retain unchanged scene layers; only dispose resources owned by a changed layer. */
  terrainLayer(key,signature,draw){
    this.liveTerrainLayers.add(key);
    const cached=this.terrainLayers.get(key);if(cached?.signature===signature)return cached;
    if(cached){this.clear(cached.group);cached.group.dispose();}
    const root=this.terrain,pickables=this.pickables,portals=this.portalModels;
    const group=new G.Group();group.native.name=key;root.add(group);
    const entry={group,signature,pickables:[],portals:new Map(),hover:[]};
    this.terrain=group;this.pickables=entry.pickables;this.portalModels=entry.portals;
    try{
      draw();group.updateMatrixWorld();
      group.traverse(o=>{
        if(o.isMesh&&!o.userData.portal&&!o.userData.hoverFor&&!o.userData.health)o.native.freezeWorldMatrix();
        if(o.userData.hoverFor||o.userData.health)entry.hover.push(o);
      });
    }finally{this.terrain=root;this.pickables=pickables;this.portalModels=portals;}
    this.terrainLayers.set(key,entry);return entry;
  }
  /** Synchronize scenery independently from visibility and tactical overlays. */
  build(state){
    const worldKey=JSON.stringify([state.seed,state.theme,state.size]);
    if(this.terrainWorldKey!==worldKey){
      this.clear(this.terrain);this.terrainLayers=new Map();this.terrainWorldKey=worldKey;
    }
    this.liveTerrainLayers=new Set();
    const key=value=>JSON.stringify(value),levels=state.buildings.map(b=>[b.id,b.x,b.y,b.width,b.depth,this.buildingLevel(b)]);
    this.terrainLayer('ground',key([state.tiles,state.scenery,!!state.civilians.total]),()=>this.buildGround(state));
    const walls=new Map();
    for(const w of state.walls){if(!walls.has(w.building))walls.set(w.building,[]);walls.get(w.building).push(w);}
    for(const b of state.buildings){
      const limit=this.buildingLevel(b),links=state.stairs.filter(([a])=>a[0]>=b.x&&a[0]<b.x+b.width&&a[1]>=b.y&&a[1]<b.y+b.depth);
      const knownWalls=walls.get(b.id)||[];
      this.terrainLayer('building:'+b.id,key([b,limit,knownWalls.filter(w=>w.a[2]<=limit),links]),()=>addBuilding(this,b,{...state,walls:knownWalls,stairs:links}));
    }
    for(const prop of state.props)this.terrainLayer('prop:'+prop.id,key(prop),()=>addProp(this,prop));
    for(const [a,b] of state.ladders){
      const building=state.buildings.find(v=>b[0]>=v.x&&b[0]<v.x+v.width&&b[1]>=v.y&&b[1]<v.y+v.depth);
      this.terrainLayer('ladder:'+a.join(',')+':'+b.join(','),key([a,b,building?this.buildingLevel(building):b[2]]),()=>this.buildLadder(state,a,b));
    }
    this.terrainLayer('fog',key([state.fog,levels]),()=>this.buildFog(state));
    this.terrainLayer('objective',key(state.mission.flag),()=>this.buildObjective(state));
    for(const [id,entry] of this.terrainLayers)if(!this.liveTerrainLayers.has(id)){
      this.clear(entry.group);entry.group.dispose();this.terrainLayers.delete(id);
    }
    this.pickables=[];this.portalModels.clear();this.terrainHoverItems=[];
    for(const entry of this.terrainLayers.values()){
      this.pickables.push(...entry.pickables);this.terrainHoverItems.push(...entry.hover);
      for(const [id,portal] of entry.portals)this.portalModels.set(id,portal);
    }
    const pickSurfaces=state.surfaces.filter(([x,y,z])=>this.surfaceVisible(x,y,z));
    this.pickSurfaceSet=new Set(pickSurfaces.map(p=>p.join(',')));this.pickSurfaceLevels=[...new Set(pickSurfaces.map(p=>p[2]))];
  }
  /** Ground and street geometry change only when terrain is discovered or damaged. */
  buildGround(state){
    const theme=state.scenery;
    const natural=['woods','farm'].includes(state.theme),groundMaterial=natural?this.groundMat:this.pavedGroundMat;
    this.groundMat.color.set(natural?theme.ground:0xffffff);this.pavedGroundMat.color.set(natural?0xc6c0b4:theme.ground);this.groundAccentMat.color.set(0xffffff);
    const n=state.size,c=(n-1)/2;
    this.box(this.terrain,n+(['urban','streets','woods'].includes(state.theme)?0:2),.4,n+(['urban','streets','woods'].includes(state.theme)?0:2),c,-.4,c,0x18282b);
    const ground=new G.Mesh(new G.PlaneGeometry(state.size,state.size),groundMaterial);ground.rotation.x=-Math.PI/2;ground.position.set(c,-.01,c);ground.receiveShadow=true;this.terrain.add(ground);
    const groundPatches=[];for(let y=0;y<n;y++)for(let x=0;x<n;x++)if(state.tiles[y][x]!=='road'&&(x*37+y*61+state.seed)%17===0)groundPatches.push({x,y:.006,z:y});
    if(!natural&&!['urban','streets'].includes(state.theme))this.tiles(this.terrain,groundPatches,this.groundAccentMat,.985);
    const roads=[],laneMarkers=[];
    for(let y=0;y<n;y++)for(let x=0;x<n;x++){
      const t=state.tiles[y][x];
      if(t==='road')roads.push({x,y:.012,z:y});
      if(t==='road'&&x===theme.road_x&&y%2===0&&!['train_station','urban','streets'].includes(state.theme))laneMarkers.push({x,y:.029,z:y});
      if(t==='crops')for(let k=0;k<3;k++)this.box(this.terrain,.055,.3,.85,x-.3+k*.3,.15,y,0x849052);
      if(t==='low'){this.box(this.terrain,.88,.55,.7,x,.275,y,0x817c61);for(let k=0;k<3;k++)this.box(this.terrain,.26,.2,.76,x-.29+k*.29,.65,y,0xa69d7b);}
      if(t==='high'){this.box(this.terrain,.84,2.2,.72,x,1.1,y,this.concreteMat);for(let k=0;k<4;k++)this.box(this.terrain,.88,.035,.76,x,.3+k*.5,y,0x93968a);}
      if(t==='rubble')for(let i=0;i<4;i++){const m=this.box(this.terrain,.2,.15,.3,x+(i%2-.5)*.45,.075,y+(Math.floor(i/2)-.5)*.4,0x6e6a5a);m.rotation.y=i;}
    }
    if(roads.length)this.tiles(this.terrain,roads,this.material(theme.road,'asphalt'),1);
    if(laneMarkers.length)this.tiles(this.terrain,laneMarkers,this.material(0xc8bd86),.055);
    if(state.theme==='urban')urbanStreets(this,state);
    if(state.theme==='streets')streetCrossing(this,state);
    if(state.theme==='woods')woodlandGround(this,state);
    if(state.theme==='train_station'){
      for(const x of [theme.road_x-.8,theme.road_x+.8]){this.box(this.terrain,.055,.065,n,x,.05,c,0x99a3a0);}
      for(let y=0;y<n;y+=.5)this.box(this.terrain,2.2,.04,.12,theme.road_x,.025,y,0x5e5445);

    }
    if(state.theme==='airport'){
      for(let i=0;i<8;i++)this.box(this.terrain,.14,.04,1.6,theme.road_x-2+i*.6,.05,n-6,0xeee9d5);
    }

    if(state.civilians.total){const evac=this.label('CIVILIAN EVACUATION →','#ace9c0',4);evac.position.set(c,.12,n-.3);this.terrain.add(evac);}
    const grid=new G.GridHelper(n,n,0x9aaca3,0x6e8074);grid.position.set(c,.035,c);grid.material.transparent=true;grid.material.opacity=.16;this.terrain.add(grid);
  }
  /** Rebuild only the ladder affected by discovery or a building cutaway. */
  buildLadder(state,a,b){
    const building=state.buildings.find(v=>b[0]>=v.x&&b[0]<v.x+v.width&&b[1]>=v.y&&b[1]<v.y+v.depth);
    const inside=a[0]===b[0]&&a[1]===b[1],limit=building?this.buildingLevel(building):b[2];
    if(inside&&a[2]>limit)return;
    const bottom=a[2]*3,top=Math.min(b[2],limit+1)*3;
    const h=top-bottom,x=inside?a[0]-.30:a[0]+(b[0]-a[0])*.30,z=a[1];
    const id=`ladder:${a.join(',')}:${b.join(',')}`,data={transition:id,ends:[a,b],x:a[0],y:a[1],z:a[2]};
    const part=(w,h,d,px,py,pz)=>{const m=this.box(this.terrain,w,h,d,px,py,pz,0xc3ac64);m.userData={...data};this.pickables.push(m);};
    for(const offset of [-.23,.23])part(.055,h+.3,.055,x,bottom+h/2+.15,z+offset);
    for(let r=.2;r<h+.3;r+=.3)part(.06,.04,.5,x,bottom+r,z);
    const icon=this.hoverLabel('LADDER ↕',id,'#f9d58a',1);icon.position.set(x+.12,bottom+1,z);this.terrain.add(icon);
  }
  /** Fog consists of two small batched meshes, independent of every structure. */
  buildFog(state){
    const n=state.size;
    const explored=new Set(state.fog.explored.map(p=>p.join(','))),visible=new Set(state.fog.visible.map(p=>p.join(','))),fogTiles={explored:[],unseen:[]};
    for(let y=0;y<n;y++)for(let x=0;x<n;x++){const b=state.buildings.find(b=>x>=b.x&&x<b.x+b.width&&y>=b.y&&y<b.y+b.depth),z=b?this.buildingLevel(b):0,key=`${x},${y},${z}`;if(!visible.has(key))fogTiles[explored.has(key)?'explored':'unseen'].push({x,y:z*3+.17,z:y});}
    this.tiles(this.terrain,fogTiles.explored,this.fogMaterials.explored,1.015);this.tiles(this.terrain,fogTiles.unseen,this.fogMaterials.unseen,1.015);
  }
  /** Objective ownership never invalidates buildings or terrain. */
  buildObjective(state){
    if(state.mission.flag){
      const f=state.mission.flag,color=f.team==='soldier'?0x45b9dc:0xe45f4a,flag=new G.Group();
      this.box(flag,.07,2.8,.07,0,1.4,0,0xc9d3ce);this.box(flag,.28,.08,.28,0,.04,0,0x59676a);
      const finial=new G.Mesh(new G.SphereGeometry(.11,12,8),this.material(0xe4c775));finial.position.y=2.85;flag.add(finial);
      for(let i=0;i<3;i++){const panel=this.box(flag,.62,.42,.035,.34+i*.05,2.52-i*.05,0,color);panel.rotation.z=-.05+i*.08;}
      const marker=this.label(f.label,f.team==='soldier'?'#9cecff':'#ffad91',1.8);marker.position.set(.3,3.25,0);flag.add(marker);
      flag.position.set(f.x,f.z*3,f.y);flag.traverse(o=>{o.userData.x=f.x;o.userData.y=f.y;o.userData.z=f.z;});this.terrain.add(flag);
    }
  }
  /** Create a camera-facing text label. */
  label(text,color='#ffffff',width=1.3){const c=document.createElement('canvas');c.width=256;c.height=64;const ctx=c.getContext('2d');ctx.fillStyle='rgba(12,22,25,.8)';ctx.fillRect(0,0,256,64);ctx.fillStyle=color;ctx.font='bold 27px monospace';ctx.textAlign='center';ctx.fillText(text,128,43,244);const map=new G.CanvasTexture(c),mat=new G.SpriteMaterial({map,depthTest:false});mat.userData.label=true;const s=new G.Sprite(mat);s.scale.set(width,width/4,1);return s;}
  /** Create a cylindrical limb between two joint positions. */
  limb(parent,a,b,r,mat){const m=new G.Mesh(new G.CylinderGeometry(r*.85,r,1,8),mat);m.castShadow=true;parent.add(m);this.placeLimb(m,a,b);return m;}
  /** Position and orient a limb between two joints. */
  placeLimb(m,a,b){const av=new G.Vector3(...a),bv=new G.Vector3(...b),delta=bv.clone().sub(av);m.position.copy(av.add(bv).multiplyScalar(.5));m.scale.y=delta.length();m.quaternion.setFromUnitVectors(new G.Vector3(0,1,0),delta.normalize());}
  /** Build the procedural fallback figure for a unit. */
  figure(u){const root=new G.Group(),body=new G.Group();root.add(body);const friendly=u.team==='soldier',civilian=u.team==='civilian',vest=this.material(friendly?0x53533c:0x3e494e),black=this.material(0x252c2a);
    const knee=u.stance==='kneeling',prone=u.stance==='prone',hip=knee?.52:.85,shoulder=hip+.43,legs=[],arms=[];
    const gun=new G.Group();gun.position.set(.10,shoulder-.15,-.36);body.add(gun);
    if(u.weapon==='RPG-7'){
      const tube=new G.Mesh(new G.CylinderGeometry(.065,.065,.85,10),vest);tube.rotation.x=Math.PI/2;gun.add(tube);const tip=new G.Mesh(new G.ConeGeometry(.1,.25,10),vest);tip.rotation.x=-Math.PI/2;tip.position.z=-.53;gun.add(tip);
    }else if(['Frag grenade','Smoke grenade','Demolition charge','Medikit'].includes(u.weapon)){
      if(u.weapon==='Demolition charge'||u.weapon==='Medikit'){this.box(gun,.22,.14,.18,0,0,0,vest);this.box(gun,.09,.025,.07,0,.08,0,black);}else{const frag=new G.Mesh(u.weapon==='Smoke grenade'?new G.CylinderGeometry(.06,.06,.17,12):new G.SphereGeometry(.075,12,10),vest);gun.add(frag);}
    }else{const pistol=u.weapon==='M9';this.box(gun,.065,.10,pistol?.2:.48,0,0,-.1,black);this.box(gun,.035,.035,pistol?.13:.35,0,.02,pistol?-.2:-.48,black);this.box(gun,.055,.16,.08,0,-.1,0,black);if(!pistol)this.box(gun,.08,.11,.19,0,0,.2,vest);}
    if(u.weapon==='Shotgun'){this.box(gun,.09,.09,.24,0,-.015,-.36,vest);this.box(gun,.045,.04,.38,0,-.045,-.4,black);}
    if(u.weapon==='Medikit'){this.box(gun,.10,.025,.03,0,.097,0,0xe8f0de);this.box(gun,.03,.025,.10,0,.098,0,0xe8f0de);}
    if(prone){body.rotation.x=-Math.PI/2;body.position.set(0,.28,.6);}
    if(civilian)gun.visible=false;
    root.position.set(u.x,u.z*3,u.y);root.rotation.y=u.facing??(friendly?0:Math.PI);
    root.userData.rig={body,legs,arms,hip,shoulder,stance:u.stance,civilian,baseY:body.position.y,baseZ:body.position.z};
    root.userData.unit=u.id;root.traverse(o=>o.userData.unit=u.id);
    const ring=new G.Mesh(new G.RingGeometry(.34,.40,32),new G.MeshBasicMaterial({color:civilian?0x8fe5ad:friendly?0x69cddd:0xec8567,side:G.DoubleSide,transparent:true,opacity:.85}));ring.rotation.x=-Math.PI/2;ring.position.y=.04;root.add(ring);
    const direction=new G.Mesh(new G.ConeGeometry(.10,.22,3),new G.MeshBasicMaterial({color:friendly?0x92e5ed:0xe9ac91}));direction.rotation.x=-Math.PI/2;direction.position.set(0,.06,-.58);direction.userData.unit=u.id;root.add(direction);
    const tag=this.healthLabel(u.name,u.hp,u.max_hp,civilian?'#bcebc6':friendly?'#b8edf2':'#ffc0a6',1.35);tag.userData.unit=u.id;tag.position.y=prone?.8:knee?1.5:1.95;root.add(tag);
    this.characters.apply(root,u,gun);
    return root;
  }
  /** Keep characters, skeletons and animations alive when only their positions change. */
  syncActors(state){
    const worldKey=JSON.stringify([state.seed,state.theme,state.size]);
    if(this.actorWorldKey!==worldKey){
      this.clear(this.actors);this.actorLayers=new Map();this.models.clear();this.memoryLayer=null;this.actorWorldKey=worldKey;
    }
    // Animation can introduce a newly revealed actor before its final state arrives.
    const retained=new Set([...this.actorLayers.values()].map(e=>e.group));if(this.memoryLayer)retained.add(this.memoryLayer);
    for(const child of [...this.actors.children])if(!retained.has(child))this.disposeObject(child);
    const live=new Set();this.models.clear();
    for(const u of state.units){
      if(!this.actorVisible(u))continue;live.add(u.id);
      const signature=JSON.stringify([u.id,u.name,u.team,u.hp,u.max_hp,u.stance,u.weapon,u.hp<=0?[u.x,u.y,u.z]:null]);
      let entry=this.actorLayers.get(u.id);
      if(entry?.signature!==signature){
        if(entry)this.disposeObject(entry.group);
        const group=new G.Group();this.actors.add(group);entry={group,signature,model:null};
        if(u.hp<=0){const root=this.actors;this.actors=group;try{this.corpse(u);}finally{this.actors=root;}}
        else{entry.model=this.figure(u);group.add(entry.model);}
        this.actorLayers.set(u.id,entry);
      }
      if(entry.model){
        entry.model.position.set(u.x,u.z*3,u.y);entry.model.rotation.y=u.facing??(u.team==='soldier'?0:Math.PI);entry.model.visible=true;
        const character=this.characters.instances.get(entry.model);if(character)character.unit=u;
        this.models.set(u.id,entry.model);
      }
    }
    for(const [id,entry] of this.actorLayers)if(!live.has(id)){this.disposeObject(entry.group);this.actorLayers.delete(id);}
    const memories=(state.last_seen||[]).filter(m=>this.surfaceVisible(m.x,m.y,m.z)),memoryKey=JSON.stringify(memories);
    if(!this.memoryLayer||this.memoryKey!==memoryKey){
      if(this.memoryLayer)this.disposeObject(this.memoryLayer);
      const root=this.actors;this.memoryLayer=new G.Group();root.add(this.memoryLayer);this.actors=this.memoryLayer;
      try{
      for(const m of memories){if(!this.surfaceVisible(m.x,m.y,m.z))continue;const ghost=new G.Group(),mat=new G.MeshBasicMaterial({color:0x9ba3a8,transparent:true,opacity:.42,depthWrite:false});const body=new G.Mesh(new G.CapsuleGeometry(.19,.65,4,8),mat);body.position.y=.7;ghost.add(body);const head=new G.Mesh(new G.SphereGeometry(.14,8,6),mat);head.position.y=1.3;ghost.add(head);const tag=this.label(`LAST SEEN · R${m.round}`,'#adb5ba',1.65);tag.position.y=1.65;ghost.add(tag);ghost.position.set(m.x,m.z*3,m.y);ghost.traverse(o=>o.userData.memory=m.id);this.actors.add(ghost);}
      }finally{this.actors=root;}
      this.memoryKey=memoryKey;
    }
    this.actorHoverItems=[];this.actors.traverse(o=>{if(o.userData.hoverFor||o.userData.health)this.actorHoverItems.push(o);});
  }
  /** Synchronize the 3D scene with authoritative game state. */
  sync(state,selected,target,mode,aim){
    this.mode=mode;
    const night=state.lighting==='night';this.sky.intensity=night?.18:.85;this.sun.intensity=night?.32:2.6;this.sun.diffuse=B.Color3.FromHexString(night?'#7592bd':'#fff1db');
    const first=!this.state||this.state.seed!==state.seed||this.state.theme!==state.theme||this.state.size!==state.size;this.state=state;this.selected=selected;
    if(first){this.home();const u=state.units.find(u=>u.id===selected);if(u){this.focus(u);this.camera.position.copy(this.controls.target).add(new G.Vector3(17,23,22));}}
    this.background.sync(state);
    const terrainContext=JSON.stringify([this.viewMode,state.buildings.map(b=>this.buildingLevel(b))]);
    if(this.terrainState!==state||this.terrainContext!==terrainContext){this.build(state);this.terrainState=state;this.terrainContext=terrainContext;}
    this.syncActors(state);
    this.updateHover(true);
    this.lastSeed=state.seed;
    this.clear(this.overlay);this.flames=[];
    const points=mode==='attack'?[]:state.movement[selected]||[];
    if(state.status==='active')for(const cost of [1,2])this.tiles(this.overlay,points.filter(p=>p.cost===cost&&this.surfaceVisible(p.x,p.y,p.z)).map(p=>({x:p.x,y:p.z*3+.05,z:p.y})),this.moveMaterials[cost-1],.91);
    if(this.renderer==='webgpu')this.syncAtmosphere(state);
    for(const smoke of state.smoke||[]){if(this.renderer!=='webgpu')for(let i=0;i<9;i++){const m=new G.Sprite(new G.SpriteMaterial({map:this.smokeMap,color:0xaab0ad,opacity:.6,depthWrite:false}));m.position.set(smoke.x+Math.sin(i*2.4)*smoke.radius*.6,smoke.z*3+.6+(i%3)*.4,smoke.y+Math.cos(i*2.4)*smoke.radius*.6);m.scale.set(smoke.radius*1.7,smoke.radius*1.7,1);this.overlay.add(m);}const label=this.label(`SMOKE ${smoke.turns}`,'#e2e5e2',1.5);label.position.set(smoke.x,smoke.z*3+2.3,smoke.y);this.overlay.add(label);}
    for(const fire of state.fires||[]){if(this.renderer!=='webgpu'){for(let i=0;i<4;i++){const flame=new G.Mesh(new G.IcosahedronGeometry(.25+i*.035,1),new G.MeshBasicMaterial({color:i%2?0xffb12b:0xf04a19,transparent:true,opacity:.82,depthWrite:false}));flame.position.set(fire.x+(i%2-.5)*.28,fire.z*3+.28+(i%3)*.14,fire.y+(Math.floor(i/2)-.5)*.25);this.overlay.add(flame);this.flames.push({mesh:flame,base:flame.position.y,phase:i*1.7+fire.x});}for(let i=0;i<5;i++){const smoke=new G.Sprite(new G.SpriteMaterial({map:this.smokeMap,color:0x4f5655,opacity:.52,depthWrite:false}));smoke.position.set(fire.x+Math.sin(i*2.3)*.38,fire.z*3+.9+(i%3)*.42,fire.y+Math.cos(i*2.3)*.38);smoke.scale.set(1.4+i*.16,1.4+i*.16,1);this.overlay.add(smoke);}}const label=this.label(`FIRE · ${fire.turns}`,'#ffb16e',1.35);label.position.set(fire.x,fire.z*3+2.7,fire.y);this.overlay.add(label);}
    for(const charge of state.charges||[]){this.box(this.overlay,.35,.18,.28,charge.x,charge.z*3+.1,charge.y,0x605746);const label=this.label(`CHARGE · ${charge.turns} PHASES`,'#ffb27d',1.7);label.position.set(charge.x,charge.z*3+.6,charge.y);this.overlay.add(label);}
    const u=state.units.find(u=>u.id===selected&&u.hp>0);
    if(u&&this.actorVisible(u)){const m=new G.Mesh(new G.RingGeometry(.45,.49,40),new G.MeshBasicMaterial({color:0xd6fdff,side:G.DoubleSide}));m.rotation.x=-Math.PI/2;m.position.set(u.x,u.z*3+.065,u.y);this.overlay.add(m);}
    if(aim&&u&&mode==='attack'&&state.weapons[u.weapon].radius){const radius=state.weapons[u.weapon].radius;const m=new G.Mesh(new G.RingGeometry(radius-.04,radius+.04,64),new G.MeshBasicMaterial({color:0xffad68,side:G.DoubleSide,depthTest:false}));m.rotation.x=-Math.PI/2;m.position.set(aim.x,aim.z*3+.08,aim.y);this.overlay.add(m);}
    const t=state.units.find(u=>u.id===target&&u.hp>0);if(u&&t&&this.actorVisible(u)&&this.actorVisible(t)&&mode!=='attack'){const line=new G.Line(new G.BufferGeometry().setFromPoints([new G.Vector3(u.x,u.z*3+1,u.y),new G.Vector3(t.x,t.z*3+1,t.y)]),new G.LineDashedMaterial({color:0xf3bc87,dashSize:.15,gapSize:.12}));line.computeLineDistances();this.overlay.add(line);}
  }
  /** Resolve a canvas pointer event to tactical scene data. */
  pick(e){this.scene.updateMatrixWorld(true);this.camera.updateMatrixWorld();const r=this.canvas.getBoundingClientRect();this.pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.ray.setFromCamera(this.pointer,this.camera);const hits=this.ray.intersectObjects([...this.actors.children,...this.pickables],true).concat(this.ray.intersectTileLayers(this.pickSurfaceLevels||[],this.pickSurfaceSet||new Set())).sort((a,b)=>a.distance-b.distance);const hit=hits.find(h=>!h.object.userData.health&&h.object.visible&&h.object.parent?.visible&&(h.object.userData.transition||h.object.userData.memory||h.object.userData.portal||h.object.userData.unit||h.object.userData.structure||h.object.userData.x!==undefined));if(!hit)return null;const data={...hit.object.userData};if(data.unit||data.memory||data.transition)return data;let structure=this.state.buildings.concat(this.state.props).find(p=>p.id===data.structure);if(structure){data.x=Math.max(structure.x,Math.min(structure.x+structure.width-1,Math.round(hit.point.x)));data.y=Math.max(structure.y,Math.min(structure.y+structure.depth-1,Math.round(hit.point.z)));data.z=Math.max(0,Math.min(structure.level||0,Math.floor((hit.point.y+.05)/3)));}else if(this.mode==='attack'&&data.x!==undefined){structure=this.state.buildings.find(b=>!b.destroyed&&data.z===b.level&&data.x>=b.x&&data.x<b.x+b.width&&data.y>=b.y&&data.y<b.y+b.depth);if(structure)data.structure=structure.id;}return data;}
  /** Update hover. */
  updateHover(force=false){
    if(!this.state||!this.ray)return;
    const hit=this.hoverPointer?this.pick(this.hoverPointer):null;
    const key=hit?.portal?`portal:${hit.portal}`:hit?.transition|| (hit?.unit?`unit:${hit.unit}`:hit?.structure?`structure:${hit.structure}`:null);
    const hoverItems=[...(this.terrainHoverItems||[]),...(this.actorHoverItems||[])];
    if(force||key!==this.hoverKey){this.hoverKey=key;for(const o of hoverItems){if(o.userData.hoverFor)o.visible=!!key&&key===o.userData.hoverFor;else o.visible=!!key&&key===(o.userData.unit?`unit:${o.userData.unit}`:`structure:${o.userData.structure}`);}}
    // Keep depth-tested opening/transition labels just in front of the picked
    // surface, so their billboard edges are not sliced by the wall itself.
    for(const o of this.terrainHoverItems||[])if(o.userData.hoverFor&&o.visible){o.userData.labelAnchor??=o.position.clone();const toward=this.camera.position.clone().sub(o.userData.labelAnchor).normalize();o.position.copy(o.userData.labelAnchor).addScaledVector(toward,.8);}
    this.onHover?.(hit);
  }
  /** Create a reusable label shown for hover feedback. */
  hoverLabel(text,key,color,width){const s=this.label(text,color,width);s.material.depthTest=true;s.material.depthWrite=false;s.userData.hoverFor=key;s.visible=false;return s;}
  /** Create a hover label containing name and health. */
  healthLabel(name,hp,max,color='#d9cfac',width=2.3){const c=document.createElement('canvas');c.width=384;c.height=96;const ctx=c.getContext('2d');ctx.fillStyle='#0b1b25de';ctx.fillRect(0,0,384,96);ctx.fillStyle=color;ctx.font='bold 23px system-ui';ctx.textAlign='center';ctx.fillText(name.toUpperCase(),192,29,370);ctx.font='19px monospace';ctx.fillText(`${hp} / ${max} HP`,192,55);ctx.fillStyle='#3b484b';ctx.fillRect(14,68,356,10);ctx.fillStyle=color;ctx.fillRect(14,68,356*Math.max(0,hp/max),10);const map=new G.CanvasTexture(c),mat=new G.SpriteMaterial({map,depthTest:false});mat.userData.label=true;const sprite=new G.Sprite(mat);sprite.scale.set(width,width/4,1);sprite.userData.health=true;sprite.visible=false;return sprite;}
  /** Show preview. */
  showPreview(preview){if(!preview)return;const u=this.state.units.find(u=>u.id===this.selected);if(!u)return;const points=preview.via?[[u.x,u.y,u.z],[preview.via.x,preview.via.y,preview.via.z],[preview.x,preview.y,preview.z]]:preview.path?[[u.x,u.y,u.z],...preview.path]:preview.x!==undefined?[[u.x,u.y,u.z],[preview.x,preview.y,preview.z]]:[];if(!points.length)return;const color=preview.action==='move'?0x8fe9ee:0xffc28b;const line=new G.Line(new G.BufferGeometry().setFromPoints(points.map(p=>new G.Vector3(p[0],p[2]*3+.2,p[1]))),new G.LineDashedMaterial({color,dashSize:.2,gapSize:.12,depthTest:false}));line.computeLineDistances();this.overlay.add(line);const p=points.at(-1);const marker=new G.Mesh(new G.RingGeometry(.32,.40,40),new G.MeshBasicMaterial({color,side:G.DoubleSide,depthTest:false}));marker.rotation.x=-Math.PI/2;marker.position.set(p[0],p[2]*3+.1,p[1]);this.overlay.add(marker);}
  /** Move the tactical camera focus to a unit. */
  focus(u){if(!u)return;const delta=new G.Vector3(u.x,u.z*3,u.y).sub(this.controls.target);this.controls.target.add(delta);this.camera.position.add(delta);this.controls.update();this.camera.updateMatrixWorld();this.updateHover();}
  /** Reset the tactical camera to a full-map view. */
  home(){const c=((this.state?.size||30)-1)/2;this.camera.position.set(c+this.state.size*.85,this.state.size*1.1,c+this.state.size);this.controls.target.set(c,0,c);this.controls.update();}
  /** Create a persistent visual marker for a fallen unit. */
  corpse(u){
    const model=this.figure({...u,stance:'standing',corpse:true}),body=model.children[0];
    model.traverse(o=>{delete o.userData.unit;Object.assign(o.userData,{x:u.x,y:u.y,z:u.z});});
    for(const child of [...model.children].slice(1)){child.geometry?.dispose();child.material?.map?.dispose();child.material?.dispose();model.remove(child);}
    body.rotation.set(-Math.PI/2,0,.2);body.position.set(0,.18,.60);model.rotation.y=(u.x+u.y)*.7;this.actors.add(model);
    for(let i=0;i<5;i++){const blood=new G.Mesh(new G.CircleGeometry(i? .12:.5,12),new G.MeshBasicMaterial({color:i?0x8d2526:0x591419,transparent:true,opacity:.85,depthWrite:false}));blood.rotation.x=-Math.PI/2;blood.scale.y=.7;blood.position.set(u.x+Math.sin(i*2.4)*.48,u.z*3+.055,u.y+Math.cos(i*2.4)*.48);this.actors.add(blood);}
  }
  /** Create a short-lived particle burst at a world position. */
  async burst(point,color,radius,duration){const particles=[];for(let i=0;i<12;i++){const m=color===0x73766d?new G.Sprite(new G.SpriteMaterial({map:this.smokeMap,color,depthWrite:false})):new G.Mesh(new G.IcosahedronGeometry(.04,0),new G.MeshBasicMaterial({color,transparent:true}));m.position.copy(point);this.fx.add(m);particles.push({m,v:new G.Vector3(Math.sin(i*2.4)*radius,.25+(i%4)*.2,Math.cos(i*2.4)*radius)});}await this.tween(duration,t=>{for(const {m,v} of particles){m.position.copy(point).addScaledVector(v,t);m.position.y-=t*t*.3;m.material.opacity=1-t;if(color===0x73766d)m.scale.setScalar(1+t*4);}});}
  /** Apply stance-aware limb motion for the current gait phase. */
  gait(model,phase,climbing=false){
    const r=model.userData.rig;if(!r)return;if(model.userData.animated){this.characters.motion(model,climbing?'climb':'walk');return;}
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
  /** Animate authoritative events before applying their final state. */
  async animate(events,followEnemies=false){
    for(const e of events||[]){
      const actor=e.actor||this.state.units.find(u=>u.id===e.unit);
      const eventPoint=e.origin||(e.x!==undefined?[e.x,e.y,e.z]:null)||e.point;
      const follow=followEnemies&&e.type!=='hide'&&(actor?.team==='alien'||['blast','impact','hurt','portal'].includes(e.type));
      if(follow){
        const p=eventPoint||[actor.x,actor.y,actor.z];
        const from=this.controls.target.clone(),to=new G.Vector3(p[0],p[2]*3,p[1]);
        if(from.distanceTo(to)>.1)await this.tween(220,t=>{const v=from.clone().lerp(to,t);this.focus({x:v.x,y:v.z,z:v.y/3});});
      }
      if(e.type!=='impact')await actionAudio.play(e);
      if(e.type==='hide'){const m=this.models.get(e.unit);if(m)m.visible=false;continue;}
      if(e.type==='move'){
        let model=this.models.get(e.unit);
        if(!model){const u=e.actor||this.state.units.find(u=>u.id===e.unit);if(!u)continue;model=this.figure(u);this.actors.add(model);this.models.set(e.unit,model);}
        model.visible=true;
        if(e.origin)model.position.set(e.origin[0],e.origin[2]*3,e.origin[1]);
        const start=model.position.clone(),end=new G.Vector3(e.x,e.z*3,e.y),climbing=Math.abs(start.y-end.y)>.1;
        const fromYaw=model.rotation.y,toYaw=(start.x!==end.x||start.z!==end.z)?Math.atan2(start.x-end.x,start.z-end.z):fromYaw;const yawDelta=Math.atan2(Math.sin(toYaw-fromYaw),Math.cos(toYaw-fromYaw));
        model.userData.walking=true;
        const duration=climbing?650:model.userData.rig.stance==='prone'?340:220;
        await this.tween(duration,t=>{model.position.lerpVectors(start,end,t);if(follow)this.focus({x:model.position.x,y:model.position.z,z:model.position.y/3});model.rotation.y=fromYaw+yawDelta*Math.min(1,t*4);this.gait(model,t*Math.PI*2,climbing);});
        model.userData.walking=false;this.characters.motion(model,'idle');
      }
      if(e.type==='face'){const model=this.models.get(e.unit);if(model){const from=model.rotation.y,delta=Math.atan2(Math.sin(e.facing-from),Math.cos(e.facing-from));await this.tween(150,t=>model.rotation.y=from+delta*t);}}
      if(e.type==='peek_out'||e.type==='peek_return'){const model=this.models.get(e.unit);if(model){const from=model.position.clone(),to=new G.Vector3(e.point[0],e.point[2]*3,e.point[1]);await this.tween(220,t=>model.position.lerpVectors(from,to,t));}if(e.contacts){for(const u of e.contacts){if(!this.models.has(u.id)){const m=this.figure(u);this.actors.add(m);this.models.set(u.id,m);}}await this.tween(280,()=>{});}}
      if(e.type==='heal'){const p=new G.Vector3(e.point[0],e.point[2]*3+1,e.point[1]);await this.burst(p,0x80f3b4,.5,400);this.clear(this.fx);}
      if(e.type==='rocket_launch'&&e.target){const from=new G.Vector3(e.point[0],e.point[2]*3+1,e.point[1]),to=new G.Vector3(e.target[0],e.target[2]*3+.4,e.target[1]),rocket=new G.Mesh(new G.SphereGeometry(.1,8,6),new G.MeshBasicMaterial({color:0xffdb9a}));this.fx.add(rocket);await this.tween(250,t=>rocket.position.lerpVectors(from,to,t));this.clear(this.fx);}
      if(e.type==='throw'){const points=[e.origin,...(e.via?[e.via]:[]),e.point].map(p=>new G.Vector3(p[0],p[2]*3+1,p[1])),ball=new G.Mesh(new G.SphereGeometry(.09,8,6),this.material(0x718268));this.fx.add(ball);for(let i=1;i<points.length;i++)await this.tween(i===1&&e.via?130:350,t=>{ball.position.lerpVectors(points[i-1],points[i],t);const distance=points[i-1].distanceTo(points[i]),arc=i===1&&e.via?.15:Math.max(1.5,Math.min(3,distance*.4));ball.position.y+=Math.sin(t*Math.PI)*arc;});this.clear(this.fx);}
      if(e.type==='portal'){const model=this.portalModels.get(e.id);if(model){const from=model.rotation.y,to=e.open?Math.PI*.48:0;await this.tween(240,t=>model.rotation.y=from+(to-from)*t);}}
      if(e.type==='shot'||e.type==='impact'){
        const point=new G.Vector3(e.point[0]+(e.hit||e.structure?0:.45),e.point[2]*3+(e.structure?1:e.hit?.8:.12),e.point[1]+(e.hit||e.structure?0:.3));
        if(e.origin){const model=this.models.get(e.unit);if(model){const yaw=Math.atan2(e.origin[0]-e.point[0],e.origin[1]-e.point[1]),from=model.rotation.y,delta=Math.atan2(Math.sin(yaw-from),Math.cos(yaw-from));await this.tween(120,t=>model.rotation.y=from+delta*t);}const origin=new G.Vector3(e.origin[0],e.origin[2]*3+1.1,e.origin[1]);const bullet=new G.Mesh(new G.SphereGeometry(.07,6,4),new G.MeshBasicMaterial({color:0xffe8b2}));this.fx.add(bullet);await this.tween(e.burst?35:100,t=>bullet.position.lerpVectors(origin,point,t));this.clear(this.fx);}
        actionAudio.play({type:'impact',point:e.point});await this.burst(point,e.hit&&!e.structure?0xb52a2c:0xffd18a,.7,e.burst?65:240);this.clear(this.fx);
      }
      if(e.type==='blast'&&this.renderer==='webgpu'){
        const effect=detailedEffects(this.nativeScene),origin=[e.x,e.z*3+.2,e.y];
        try{await this.tween(1700,t=>effect.update({kind:'explosion',age:t*4},origin,Math.max(.5,e.radius*.55)));}finally{effect.dispose();}
      }
      if(e.type==='blast'&&this.renderer!=='webgpu'){
        const point=new G.Vector3(e.x,e.z*3+.35,e.y);
        const fireballs=[];for(let i=0;i<7;i++){const fire=new G.Mesh(new G.IcosahedronGeometry(.3+(i%3)*.12,1),new G.MeshBasicMaterial({color:i%2?0xffd05a:0xff5a20,transparent:true,opacity:.95}));fire.position.copy(point);this.fx.add(fire);fireballs.push({fire,offset:new G.Vector3(Math.sin(i*2.4),.25+(i%3)*.28,Math.cos(i*2.4))});}
        const ring=new G.Mesh(new G.RingGeometry(.8,1,32),new G.MeshBasicMaterial({color:0xfac881,transparent:true,side:G.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.copy(point);ring.position.y=e.z*3+.20;this.fx.add(ring);
        await this.tween(500,t=>{for(const f of fireballs){f.fire.position.copy(point).addScaledVector(f.offset,t*e.radius*.7);f.fire.scale.setScalar(.4+Math.sin(t*Math.PI)*e.radius*1.3);f.fire.material.opacity=1-t;}ring.scale.setScalar(.2+t*e.radius*2.2);ring.material.opacity=1-t;});this.clear(this.fx);
        await this.burst(point,0x73766d,e.radius*1.5,450);this.clear(this.fx);
      }
      if(e.type==='evacuate'){const m=this.models.get(e.unit);if(m)m.visible=false;}
    }
  }
  /** Animate a value over a duration using animation frames. */
  tween(ms,fn){return new Promise(resolve=>{const start=performance.now();const tick=now=>{const t=Math.max(0,Math.min(1,(now-start)/ms));fn(t);if(t<1)requestAnimationFrame(tick);else resolve();};requestAnimationFrame(tick);});}
}
