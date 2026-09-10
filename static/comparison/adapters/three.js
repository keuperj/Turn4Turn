import * as T from 'three';
import {GLTFLoader} from '../vendor/loaders/GLTFLoader.js';
export async function create(canvas){
 const renderer=new T.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.toneMapping=T.ACESFilmicToneMapping;
 const scene=new T.Scene();scene.background=new T.Color('#9aaeb8');const camera=new T.PerspectiveCamera(45,1,.1,120);
 scene.add(new T.HemisphereLight('#dbeaff','#8e8773',1.8));const sun=new T.DirectionalLight('#fff1db',3);sun.position.set(-6,12,8);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-15,right:15,top:15,bottom:-15,far:45});sun.shadow.normalBias=.025;scene.add(sun);
 const loader=new GLTFLoader();const [env,person,vehicle]=await Promise.all(['courtyard','character','CesiumMilkTruck'].map(n=>loader.loadAsync(`assets/${n}.glb`)));
 for(const asset of [env,person,vehicle]){asset.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});scene.add(asset.scene);}
 function normalize(root,height){root.updateMatrixWorld(true);const b=new T.Box3().setFromObject(root),size=b.getSize(new T.Vector3()),scale=height/size.y;const wrap=new T.Group();scene.remove(root);wrap.add(root);root.scale.multiplyScalar(scale);root.position.set(-(b.min.x+b.max.x)/2*scale,-b.min.y*scale,-(b.min.z+b.max.z)/2*scale);scene.add(wrap);return wrap;}
 const actor=normalize(person.scene,1.8),truck=normalize(vehicle.scene,2.4);truck.position.set(5,0,-.2);truck.rotation.y=-Math.PI/2;
 const mixer=new T.AnimationMixer(person.scene),clips=person.animations,actions=clips.map(c=>mixer.clipAction(c));let active=null;
 const effects=Array.from({length:42},(_,i)=>{const m=new T.Mesh(new T.SphereGeometry(1,10,7),new T.MeshStandardMaterial({color:i<10?'#ff992e':'#5b6266',transparent:true,depthWrite:false,roughness:1}));scene.add(m);m.visible=false;return m;});
 return {version:T.REVISION,clips:clips.map(c=>c.name),
 resize(w,h){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();},
 camera(eye,target){camera.position.set(...eye);camera.lookAt(...target);},
 cutaway(mode){env.scene.traverse(o=>{if(o.name==='roof')o.visible=mode==='exterior';if(o.name==='level_1')o.visible=mode!=='ground';if(o.name==='near_0')o.visible=mode!=='ground';if(o.name==='near_1')o.visible=mode==='exterior';});},
 motion(name){const i=clips.findIndex(c=>c.name.toLowerCase().split('|').pop()===name);const next=actions[i<0?0:i];if(next&&next!==active){next.reset().fadeIn(.25).play();active?.fadeOut(.25);active=next;}},
 update(dt,pos,yaw,fx){mixer.update(dt);actor.position.set(...pos);actor.rotation.y=yaw;effects.forEach((m,i)=>{const p=fx[i];m.visible=!!p;if(p){m.position.set(...p.pos);m.scale.setScalar(p.scale);m.material.opacity=p.opacity;m.material.emissive.setHex(p.fire?0xe55d12:0x000000);}});renderer.render(scene,camera);},
 stats(){return {draws:renderer.info.render.calls,triangles:renderer.info.render.triangles};},
 capture(){return canvas.toDataURL('image/png');}
 };
}
