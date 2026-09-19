/** Open factory platforms, stair wells and two outer walls for both renderers. */
import {surfaceBatch} from './street-crossing.js';

export function factoryBuilding(view,b,state){
 const parent=view.terrain,limit=view.buildingLevel(b),cx=b.x+(b.width-1)/2,cy=b.y+(b.depth-1)/2;
 if(b.destroyed){view.box(parent,b.width,.12,b.depth,cx,.06,cy,0x686c69);return;}
 const concrete=view.material(0xadb2ae,'concrete'),steel=view.material(0x60747b,'metal'),yellow=view.material(0xd1aa45),wall=view.material(0x8e9ea1,'metal');
 const part=(name,w,h,d,x,y,z,material)=>{
  const mesh=view.box(parent,w,h,d,x,y,z,material);mesh.native.name=name;mesh.userData.structure=b.id;view.pickables.push(mesh);return mesh;
 };
 for(let level=0;level<=limit;level++){
  const height=level*3;
  // Merge solid floor runs, leaving the stair wells open through each slab.
  const holes=new Set((b.floor_holes||[]).filter(p=>p[2]===level).map(p=>p[0]+','+p[1])),patches=[];
  for(let z=b.y;z<b.y+b.depth;z++){
   let x=b.x;
   while(x<b.x+b.width){
    if(holes.has(x+','+z)){x++;continue;}
    const start=x;while(x<b.x+b.width&&!holes.has(x+','+z))x++;
    const previous=patches.find(p=>p.x===start&&p.w===x-start&&p.z+p.d===z);
    if(previous)previous.d++;else patches.push({x:start,z,w:x-start,d:1});
   }
  }
  for(const p of patches){const floor=part('factory-floor',p.w,.14,p.d,p.x+(p.w-1)/2,height-.07,p.z+(p.d-1)/2,concrete);Object.assign(floor.native.metadata,{factoryFloor:b.id,level});}
  const paint=[];
  for(const side of [-1,1])paint.push({x:cx+side*(b.width/2-1),z:cy,w:.07,d:Math.max(1,b.depth-2)});
  surfaceBatch(view,parent,'factory-aisle-'+b.id+'-'+level,paint,yellow,height+.012);
  if(b.y===0){
   part('factory-wall-north',b.width,2.95,.16,cx,height+1.475,-.5,wall);
   part('factory-wall-trim',b.width,.22,.18,cx,height+.3,-.5,yellow);
   for(let x=b.x;x<b.x+b.width;x+=4)part('factory-wall-column',.18,3,.25,x,height+1.5,-.44,steel);
  }
  if(b.x===0){
   part('factory-wall-west',.16,2.95,b.depth,-.5,height+1.475,cy,wall);
   part('factory-wall-trim',.18,.22,b.depth,-.5,height+.3,cy,yellow);
   for(let z=b.y;z<b.y+b.depth;z+=4)part('factory-wall-column',.25,3,.18,-.44,height+1.5,z,steel);
  }
  if(level>0){
   const exposed=(x,z)=>!state.buildings.some(other=>!other.destroyed&&x>=other.x&&x<other.x+other.width&&z>=other.y&&z<other.y+other.depth&&other.level>=level);
   for(const side of [-1,1]){
    const edgeZ=side<0?b.y-.5:b.y+b.depth-.5,neighborZ=side<0?b.y-1:b.y+b.depth;
    for(let x=b.x;x<b.x+b.width;x++)if(neighborZ>=0&&exposed(x,neighborZ)){
     for(const h of [.45,.95])part('factory-guardrail',1,.055,.055,x,height+h,edgeZ,yellow);
     if((x-b.x)%2===0)part('factory-rail-post',.065,1,.065,x,height+.5,edgeZ,steel);
    }
    const edgeX=side<0?b.x-.5:b.x+b.width-.5,neighborX=side<0?b.x-1:b.x+b.width;
    for(let z=b.y;z<b.y+b.depth;z++)if(neighborX>=0&&exposed(neighborX,z)){
     for(const h of [.45,.95])part('factory-guardrail',.055,.055,1,edgeX,height+h,z,yellow);
     if((z-b.y)%2===0)part('factory-rail-post',.065,1,.065,edgeX,height+.5,z,steel);
    }
   }
   // Visible steel legs support the central stack and platform corners.
   for(const x of [b.x-.35,b.x+b.width-.65])for(const z of [b.y-.35,b.y+b.depth-.65])part('factory-platform-column',.16,3,.16,x,height-1.5,z,steel);
  }
 }
 for(const [a,d] of state.stairs){
  if(a[0]<b.x||a[0]>=b.x+b.width||a[1]<b.y||a[1]>=b.y+b.depth||a[2]>limit)continue;
  const link={transition:`stairs:${a.join(',')}:${d.join(',')}`,ends:[a,d],x:a[0],y:a[1],z:a[2]},dx=d[0]-a[0],dz=d[1]-a[1],alongX=dx!==0;
  for(let i=0;i<12;i++){
   const t=(i+.5)/12,x=a[0]+dx*t,z=a[1]+dz*t,y=a[2]*3+(i+1)/4;
   const step=part('factory-stair',alongX?.27:.9,.12,alongX?.9:.27,x,y-.06,z,steel);step.userData={...link};
   const nosing=part('factory-stair-nosing',alongX?.04:.9,.025,alongX?.9:.04,x,y+.015,z,yellow);nosing.userData={...link};
   if(i%3===0)for(const side of [-1,1]){const post=part('factory-stair-post',.04,.9,.04,x+(alongX?0:side*.46),y+.45,z+(alongX?side*.46:0),yellow);post.userData={...link};}
  }
  for(const side of [-1,1]){
   const rail=part('factory-stair-handrail',alongX?Math.sqrt(18):.05,.055,alongX?.05:Math.sqrt(18),(a[0]+d[0])/2+(alongX?0:side*.46),a[2]*3+2.4,(a[1]+d[1])/2+(alongX?side*.46:0),yellow);
   if(alongX)rail.rotation.z=Math.atan2(3,dx);else rail.rotation.x=-Math.atan2(3,dz);
   rail.userData={...link};
  }
  const sign=view.hoverLabel('STAIRS ↕',link.transition,'#f6d495',1);sign.position.set(a[0],a[2]*3+1,a[1]);parent.add(sign);
 }
 const label=view.label(b.name,'#f2da91',Math.min(4,b.width-1));label.position.set(cx,limit*3+.03,cy);label.rotation.x=-Math.PI/2;parent.add(label);
}
