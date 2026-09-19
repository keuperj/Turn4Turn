import {surfaceBatch} from '../../surfaces.js';
const trees=['CommonTree_1','CommonTree_3','BirchTree_1','BirchTree_3'];
const shrubs=['Bush_1','BushBerries_1'];
export function background(state,rng){
  const n=state.size,c=(n-1)/2,rx=state.scenery.road_x,edge=state.scenery.field_edge||Math.max(3,Math.floor(n/6)),extent=100;
  const road=this.view.material(state.scenery.road,'soil'),soil=this.view.material(0x79603f,'soil'),crop=this.view.material(0xa5a05c,'soil');
  const rows=[],fields=[],roads=[];
  for(const [start,end] of [[-extent,-.5],[n-.5,n+extent]])roads.push({x:rx,z:(start+end)/2,w:3,d:end-start});
  // Wide side fields reach the horizon; rows align at all four board edges.
  for(const [left,right] of [[-extent,edge-.5],[n-edge-.5,n+extent]]){
   const outside=left<0?[[-extent,-.5,-extent,n+extent],[-.5,right,-extent,-.5],[-.5,right,n-.5,n+extent]]:[[n-.5,n+extent,-extent,n+extent],[left,n-.5,-extent,-.5],[left,n-.5,n-.5,n+extent]];
   for(const [l,r,t,b] of outside){
    fields.push({x:(l+r)/2,z:(t+b)/2,w:r-l,d:b-t});
    for(let x=Math.ceil(l);x<r;x++)for(const off of [-.3,0,.3])rows.push({x:x+off,z:(t+b)/2,w:.12,d:b-t});
   }
  }
  surfaceBatch(this.view,this.root,'background-farm-fields',fields,soil,.014);
  surfaceBatch(this.view,this.root,'background-farm-crop-rows',rows,crop,.065);
  surfaceBatch(this.view,this.root,'background-farm-road',roads,road,.012);
  // A few distant farms punctuate the open landscape, connected to the lane.
  const paths=[];
  for(const z of [-30,n+34]){
   this.add('House2',rx-10,z,.8,Math.PI/2,0);this.add('BigBarn',rx+11,z+5,.9,-Math.PI/2,0);
   this.add('Silo',rx+17,z+5,.8,0,0);
   paths.push({x:rx-5,z,w:10,d:1.5},{x:rx+5,z:z+5,w:10,d:1.5});
   for(const side of [-1,1])this.add(trees[Math.floor(rng()*trees.length)],rx+side*7,z-7,.65+rng()*.15,0,0);
  }
  surfaceBatch(this.view,this.root,'background-farm-paths',paths,road,.018);
  // Mixed hedgerows frame the fields, with generous clearance from the board.
  for(const x of [-6,n+5])for(let z=-48;z<n+48;z+=3){
   const px=x+(rng()-.5)*1.2,pz=z+(rng()-.5)*1.2;
   this.add(shrubs[Math.floor(rng()*shrubs.length)],px,pz,.55+rng()*.25,rng()*Math.PI*2,0);
   if(Math.floor((z+48)/3)%3===0)this.add(trees[Math.floor(rng()*trees.length)],px-1,pz,.55+rng()*.25,rng()*Math.PI*2,0);
  }
  // Distant shelter belts break up the horizon; leave the central lane open.
  for(const z of [-52,n+55])for(let x=-45;x<n+45;x+=5){
   if(Math.abs(x-rx)<5)continue;
   this.add(trees[Math.floor(rng()*trees.length)],x,z+rng()*3,.65+rng()*.35,rng()*Math.PI*2,0);
   this.add(shrubs[Math.floor(rng()*shrubs.length)],x+1,z+2,.6,rng()*Math.PI*2,0);
  }
 }
