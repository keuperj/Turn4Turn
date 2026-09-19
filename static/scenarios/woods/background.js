const trees=['CommonTree_1','CommonTree_3','BirchTree_1','BirchTree_3'];
const shrubs=['Bush_1','BushBerries_1'];
export function background(state,rng){
  const n=state.size,c=(n-1)/2,trail=n>>1,extent=48;
  const path=this.material('woodland-trail','#9b8764','terrain-mixed-v2.webp',4);
  for(const z of [-10.5,n+9.5])this.plane('background-forest-path',trail,z,1,20,path,.018);
  let index=0;
  for(let x=-extent;x<n+extent;x+=3.8)for(let z=-extent;z<n+extent;z+=3.8){
   const px=x+(rng()-.5)*2,pz=z+(rng()-.5)*2;
   if(px>-5.5&&px<n+4.5&&pz>-5.5&&pz<n+4.5)continue;
   if(Math.abs(px-trail)<2.5&&pz>-21&&pz<n+20)continue;
   // Patchy density, with shrubs below tall birches and broadleaf canopies.
   if(rng()<.12)continue;
   const id=trees[index%trees.length];this.add(id,px,pz,.78+rng()*.42,rng()*Math.PI*2,0);
   if(index%2===0)this.add(shrubs[(index>>1)%shrubs.length],px+1,pz+1,.45+rng()*.3,rng()*Math.PI*2,0);
   index++;
  }
 }
