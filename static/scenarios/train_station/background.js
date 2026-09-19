import {railTracks} from './scene.js';
const trees=['CommonTree_1','CommonTree_3','BirchTree_1','BirchTree_3'];
const shrubs=['Bush_1','BushBerries_1'];
export function background(state,rng){
  const n=state.size,c=(n-1)/2,tracks=state.scenery.tracks||[state.scenery.road_x,state.scenery.road_x+4],middle=(tracks[0]+tracks[1])/2,extent=65;
  for(const [start,end] of [[-extent,-.5],[n-.5,n+extent]])railTracks(this.view,this.root,tracks,start,end,'background-railway');
  const road=this.material('rail-city-road','#50585b','concrete-weathered-v2.webp',14),paving=this.material('rail-city-paving','#aaa99c','concrete-weathered-v2.webp',14);
  // Parallel city streets leave the railway corridor clear all the way to the horizon.
  for(const x of [.5,n-1.5,-19,n+18]){
   for(const [start,end] of (x<0||x>n? [[-extent,n+extent]]:[[-extent,-.5],[n-.5,n+extent]])){
    this.plane('background-station-sidewalk',x,(start+end)/2,6,end-start,paving,.011);
    this.plane('background-station-street',x,(start+end)/2,2,end-start,road,.02);
   }
  }
  // Cross streets stop at the rail corridor, avoiding asphalt over the track bed.
  for(const z of [-18,n+17])for(const [left,right] of [[-extent,middle-6],[middle+6,n+extent]]){
   this.plane('background-station-sidewalk',(left+right)/2,z,right-left,7,paving,.011);
   this.plane('background-station-street',(left+right)/2,z,right-left,4,road,.02);
  }
  let i=0;
  for(let x=-48;x<n+48;x+=12)for(let z=-48;z<n+48;z+=12){
   const px=x+(rng()-.5)*2,pz=z+(rng()-.5)*2;
   if(px>-7&&px<n+6&&pz>-7&&pz<n+6)continue;
   if(Math.abs(px-middle)<10||[.5,n-1.5,-19,n+18].some(v=>Math.abs(px-v)<7)||[-18,n+17].some(v=>Math.abs(pz-v)<7))continue;
   const id=['Flat','Flat2','Shop','House2','House3'][i%5];this.add(id,px,pz,.70+rng()*.2,rng()<.5?0:Math.PI,0);
   if(i%3===0)this.add([...trees,...shrubs][Math.floor(i/3)%6],px+4,pz,.5,0,0);
   i++;
  }
 }
