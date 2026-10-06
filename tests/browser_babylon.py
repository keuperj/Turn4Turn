"""Native Babylon assets, animated bones, stance rendering and scene cleanup."""
import sys,threading,copy
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from playwright.sync_api import sync_playwright
class QuietHandler(server.Handler):
    """Group automated checks for quiethandler behavior."""
    def log_message(self,*args):
        """Suppress HTTP access logging during tests."""
        pass
g=Game(41,'urban');g.buildings=[];g.props=[];g.walls={};g.portals=[];g.ladders=[];g.stairs=[];g.blocked=set();g.surfaces={(x,y,0) for x in range(g.size) for y in range(g.size)};g.tiles=[['grass']*g.size for _ in range(g.size)];g.heights=[[0]*g.size for _ in range(g.size)]
g.units=g.alive('soldier')
for i,u in enumerate(g.units):u.update(x=13+i*2,y=25,z=0,stance=['standing','kneeling','prone','standing'][i])
g.units[-1]['team']='civilian'
for i in range(7):
    unit=copy.deepcopy(g.units[0]);unit.update(id=f'appearance{i}',team='alien' if i==0 else 'civilian',x=11+i*2,y=22,stance='standing');g.units.append(unit)
g.geometry_revision+=1;g._los_cache.clear();g.init_fog();server.game=g
httpd=HTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  gpu='--webgpu' in sys.argv
  args=['--no-sandbox','--enable-unsafe-swiftshader']+(['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if gpu else ['--use-gl=angle','--use-angle=swiftshader'])
  b=p.chromium.launch(headless=True,args=args)
  page=b.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(60000)
  page.route('**/character-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><canvas style="width:1440px;height:1050px"></canvas></body>'))
  page.goto(f'http://127.0.0.1:{httpd.server_port}/character-test')
  page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
  page.evaluate("async gpu=>{const {Battlefield}=await import('/scene.js');window.v=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await v.ready;}",gpu)
  state=g.state();state['units']=g.units;state['fog']={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)}
  page.evaluate("state=>{v.sync(state,'s0',null,'move');v.controls.target.set(16,.6,23);v.camera.position.set(16,6,32);v.controls.update();}",state)
  assert page.evaluate('v.renderer')==('webgpu' if gpu else 'webgl')
  assert page.evaluate('v.characters.instances.size')==11
  entry="v.characters.instances.get(v.models.get('s0'))"
  page.evaluate("v.characters.motion(v.models.get('s0'),'walk')")
  page.wait_for_timeout(350)
  before=page.evaluate(entry+".bones.get('UpperLegL').rotationQuaternion.asArray()")
  page.wait_for_timeout(550)
  assert before!=page.evaluate(entry+".bones.get('UpperLegL').rotationQuaternion.asArray()"),'Walking must animate skeleton, not just root position'
  page.screenshot(path=f"/tmp/characters-{'webgpu' if gpu else 'webgl'}.png")
  page.evaluate("v.characters.motion(v.models.get('s0'),'idle')")
  colors=page.evaluate("[...v.characters.instances.get(v.models.get('s3')).materials].map(m=>m.albedoColor?.asArray())")
  assert all(0<=component<=1 for color in colors if color for component in color),colors
  appearances=page.evaluate('''()=>[...v.characters.instances.values()].map(e=>({team:e.unit.team,variant:e.variant,weapon:e.weapon.visible,clips:e.instance.animationGroups.length,hand:!!e.hand,camo:[...e.materials].filter(m=>m.albedoTexture?.url?.endsWith('/camouflage.png')).length}))''')
  assert all(e['variant']=='Ninja_Male' for e in appearances if e['team']=='alien'),appearances
  assert len({e['variant'] for e in appearances if e['team']=='civilian'})>=3,appearances
  assert all(not e['weapon'] and not e['camo'] for e in appearances if e['team']=='civilian'),appearances
  assert all(e['camo']>=1 for e in appearances if e['team']=='soldier'),appearances
  assert all(e['clips'] and e['hand'] for e in appearances),appearances
  assert page.evaluate('''()=>[...v.characters.sources.values()].every(s=>s.container.animationGroups.some(g=>g.name.endsWith('|Walk_Carry')))&&v.characters.sources.get('soldier').container.meshes.filter(m=>m.material?.albedoTexture).every(m=>m.isVerticesDataPresent(BABYLON.VertexBuffer.UVKind))''')
  counts=[]
  for _ in range(3):
   page.evaluate("v.sync(v.state,v.selected,null,'move',null)")
   page.wait_for_timeout(200)
   counts.append(page.evaluate('({meshes:v.nativeScene.meshes.length,materials:v.nativeScene.materials.length,skeletons:v.nativeScene.skeletons.length,animations:v.nativeScene.animationGroups.length})'))
  assert counts[0]==counts[-1],counts
  assert colors==page.evaluate("[...v.characters.instances.get(v.models.get('s3')).materials].map(m=>m.albedoColor?.asArray())"),'Team tints must not accumulate across refreshes'
  assert appearances==page.evaluate('''()=>[...v.characters.instances.values()].map(e=>({team:e.unit.team,variant:e.variant,weapon:e.weapon.visible,clips:e.instance.animationGroups.length,hand:!!e.hand,camo:[...e.materials].filter(m=>m.albedoTexture?.url?.endsWith('/camouflage.png')).length}))''')
  assert not errors,errors
  print('PASS Babylon native animation, three stances, stable mesh/material/skeleton counts:',counts[-1],flush=True)
  b.close()
finally:httpd.shutdown()
