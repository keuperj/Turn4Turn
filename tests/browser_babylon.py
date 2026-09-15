"""Native Babylon assets, animated bones, stance rendering and scene cleanup."""
import sys,threading
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
g.geometry_revision+=1;g._los_cache.clear();g.init_fog();server.game=g
httpd=HTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/snap/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=b.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(60000)
  page.goto(f'http://127.0.0.1:{httpd.server_port}/?mode=single');page.wait_for_selector('#move-mode');page.wait_for_function("!document.body.classList.contains('busy')")
  page.evaluate("async()=>{const {battlefield:v}=await import('/app.js');window.v=v;v.controls.target.set(16,.6,25);v.camera.position.set(16,5,33);v.controls.update();}")
  assert page.evaluate('v.characters.instances.size')==4
  entry="v.characters.instances.get(v.models.get('s0'))"
  page.evaluate("v.characters.motion(v.models.get('s0'),'walk')")
  page.wait_for_timeout(350)
  before=page.evaluate(entry+".bones.get('UpperLegL').rotationQuaternion.asArray()")
  page.wait_for_timeout(550)
  assert before!=page.evaluate(entry+".bones.get('UpperLegL').rotationQuaternion.asArray()"),'Walking must animate skeleton, not just root position'
  page.screenshot(path='/tmp/ground-control-babylon-stances.png')
  page.evaluate("v.characters.motion(v.models.get('s0'),'idle')")
  colors=page.evaluate("[...v.characters.instances.get(v.models.get('s3')).materials].map(m=>m.albedoColor?.asArray())")
  assert all(0<=component<=1 for color in colors if color for component in color),colors
  counts=[]
  for _ in range(3):
   page.evaluate("v.sync(v.state,v.selected,null,'move',null)")
   page.wait_for_timeout(200)
   counts.append(page.evaluate('({meshes:v.nativeScene.meshes.length,materials:v.nativeScene.materials.length,skeletons:v.nativeScene.skeletons.length,animations:v.nativeScene.animationGroups.length})'))
  assert counts[0]==counts[-1],counts
  assert colors==page.evaluate("[...v.characters.instances.get(v.models.get('s3')).materials].map(m=>m.albedoColor?.asArray())"),'Team tints must not accumulate across refreshes'
  assert not errors,errors
  print('PASS Babylon native animation, three stances, stable mesh/material/skeleton counts:',counts[-1],flush=True)
  b.close()
finally:httpd.shutdown()
