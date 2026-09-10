export async function create(canvas){
 const p=window.pc,app=new p.Application(canvas,{graphicsDeviceOptions:{deviceTypes:['webgl2'],antialias:true,preserveDrawingBuffer:true,alpha:false}});
 app.graphicsDevice.maxPixelRatio=1;app.setCanvasFillMode(p.FILLMODE_NONE,canvas.clientWidth,canvas.clientHeight);app.setCanvasResolution(p.RESOLUTION_AUTO);app.scene.ambientLight=new p.Color(.48,.51,.53);
 const camera=new p.Entity('camera');camera.addComponent('camera',{clearColor:new p.Color(.604,.682,.722),toneMapping:p.TONEMAP_ACES,gammaCorrection:p.GAMMA_SRGB,fov:45,nearClip:.1,farClip:120});app.root.addChild(camera);
 const sun=new p.Entity('sun');sun.addComponent('light',{type:'directional',color:new p.Color(1,.945,.859),intensity:3,castShadows:true,shadowDistance:40,shadowResolution:2048,shadowBias:.15,normalOffsetBias:.025,shadowType:p.SHADOW_PCF3});sun.setPosition(-6,12,8);sun.setRotation(new p.Quat().setFromDirections(new p.Vec3(0,-1,0),new p.Vec3(6,-12,-8).normalize()));app.root.addChild(sun);
 function load(name){return new Promise((resolve,reject)=>app.assets.loadFromUrl(`assets/${name}.glb`,'container',(err,asset)=>err?reject(err):resolve(asset)));}
 const [env,person,vehicle]=await Promise.all(['courtyard','character','CesiumMilkTruck'].map(load));
 const world=env.resource.instantiateRenderEntity();app.root.addChild(world);
 function normalize(asset,height){const root=asset.resource.instantiateRenderEntity();app.root.addChild(root);const renders=root.findComponents('render'),bounds=new p.BoundingBox();let first=true;for(const r of renders)for(const m of r.meshInstances){if(first){bounds.copy(m.aabb);first=false;}else bounds.add(m.aabb);}const scale=height/(bounds.halfExtents.y*2),wrap=new p.Entity('placement');root.reparent(wrap);root.setLocalScale(scale,scale,scale);root.setLocalPosition(-bounds.center.x*scale,-(bounds.center.y-bounds.halfExtents.y)*scale,-bounds.center.z*scale);app.root.addChild(wrap);return {wrap,root};}
 const actor=normalize(person,1.8),truck=normalize(vehicle,2.4);truck.wrap.setLocalPosition(5,0,-.2);truck.wrap.setLocalEulerAngles(0,-90,0);
 actor.root.addComponent('anim',{activate:true});const clips=person.resource.animations.map(a=>({name:a.resource.name,resource:a.resource}));
 actor.root.anim.loadStateGraph({layers:[{name:'Base',states:[{name:'START'},...clips.map(c=>({name:c.name,speed:1,loop:true}))],transitions:[{from:'START',to:clips.find(c=>c.name.endsWith('|Walk')).name}]}],parameters:{}});
 for(const clip of clips)actor.root.anim.assignAnimation(clip.name,clip.resource);
 let active=null;
 const effects=Array.from({length:42},(_,i)=>{const e=new p.Entity('fx');e.addComponent('render',{type:'sphere',castShadows:false,receiveShadows:false});const mat=new p.StandardMaterial();mat.diffuse=new p.Color(i<10?1:.357,i<10?.6:.384,i<10?.18:.4);mat.blendType=p.BLEND_NORMAL;mat.depthWrite=false;mat.update();e.render.material=mat;app.root.addChild(e);e.enabled=false;return e;});
 return {version:p.version,clips:clips.map(c=>c.name),
 resize(w,h){app.setCanvasResolution(p.RESOLUTION_FIXED,w,h);canvas.style.width='100%';canvas.style.height='100%';camera.camera.aspectRatio=w/h;},camera(eye,target){camera.setPosition(...eye);camera.lookAt(new p.Vec3(...target));},
 cutaway(mode){for(const [name,visible] of [['roof',mode==='exterior'],['level_1',mode!=='ground'],['near_0',mode!=='ground'],['near_1',mode==='exterior']]){const n=world.findByName(name);if(n)n.enabled=visible;}},
 motion(name){const clip=clips.find(c=>c.name.toLowerCase().split('|').pop()===name)||clips[0];if(clip&&active!==clip.name){actor.root.anim.baseLayer.transition(clip.name,.25);active=clip.name;}},
 update(dt,pos,yaw,fx){actor.wrap.setLocalPosition(...pos);actor.wrap.setLocalEulerAngles(0,yaw*180/Math.PI,0);effects.forEach((e,i)=>{const v=fx[i];e.enabled=!!v;if(v){e.setLocalPosition(...v.pos);e.setLocalScale(v.scale*2,v.scale*2,v.scale*2);e.render.material.opacity=v.opacity;e.render.material.emissive=new p.Color(v.fire?.9:0,v.fire?.36:0,v.fire?.07:0);e.render.material.update();}});app.update(dt);app.render();},
 stats(){return {draws:app.stats.drawCalls.total,triangles:app.stats.frame.triangles};},capture(){return canvas.toDataURL('image/png');}
 };
}
