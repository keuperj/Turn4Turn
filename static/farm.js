/** Batched soil, crop rows and connecting farmyard paths for both renderers. */
import {surfaceBatch} from './street-crossing.js';
export function farmGround(view,state){
 const soil=[],rows=[],paths=[];
 for(let z=0;z<state.size;z++)for(let x=0;x<state.size;x++){
  const type=state.tiles[z][x];
  if(type==='farm_path')paths.push({x,z,w:1,d:1});
  if(type!=='crops')continue;
  soil.push({x,z,w:1,d:1});
  for(const off of [-.3,0,.3])rows.push({x:x+off,z,w:.12,d:1});
 }
 surfaceBatch(view,view.terrain,'farm-soil',soil,view.material(0x79603f,'soil'),.014);
 surfaceBatch(view,view.terrain,'farm-crop-rows',rows,view.material(0xa5a05c,'soil'),.065);
 surfaceBatch(view,view.terrain,'farm-paths',paths,view.material(state.scenery.road,'soil'),.018);
}
