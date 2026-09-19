import {surfaceBatch,crossingPaint} from '../../surfaces.js';
/** All non-road terrain has a named surface; unknown tiles stay under fog. */
export function streetCrossing(view,state){
 const n=state.size,{road_x:rx,cross_y:cy}=state.scenery;
 const groups={sidewalk:[],lawn:[],garden:[],garden_path:[]},curbs=[],joints=[];
 for(let z=0;z<n;z++)for(let x=0;x<n;x++){
  const type=state.tiles[z][x];if(groups[type])groups[type].push({x,z,y:.022});
  if(type==='sidewalk'){
   if(x+1<n&&state.tiles[z][x+1]==='road')curbs.push({x:x+.47,z,w:.08,d:1});
   if(x>0&&state.tiles[z][x-1]==='road')curbs.push({x:x-.47,z,w:.08,d:1});
   if(z+1<n&&state.tiles[z+1][x]==='road')curbs.push({x,z:z+.47,w:1,d:.08});
   if(z>0&&state.tiles[z-1][x]==='road')curbs.push({x,z:z-.47,w:1,d:.08});
   joints.push({x,z,w:.96,d:.018});
  }
 }
 for(const [kind,points] of Object.entries(groups)){
  const material=kind==='lawn'?view.material(0x8fa573,'soil'):kind==='garden'?view.material(0x746449,'soil'):view.material(kind==='sidewalk'?0xc8c6b7:0xd2c2a3,'concrete');
  const mesh=view.tiles(view.terrain,points,material);if(mesh)mesh.native.name='streets-'+kind;
 }
 const known=r=>{const x=Math.round(r.x),y=Math.round(r.z);return x>=0&&y>=0&&x<n&&y<n&&state.tiles[y][x]==='road';};
 const paint=crossingPaint(rx,cy,-.5,n-.5);
 surfaceBatch(view,view.terrain,'streets-white-markings',paint.white.filter(known),view.material(0xeee9d7,'concrete'));
 surfaceBatch(view,view.terrain,'streets-center-lines',paint.yellow.filter(known),view.material(0xecd18c,'concrete'));
 surfaceBatch(view,view.terrain,'streets-curbs',curbs,view.material(0xddd7c7,'concrete'),.045);
 surfaceBatch(view,view.terrain,'streets-paver-joints',joints,view.material(0xa3a496,'concrete'),.027);
}
