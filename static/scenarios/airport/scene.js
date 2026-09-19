/** Continuous runway surfaces and batched airfield markings for both renderers. */
import {surfaceBatch} from '../../surfaces.js';

export function runwayStrip(view,parent,state,start,end,prefix='airport'){
 const x=state.scenery.runway_x,w=state.scenery.runway_width,white=[];
 surfaceBatch(view,parent,prefix+'-runway',[{x,z:(start+end)/2,w,d:end-start}],view.material(0x454c50,'asphalt'),.018);
 for(const side of [-1,1])white.push({x:x+side*(w/2-.22),z:(start+end)/2,w:.10,d:end-start});
 // Clip a single global dash pattern to each region so it crosses map edges cleanly.
 for(let z=Math.floor(start/6)*6;z<end;z+=6){
  const a=Math.max(start,z),b=Math.min(end,z+2.8);
  if(b>a)white.push({x,z:(a+b)/2,w:.16,d:b-a});
 }
 surfaceBatch(view,parent,prefix+'-runway-markings',white,view.material(0xeae8dc),.028);
 const lights=[];
 for(let z=Math.ceil(start/6)*6;z<end;z+=6)for(const side of [-1,1])lights.push({x:x+side*(w/2+.16),z,w:.13,d:.18});
 surfaceBatch(view,parent,prefix+'-runway-lights',lights,view.material(0xf9e9a5),.04);
}

export function airportGround(view,state){
 const n=state.size,apron=[],yellow=[],rx=state.scenery.runway_x,ax=state.scenery.apron_x;
 for(let z=0;z<n;z++)for(let x=0;x<n;x++)if(state.tiles[z][x]==='apron')apron.push({x,z,w:1,d:1});
 surfaceBatch(view,view.terrain,'airport-apron',apron,view.material(0x949b97,'concrete'),.015);
 runwayStrip(view,view.terrain,state,-.5,n-.5);
 // Taxiway centerline and hold-short paint connect apron to runway at each end.
 for(const z of [1,n-3]){
  yellow.push({x:(ax+rx)/2,z,w:rx-ax,d:.10});
  for(const dz of [-.18,.18])yellow.push({x:rx-state.scenery.runway_width/2-.6,z:z+dz,w:.10,d:1.3});
 }
 yellow.push({x:ax+.35,z:(n-1)/2,w:.10,d:n});
 surfaceBatch(view,view.terrain,'airport-taxi-paint',yellow,view.material(0xe7be4e),.03);
}
