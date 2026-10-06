/** Shared harbour model placement and continuous dock geometry. */
import {B} from '../../rendering.js';
import {surfaceBatch} from '../../surfaces.js';

/** Instance bundled scenery with no gameplay picking or collision ownership. */
export function placeModel(view,parent,id,x,y,z,scale=1,angle=0,stretch=null){
 const source=view.transport.sources.get(id);if(!source)return null;
 const holder=new B.TransformNode('port-scenery:'+id,view.nativeScene);holder.parent=parent.native||parent;
 holder.position.set(x,y,z);holder.rotation.y=angle;
 holder.scaling.copyFrom(stretch?new B.Vector3(...stretch):new B.Vector3(scale,scale,scale));
 const instance=source.instantiateModelsToScene(name=>'port:'+id+':'+name,false,{doNotInstantiate:false});
 for(const root of instance.rootNodes){root.parent=holder;for(const mesh of [root,...root.getChildMeshes()]){mesh.isPickable=false;mesh.receiveShadows=true;mesh.metadata={scenery:true,asset:id};}}
 return holder;
}

/** Draw only the land slab, leaving the basin open to the background water. */
export function baseGround(view,state){
 const n=state.size,s=state.scenery.shore_y,c=(n-1)/2;
 view.box(view.terrain,n,.65,n-s,c,-.34,(s+n-1)/2,0x647b81);
 surfaceBatch(view,view.terrain,'port-quay',[{x:c,z:(s+n-1)/2,w:n,d:n-s}],view.material(0x96a4a4,'concrete'),.012);
}

/** Render piers, moored vessels, dock lighting and quay edge paint. */
export function ground(view,state){
 const {shore_y:s,piers,vessels}=state.scenery,n=state.size;
 const pontoons=view.transport.models.find(m=>m.id==='PortPontoon'),dims=pontoons?.dimensions||[7.71,.347,2.4];
 const dock=(x,z,w,d,alongZ)=>{
   // The ported GLB is stretched only in plan; the deck stays at ground level.
   const length=alongZ?d:w,width=alongZ?w:d,count=Math.ceil(length/8),part=length/count;
   for(let i=0;i<count;i++)placeModel(view,view.terrain,'PortPontoon',alongZ?x:x-length/2+part*(i+.5),-dims[1],alongZ?z-length/2+part*(i+.5):z,1,alongZ?Math.PI/2:0,[part/dims[0],1,width/dims[2]]);
   if(!view.transport.sources.has('PortPontoon'))surfaceBatch(view,view.terrain,'port-pier-fallback',[{x,z,w,d}],view.material(0x9d927a,'wood'),0);
 };
 dock((n-1)/2,2.5,n-4,2,false);
 for(const x of piers){
   dock(x,(s+3)/2,3,s-4,true);
   for(let y=4;y<s;y+=5){
     placeModel(view,view.terrain,'PortLamp',x+1.23,-.04,y,.7);
     view.box(view.terrain,.14,.9,.14,x+1.28,-.15,y,0x42535a);
   }
   placeModel(view,view.terrain,'PortLifebuoy',x+1.22,0,s-.4,.7);
 }
 for(const ship of vessels)placeModel(view,view.terrain,ship.model,ship.x,-.55,ship.y,ship.scale,ship.angle);
 const stripes=[];
 for(let x=0;x<n;x+=2)stripes.push({x,z:s-.32,w:.9,d:.16});
 surfaceBatch(view,view.terrain,'port-quay-safety-stripe',stripes,view.material(0xe4bc59),.026);
 const label=view.label('PORT / QUAYSIDE','#e7d29b',3);label.position.set(n-4,.06,s+.5);view.terrain.add(label);
}
