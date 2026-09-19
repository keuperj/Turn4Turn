"""Import CC0 farm models. Usage: .venv/bin/python tools/import_farm.py /tmp/farm-sources
Downloads original archives if absent; bakes static poses and embeds textures in GLBs.
Requires Playwright and Chromium, like the other asset import tools.
"""
import sys,zipfile,json,hashlib,base64,threading
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1];src=Path(sys.argv[1]);dest=root/'static/scenarios/farm/models'
src.mkdir(parents=True,exist_ok=True)
from urllib.request import urlopen
for file,url in [('cars.zip','https://kenney.nl/media/pages/assets/car-kit/1a312ec241-1775131960/kenney_car-kit.zip'),('animals.zip','https://opengameart.org/sites/default/files/Farm%20Animals%20by%20%40Quaternius.zip')]:
 if not (src/file).exists():
  with urlopen(url,timeout=60) as response:(src/file).write_bytes(response.read())
cars=zipfile.ZipFile(src/'cars.zip');animals=zipfile.ZipFile(src/'animals.zip')
(src/'colormap.png').write_bytes(cars.read('Models/GLB format/Textures/colormap.png'))
for name in ['tractor','tractor-shovel']:(src/(name+'.glb')).write_bytes(cars.read('Models/GLB format/'+name+'.glb'))
for name in ['Cow','Sheep','Pig']:(src/(name+'.fbx')).write_bytes(animals.read('Farm Animals by @Quaternius/FBX/'+name+'.fbx'))
(dest/'LICENSE-farm-vehicles.txt').write_bytes(cars.read('License.txt'))
(dest/'LICENSE-farm-animals.txt').write_bytes(animals.read('Farm Animals by @Quaternius/License.txt'))
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/':
   self.send_response(200);self.end_headers();self.wfile.write(b'<script type="importmap">{"imports":{"three":"/vendor/three.module.js"}}</script>')
  else:super().do_GET()
 def translate_path(self,path):
  if path.startswith('/source/'):return str(src/Path(path).name)
  return super().translate_path(path)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(root/'static')));threading.Thread(target=server.serve_forever,daemon=True).start()
manifest=json.loads((dest/'manifest.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}')
 for id,name,kind,w,d,h in [('FarmTractor','tractor','tractor',1.88,2.82,2),('FarmLoader','tractor-shovel','tractor',1.88,2.82,2),('FarmCow','Cow','cow',.94,1.88,1.4),('FarmSheep','Sheep','sheep',.94,.94,.8),('FarmPig','Pig','pig',.94,.94,.65)]:
  result=page.evaluate('''async ({name,w,d,h})=>{
   const T=await import('three'),{GLTFLoader}=await import('/comparison/vendor/loaders/GLTFLoader.js'),{FBXLoader}=await import('/comparison/vendor/loaders/FBXLoader.js'),{GLTFExporter}=await import('/comparison/vendor/exporters/GLTFExporter.js');
   const source=name.startsWith('tractor')?(await new GLTFLoader().loadAsync('/source/'+name+'.glb')).scene:await new FBXLoader().loadAsync('/source/'+name+'.fbx');
   source.updateMatrixWorld(true);
   // Bake a static rest pose: livestock are scenery, not animated combat actors.
   const group=new T.Group();source.traverse(o=>{if(!o.isMesh)return;const geometry=o.geometry.clone();if(o.isSkinnedMesh){const pos=geometry.attributes.position;for(let i=0;i<pos.count;i++){const v=new T.Vector3().fromBufferAttribute(pos,i);o.applyBoneTransform(i,v);pos.setXYZ(i,v.x,v.y,v.z);}geometry.deleteAttribute('skinIndex');geometry.deleteAttribute('skinWeight');}geometry.applyMatrix4(o.matrixWorld);geometry.computeVertexNormals();const mats=(Array.isArray(o.material)?o.material:[o.material]).map(m=>new T.MeshStandardMaterial({color:m.color,map:m.map,roughness:.9}));group.add(new T.Mesh(geometry,Array.isArray(o.material)?mats:mats[0]));});
   const bounds=new T.Box3().setFromObject(group),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3()),scale=Math.min(w/size.x,d/size.z,h/size.y);group.scale.setScalar(scale);group.position.set(-center.x*scale,-bounds.min.y*scale,-center.z*scale);const grounded=new T.Group();grounded.add(group);
   const data=await new GLTFExporter().parseAsync(grounded,{binary:true});return {dimensions:size.multiplyScalar(scale).toArray(),data:await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.readAsDataURL(new Blob([data]));})};
  }''',dict(name=name,w=w,d=d,h=h))
  data=base64.b64decode(result['data']);(dest/(id+'.glb')).write_bytes(data)
  entry=dict(id=id,kind=kind,pack='farmVehicles' if kind=='tractor' else 'farmAnimals',file=id+'.glb',dimensions=result['dimensions'],sha256=hashlib.sha256(data).hexdigest(),sourceSha256=hashlib.sha256((src/(name+('.glb' if kind=='tractor' else '.fbx'))).read_bytes()).hexdigest(),source='https://kenney.nl/assets/car-kit' if kind=='tractor' else 'https://opengameart.org/content/lowpoly-animated-farm-animal-pack',author='Kenney' if kind=='tractor' else 'Quaternius',license='CC0-1.0')
  manifest['models']=[e for e in manifest['models'] if e['id']!=id]+[entry];print(id,result['dimensions'],flush=True)
 browser.close()
manifest['packs'].update(farmVehicles='https://kenney.nl/assets/car-kit',farmAnimals='https://quaternius.com/packs/farmanimal.html')
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');server.shutdown()
