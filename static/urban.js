/** Pavements and road markings follow authoritative tiles, including explored fog. */
export function urbanStreets(view,state){
 const n=state.size,{road_x:rx,cross_y:cy}=state.scenery;
 const surfaces={sidewalk:[],plaza:[],park:[],park_path:[]};
 for(let z=0;z<n;z++)for(let x=0;x<n;x++)if(surfaces[state.tiles[z][x]])surfaces[state.tiles[z][x]].push({x,y:.023,z});
 const colors={sidewalk:0xc6c4b5,plaza:0xb6aa95,park:0x6e894e,park_path:0xd3c19b};
 for(const [kind,points] of Object.entries(surfaces)){
  const mesh=view.tiles(view.terrain,points,view.material(colors[kind],kind==='park'?'soil':'concrete'));
  if(mesh)mesh.native.name='urban-'+kind;
 }
 const part=(name,w,d,x,z,color,y=.034)=>{
  const tx=Math.round(x),tz=Math.round(z);if(tx<0||tz<0||tx>=n||tz>=n||state.tiles[tz][tx]==='unknown')return;
  const m=view.box(view.terrain,w,.014,d,x,y,z,view.material(color,'concrete'));m.native.name=name;m.native.isPickable=false;return m;
 };
 // Curbs border every road-facing sidewalk; the intersection has dropped crossings.
 for(let i=0;i<n;i++)for(const side of [-1,1]){
  if(Math.abs(i-cy)>2)part('urban-curb',.12,1,rx+side*2.53,i,0xe2dccb);
  if(Math.abs(i-rx)>2)part('urban-curb',1,.12,i,cy+side*2.53,0xe2dccb);
  if(i%3===0&&Math.abs(i-cy)>4)part('urban-lane-mark',.10,1.4,rx,i,0xe8d195);
  if(i%3===0&&Math.abs(i-rx)>4)part('urban-lane-mark',1.4,.10,i,cy,0xe8d195);
 }
 for(const side of [-1,1])for(let stripe=-2;stripe<=2;stripe++){
  part('urban-crosswalk',.52,1.05,rx+stripe*.85,cy+side*3.45,0xeee9d8);
  part('urban-crosswalk',1.05,.52,rx+side*3.45,cy+stripe*.85,0xeee9d8);
 }
 // Paver joints distinguish walking areas from asphalt and the single green space.
 for(const kind of ['sidewalk','plaza','park_path'])for(const p of surfaces[kind]){
  if((p.x+p.z)%2===0)part('urban-paver-joint',.96,.018,p.x,p.z,kind==='park_path'?0xb5a47f:0x98978b,.032);
 }
}
