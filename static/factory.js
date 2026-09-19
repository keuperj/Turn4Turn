/** Open factory platforms and two outer walls, shared by WebGL and WebGPU. */
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
  part('factory-floor',b.width,.14,b.depth,cx,height-.07,cy,concrete);
  const paint=[];
  // Yellow aisle boundaries make working lanes readable on every platform.
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
   // Guardrails only at exposed mezzanine edges, not between joined platforms.
   const exposed=(x,z)=>!state.buildings.some(other=>!other.destroyed&&x>=other.x&&x<other.x+other.width&&z>=other.y&&z<other.y+other.depth&&other.level>=level);
   for(let x=b.x;x<b.x+b.width;x++)if(exposed(x,b.y+b.depth)){
    for(const h of [.45,.95])part('factory-guardrail',1,.055,.055,x,height+h,b.y+b.depth-.5,yellow);
    if((x-b.x)%2===0)part('factory-rail-post',.065,1,.065,x,height+.5,b.y+b.depth-.5,steel);
   }
   for(let z=b.y;z<b.y+b.depth;z++)if(exposed(b.x+b.width,z)){
    for(const h of [.45,.95])part('factory-guardrail',.055,.055,1,b.x+b.width-.5,height+h,z,yellow);
    if((z-b.y)%2===0)part('factory-rail-post',.065,1,.065,b.x+b.width-.5,height+.5,z,steel);
   }
  }
 }
 for(const [a,d] of state.stairs){
  if(a[0]<b.x||a[0]>=b.x+b.width||a[1]<b.y||a[1]>=b.y+b.depth||a[2]>limit)continue;
  const link={transition:`stairs:${a.join(',')}:${d.join(',')}`,ends:[a,d],x:a[0],y:a[1],z:a[2]};
  for(let i=0;i<12;i++){
   const step=part('factory-stair',.85,(i+1)/4,.16,a[0],a[2]*3+(i+1)/8,a[1]-.9+i*.16,steel);step.userData={...link};
  }
  const sign=view.hoverLabel('STAIRS ↕',link.transition,'#f6d495',1);sign.position.set(a[0],a[2]*3+1,a[1]);parent.add(sign);
 }
 const label=view.label(b.name,'#f2da91',Math.min(4,b.width-1));label.position.set(cx,limit*3+.03,cy);label.rotation.x=-Math.PI/2;parent.add(label);
}
