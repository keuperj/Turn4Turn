/** Shared opaque vehicle geometry used by the game and comparison. */
export function detailedCar(context,name,estate,position,yaw,texture){
 const {scene,root,box,cyl,mesh,mat,maps,rubber,chrome,glass,cream,steel,lamp,tail}=context,B=window.BABYLON;
  const car=new B.TransformNode(name,scene);car.parent=root;car.position.copyFromFloats(...position);car.rotation.y=yaw;
  const paint=mat(name+'-paint','#ffffff',estate?.42:.34,.35);paint.albedoTexture=texture;paint.bumpTexture=maps.normal;paint.clearCoat.isEnabled=true;paint.clearCoat.intensity=.65;paint.clearCoat.roughness=.25;
  const length=estate?4.2:3.35,width=estate?1.72:1.60,front=-length/2,rear=length/2;
  // An extruded profile produces sloping windscreens and different roof silhouettes.
  function profile(label,points,w,material){
   const positions=[],indices=[],uvs=[],normals=[];
   for(const side of [-1,1])for(const [z,y] of points){positions.push(side*w/2,y,z);uvs.push((z+length/2)/length,y/1.8);}
   // Match Babylon's built-in meshes: clockwise outside faces and outward normals.
   // Both end caps and the connecting panels must use the same convention.
   const n=points.length;
   for(let i=1;i<n-1;i++)indices.push(0,i,i+1,n,n+i+1,n+i);
   for(let i=0;i<n;i++){const j=(i+1)%n;indices.push(i,n+j,j,i,n+i,n+j);}
   B.VertexData.ComputeNormals(positions,indices,normals);
   const m=new B.Mesh(label,scene),data=new B.VertexData();
   Object.assign(data,{positions,indices,uvs,normals});data.applyToMesh(m);m.convertToFlatShadedMesh();
   return mesh(m,[0,0,0],material,car);
  }
  profile(name+'-body',[[front,.42],[front+.10,.83],[front+.7,.96],[rear-.35,.94],[rear,.75],[rear,.42]],width,paint);
  const cabinFront=estate?-.85:-.65,cabinRear=estate?1.65:1.15,roofFront=estate?-.42:-.22,roofRear=estate?1.32:.73;
  profile(name+'-cabin',[[cabinFront,.94],[roofFront,1.52],[roofRear,1.52],[cabinRear,.94]],width*.87,glass);
  box(name+'-roof',[width*.88,.065,roofRear-roofFront],[0,1.54,(roofRear+roofFront)/2],paint,car);
  for(const side of [-1,1]){
   for(const z of [roofFront,roofRear])box('window-pillar',[.055,.55,.055],[side*width*.44,1.24,z],paint,car);
   box('door-beltline',[.045,.055,cabinRear-cabinFront],[side*width*.45,.98,(cabinFront+cabinRear)/2],paint,car);
   box('door-pillar',[.065,.54,.075],[side*width*.45,1.23,.45],paint,car);
   for(const z of [0,.91]){box('door-seam',[.014,.39,.014],[side*(width/2+.003),.72,z],rubber,car);box('door-handle',[.026,.035,.17],[side*(width/2+.017),.86,z-.12],chrome,car);}
   box('car-mirror',[.18,.10,.17],[side*(width*.5+.06),1.08,cabinFront+.1],paint,car);
   for(const z of [front+.62,rear-.64]){
    const wheel=cyl('car-tire',.31,.20,[side*width*.49,.34,z],rubber,car);wheel.rotation.z=Math.PI/2;
    const hub=cyl('alloy-wheel',.205,.215,[side*width*.49,.34,z],chrome,car);hub.rotation.z=Math.PI/2;
    for(let k=0;k<8;k++){const a=k*Math.PI/4;const spoke=box('wheel-spoke',[.012,.30,.038],[side*(width*.49+.112),.34,z],rubber,car);spoke.rotation.x=a;}
   }
  }
  for(const z of [front-.02,rear+.02]){box('bumper',[width*.94,.12,.13],[0,.44,z],rubber,car);box('license-plate',[.37,.10,.025],[0,.62,z+(z<0?-.08:.08)],cream,car);}
  for(const side of [-1,1]){box('headlight',[.35,.16,.055],[side*.51,.77,front-.025],lamp,car);box('taillight',[.23,.20,.055],[side*.60,.76,rear+.025],tail,car);}
  for(let i=0;i<7;i++)box('grille-slat',[.52,.017,.02],[0,.62+i*.035,front-.05],rubber,car);
  if(estate)for(const side of [-1,1])box('estate-roof-rail',[.035,.08,1.8],[side*.64,1.62,.47],steel,car);
  return car;
 }
