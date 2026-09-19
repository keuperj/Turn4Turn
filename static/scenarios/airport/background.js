import {surfaceBatch} from '../../surfaces.js';
import {runwayStrip} from './scene.js';
export function background(state){
  const n=state.size,extent=180;
  runwayStrip(this.view,this.root,state,-extent,-.5,'background-airport-north');
  runwayStrip(this.view,this.root,state,n-.5,n+extent,'background-airport-south');
  surfaceBatch(this.view,this.root,'background-airport-access-road',[
   {x:(-extent-.5)/2,z:state.scenery.access_y,w:extent-.5,d:3}
  ],this.view.material(state.scenery.road,'asphalt'),.012);
 }
