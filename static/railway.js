/** Shared double-track geometry for the station and its city surroundings. */
import {surfaceBatch} from './street-crossing.js';
export function railTracks(view,parent,tracks,start,end,prefix='railway'){
 const ballast=[],sleepers=[],rails=[];
 for(const x of tracks){
  ballast.push({x,z:(start+end)/2,w:3,d:end-start});
  for(let z=start+.25;z<end;z+=.65)sleepers.push({x,z,w:2.65,d:.20});
  for(const side of [-1,1])rails.push({x:x+side*.8,z:(start+end)/2,w:.095,d:end-start});
 }
 surfaceBatch(view,parent,prefix+'-ballast',ballast,view.material(0x77766f,'soil'),.013);
 surfaceBatch(view,parent,prefix+'-sleepers',sleepers,view.material(0x665644,'wood'),.045);
 surfaceBatch(view,parent,prefix+'-rails',rails,view.material(0xa9b0ad,'metal'),.08);
}
export function railwayGround(view,state){
 const n=state.size,tracks=state.scenery.tracks||[state.scenery.road_x,state.scenery.road_x+4],c=tracks[0];
 for(const [type,color] of [['platform',0xb5b1a2],['sidewalk',0xbcb9aa],['plaza',0xa59d8a],['railway',0x77766f]]){
  const cells=[];for(let z=0;z<n;z++)for(let x=0;x<n;x++)if(state.tiles[z][x]===type)cells.push({x,z,w:1,d:1});
  surfaceBatch(view,view.terrain,'station-'+type,cells,view.material(color,'concrete'),.012);
 }
 railTracks(view,view.terrain,tracks,-.5,n-.5);
 const paint=[],crossings=[];
 for(const x of [c-1.65,c+5.65])for(let z=2;z<n-3;z++)paint.push({x,z,w:.14,d:.85});
 for(const z of [1,n-3])crossings.push({x:c+2,z,w:13,d:1});
 surfaceBatch(view,view.terrain,'station-platform-safety',paint,view.material(0xe3c866),.028);
 surfaceBatch(view,view.terrain,'station-track-crossings',crossings,view.material(0xb6aa8e,'wood'),.089);
 for(const [i,x] of [c-3,c+7].entries()){
  const sign=view.label('PLATFORM '+(i+1),'#dee5d7',2.7);sign.position.set(x,2.5,2.5);view.terrain.add(sign);
 }
}
