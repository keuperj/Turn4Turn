/* Application scene primitives backed exclusively by Babylon.js.
 * Grid scenery and tactical overlays use this small API; native Babylon objects
 * remain available as .native for asset loading, animation and diagnostics.
 */
export const B=window.BABYLON;
let world,shadows;
export function configure(scene,shadowGenerator){world=scene;shadows=shadowGenerator;}
export const DoubleSide=2,RepeatWrapping=1,SRGBColorSpace='srgb';
export class Vector3 extends B.Vector3 {
 static link(v){const out=new Vector3();for(const [field,key] of [['_x','x'],['_y','y'],['_z','z']])Object.defineProperty(out,field,{get:()=>v[key],set:value=>v[key]=value});return out;}
 copy(v){return this.copyFrom(v);} clone(){return new Vector3(this.x,this.y,this.z);}
 add(v){return this.addInPlace(v);} sub(v){return this.subtractInPlace(v);}
 multiplyScalar(s){return this.scaleInPlace(s);} setScalar(s){return this.set(s,s,s);}
 addScaledVector(v,s){this.x+=v.x*s;this.y+=v.y*s;this.z+=v.z*s;return this;}
 lerp(v,t){return this.lerpVectors(this.clone(),v,t);}
 lerpVectors(a,b,t){return this.set(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,a.z+(b.z-a.z)*t);}
 distanceTo(v){return Math.hypot(this.x-v.x,this.y-v.y,this.z-v.z);}
 toArray(){return [this.x,this.y,this.z];}
 project(camera){const c=camera.native||camera,e=c.getScene().getEngine();const p=B.Vector3.Project(this,B.Matrix.Identity(),c.getViewMatrix().multiply(c.getProjectionMatrix()),new B.Viewport(0,0,e.getRenderWidth(),e.getRenderHeight()));return this.set(p.x/e.getRenderWidth()*2-1,1-p.y/e.getRenderHeight()*2,p.z);}
}
export class Vector2 extends B.Vector2 {}
class Quaternion extends B.Quaternion {
 setFromUnitVectors(a,b){B.Quaternion.FromUnitVectorsToRef(a,b,this);return this;}
}
export class Color {
 constructor(value=0xffffff){this.native=B.Color3.White();this.set(value);}
 set(v){if(v instanceof Color)this.native.copyFrom(v.native);else this.native.copyFrom(B.Color3.FromHexString(typeof v==='number'?'#'+v.toString(16).padStart(6,'0'):v));this.changed?.();return this;}
}
export class Group {
 constructor(native){this.native=native||new B.TransformNode('group',world);this.native.metadata={...(this.native.metadata||{}),owner:this};this.children=[];this.userData={};this.parent=null;this.native.position=new B.Vector3();this.native.rotation=new B.Vector3();this.native.scaling=new B.Vector3(1,1,1);this._position=Vector3.link(this.native.position);this._rotation=Vector3.link(this.native.rotation);this._scale=Vector3.link(this.native.scaling);}
 get position(){return this._position;} get rotation(){return this._rotation;} get scale(){return this._scale;}
 get quaternion(){if(!this.native.rotationQuaternion)this.native.rotationQuaternion=new Quaternion();return this.native.rotationQuaternion;}
 get visible(){return this.native.isEnabled();} set visible(v){this.native.setEnabled(v);}
 add(...nodes){for(const n of nodes){n.parent?.remove(n);n.parent=this;n.native.parent=this.native;if(n._detachedEnabled!==undefined){n.native.setEnabled(n._detachedEnabled);delete n._detachedEnabled;}this.children.push(n);}return this;}
 remove(n){const i=this.children.indexOf(n);if(i>=0)this.children.splice(i,1);n._detachedEnabled=n.native.isEnabled(false);n.native.setEnabled(false);n.native.parent=null;n.parent=null;return this;}
 traverse(fn){fn(this);for(const c of this.children)c.traverse(fn);}
 updateMatrixWorld(){this.native.computeWorldMatrix(true);for(const n of this.native.getDescendants())n.computeWorldMatrix(true);}
 dispose(){this.parent?.remove(this);for(const n of [this.native,...this.native.getChildMeshes()])shadows?.removeShadowCaster(n,false);this.native.dispose(false,false);this.children=[];}
}
export class Scene extends Group {
 constructor(native){super(new B.TransformNode('world',native));this.scene=native;}
}
class Geometry {constructor(kind,options){this.kind=kind;this.options=options;}dispose(){}}
export class BoxGeometry extends Geometry{constructor(w,h,d){super('Box',{width:w,height:h,depth:d});}}
export class PlaneGeometry extends Geometry{constructor(w,h){super('Plane',{width:w,height:h,sideOrientation:B.Mesh.DOUBLESIDE});}}
export class SphereGeometry extends Geometry{constructor(r,segments=16){super('Sphere',{diameter:r*2,segments:Math.max(8,segments)});}}
export class IcosahedronGeometry extends Geometry{constructor(r,detail=1){super('IcoSphere',{radius:r,subdivisions:Math.max(1,detail+1),flat:false});}}
export class CylinderGeometry extends Geometry{constructor(top,bottom,h,segments=12){super('Cylinder',{diameterTop:top*2,diameterBottom:bottom*2,height:h,tessellation:segments});}}
export class ConeGeometry extends CylinderGeometry{constructor(r,h,segments=12){super(0,r,h,segments);}}
export class CapsuleGeometry extends Geometry{constructor(r,h){super('Capsule',{radius:r,height:h+2*r,tessellation:12,subdivisions:2});}}
export class CircleGeometry extends Geometry{constructor(r,segments=24){super('Disc',{radius:r,tessellation:segments,sideOrientation:B.Mesh.DOUBLESIDE});}}
export class RingGeometry extends Geometry{constructor(inner,outer,segments=32){super('ring',{inner,outer,segments});}}
export class BufferGeometry extends Geometry{constructor(){super('line',{});}setFromPoints(points){this.options.points=points;return this;}}
export class Texture {
 constructor(native){this.native=native;this.repeat={set:(x,y)=>{native.uScale=x;native.vScale=y;}};}
 set wrapS(v){this.native.wrapU=B.Texture.WRAP_ADDRESSMODE;}set wrapT(v){this.native.wrapV=B.Texture.WRAP_ADDRESSMODE;}
 set anisotropy(v){this.native.anisotropicFilteringLevel=v;}
 dispose(){this.native.dispose();}
}
export class TextureLoader{load(url){return new Texture(new B.Texture(url,world,false,false));}}
export class CanvasTexture extends Texture{constructor(canvas){const t=new B.DynamicTexture('canvas',canvas,world,true);t.hasAlpha=true;t.update(false);super(t);this.canvas=canvas;}}
function normalTexture(texture){
 if(texture.normal)return texture.normal;
 const c=texture.canvas,w=c.width,h=c.height,src=c.getContext('2d').getImageData(0,0,w,h).data,out=document.createElement('canvas');out.width=w;out.height=h;const ctx=out.getContext('2d'),pixels=ctx.createImageData(w,h);
 const height=(x,y)=>src[(((y+h)%h)*w+(x+w)%w)*4]/255;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){let nx=(height(x-1,y)-height(x+1,y))*1.5,ny=(height(x,y-1)-height(x,y+1))*1.5;const length=Math.hypot(nx,ny,1),i=(y*w+x)*4;pixels.data[i]=(nx/length*.5+.5)*255;pixels.data[i+1]=(ny/length*.5+.5)*255;pixels.data[i+2]=(1/length*.5+.5)*255;pixels.data[i+3]=255;}
 ctx.putImageData(pixels,0,0);const n=new B.DynamicTexture('surface-normal',out,world,true);n.gammaSpace=false;n.update(false);texture.normal=n;return n;
}
export class MeshStandardMaterial {
 constructor(options={}){this.native=new B.PBRMaterial('surface',world);this.userData={};this.color=new Color(options.color??0xffffff);this.color.changed=()=>{this.native.albedoColor=this.color.native.toLinearSpace();};this.color.changed();this.native.metallic=options.metalness??0;this.native.roughness=options.roughness??.85;this.map=options.map;if(options.bumpMap?.canvas)this.native.bumpTexture=normalTexture(options.bumpMap);this.depthTest=options.depthTest!==false;this.depthWrite=options.depthWrite!==false;this.opacity=options.opacity??1;this.transparent=options.transparent||false;this.visible=options.visible!==false;this.native.backFaceCulling=options.side!==DoubleSide;}
 get map(){return this._map;}set map(t){this._map=t;this.native.albedoTexture=t?.native||null;}
 set opacity(v){this.native.alpha=v;}get opacity(){return this.native.alpha;}
 set transparent(v){this.native.transparencyMode=v?B.PBRMaterial.PBRMATERIAL_ALPHABLEND:B.PBRMaterial.PBRMATERIAL_OPAQUE;}
 set depthTest(v){this._depthTest=v;this.native.depthFunction=v?B.Constants.LEQUAL:B.Constants.ALWAYS;}get depthTest(){return this._depthTest;}
 set depthWrite(v){this.native.disableDepthWrite=!v;}get depthWrite(){return !this.native.disableDepthWrite;}
 dispose(){this.native.dispose(false,false);}
}
export class MeshBasicMaterial extends MeshStandardMaterial{constructor(o={}){super(o);this.native.unlit=true;}}
export class SpriteMaterial extends MeshBasicMaterial{constructor(o={}){super({...o,transparent:true,side:DoubleSide});this.native.useAlphaFromAlbedoTexture=true;if(this.map){this.map.native.uScale=-1;this.map.native.uOffset=1;}}}
export class LineDashedMaterial extends MeshBasicMaterial{constructor(o={}){super(o);this.dashSize=o.dashSize;this.gapSize=o.gapSize;}}
function makeGeometry(g){if(g.kind==='ring'){const {inner,outer,segments}=g.options,positions=[],indices=[],normals=[],uvs=[];for(let i=0;i<=segments;i++){const a=i/segments*Math.PI*2;for(const r of [inner,outer]){positions.push(Math.cos(a)*r,Math.sin(a)*r,0);normals.push(0,0,1);uvs.push((Math.cos(a)+1)/2,(Math.sin(a)+1)/2);}if(i<segments){const k=i*2;indices.push(k,k+1,k+2,k+1,k+3,k+2);}}const m=new B.Mesh('ring',world),data=new B.VertexData();Object.assign(data,{positions,indices,normals,uvs});data.applyToMesh(m);return m;}return B.MeshBuilder['Create'+g.kind](g.kind,g.options,world);}
export class Mesh extends Group {
 constructor(geometry,material){super(makeGeometry(geometry));this.geometry=geometry;this.isMesh=true;this.material=material;this.native.isPickable=true;}
 set material(m){this._material=m;this.native.material=m.native;if(m.visible===false){this.native.visibility=0;this.native.alwaysSelectAsActiveMesh=false;}}
 get material(){return this._material;}
 set castShadow(v){if(v)shadows?.addShadowCaster(this.native,false);else shadows?.removeShadowCaster(this.native,false);}
 set receiveShadow(v){this.native.receiveShadows=v;}
}
export class Sprite extends Mesh{constructor(mat){super(new PlaneGeometry(1,1),mat);this.native.billboardMode=B.Mesh.BILLBOARDMODE_ALL;this.native.isPickable=false;}}
export class Line extends Group{constructor(geometry,material){super(B.MeshBuilder.CreateDashedLines('path',{points:geometry.options.points,dashSize:material.dashSize||.2,gapSize:material.gapSize||.1,dashNb:100},world));this.native.color=material.color.native;this.native.isPickable=false;this.geometry=geometry;this.material=material;}computeLineDistances(){}}
export class GridHelper extends Group{constructor(n,divisions,color){const lines=[];for(let i=0;i<=divisions;i++){const p=-n/2+i*n/divisions;lines.push([new B.Vector3(p,0,-n/2),new B.Vector3(p,0,n/2)],[new B.Vector3(-n/2,0,p),new B.Vector3(n/2,0,p)]);}super(B.MeshBuilder.CreateLineSystem('grid',{lines},world));this.native.color=new Color(color).native.scale(.22);this.native.isPickable=false;this.material={set transparent(v){},set opacity(v){},dispose(){}};this.native.alpha=.16;}}
export class PerspectiveCamera {
 constructor(fov,aspect,near,far){this.native=new B.FreeCamera('tactical-camera',new B.Vector3(),world);this._position=Vector3.link(this.native.position);this.native.fov=fov*Math.PI/180;this.native.minZ=near;this.native.maxZ=far;this.native.inputs.clear();}
 get position(){return this._position;}get matrixWorld(){return {elements:this.native.getWorldMatrix().asArray()};}
 updateMatrixWorld(){this.native.getViewMatrix(true);}
 updateProjectionMatrix(){this.native.getProjectionMatrix(true);}
}
export class Raycaster {
 setFromCamera(pointer,camera){const e=world.getEngine();this.ray=world.createPickingRay((pointer.x+1)*e.getRenderWidth()/2,(1-pointer.y)*e.getRenderHeight()/2,B.Matrix.Identity(),camera.native,false);}
 intersectObjects(objects,recursive){const allowed=new Set();for(const o of objects){allowed.add(o);if(recursive)o.traverse(n=>allowed.add(n));}
 const owner=m=>{for(let n=m;n;n=n.parent){if(n.metadata?.pickOwner)return n.metadata.pickOwner;if(n.metadata?.owner&&allowed.has(n.metadata.owner))return n.metadata.owner;}return null;};
 return (world.multiPickWithRay(this.ray,m=>{const o=owner(m);return !!o&&m.isEnabled()&&m.isPickable&&!o.userData.health;})||[]).map(h=>({object:owner(h.pickedMesh),point:h.pickedPoint,distance:h.distance})).sort((a,b)=>a.distance-b.distance);
 }
}
export class OrbitControls {
 constructor(camera,canvas){this.camera=camera;this.canvas=canvas;this.target=new Vector3();this.minDistance=2;this.maxDistance=220;this.maxPolarAngle=Math.PI*.46;this.listeners=[];this.last='';let drag;
 canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,button:e.button};canvas.setPointerCapture(e.pointerId);});
 canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
 canvas.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;const offset=camera.position.clone().sub(this.target),r=offset.length(),yaw=Math.atan2(offset.x,offset.z),pitch=Math.acos(offset.y/r);
 if(drag.button===2){const y=yaw-dx*.006,p=Math.max(.12,Math.min(this.maxPolarAngle,pitch+dy*.006));camera.position.set(this.target.x+r*Math.sin(p)*Math.sin(y),this.target.y+r*Math.cos(p),this.target.z+r*Math.sin(p)*Math.cos(y));}
 else if(drag.button===1)this.zoom(dy*.012);
 else{const scale=r*.0016,delta=new Vector3(-Math.cos(yaw)*dx+Math.sin(yaw)*dy,0,Math.sin(yaw)*dx+Math.cos(yaw)*dy).multiplyScalar(scale);camera.position.add(delta);this.target.add(delta);}this.update();});
 canvas.addEventListener('wheel',e=>{e.preventDefault();this.zoom(e.deltaY*.001);this.update();},{passive:false});}
 zoom(amount){const delta=this.camera.position.clone().sub(this.target),r=Math.max(this.minDistance,Math.min(this.maxDistance,delta.length()*Math.exp(amount)));delta.normalize().multiplyScalar(r);this.camera.position.copy(this.target).add(delta);}
 addEventListener(type,fn){if(type==='change')this.listeners.push(fn);}
 update(){this.camera.native.setTarget(this.target);const key=[...this.target.toArray(),...this.camera.position.toArray()].join(',');if(key!==this.last){this.last=key;this.listeners.forEach(fn=>fn());}}
}
