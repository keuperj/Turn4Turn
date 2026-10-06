"""Bundle selected CC0 factory GLBs, normalized to tactical prop footprints.

Usage: .venv/bin/python tools/import_factory.py /tmp/factory-sources
Requires Playwright/Chromium. Downloads are only needed at import time.
"""
import base64
import hashlib
import json
import sys
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PACKS=['machine-shop-and-factory-hall','car-factory-production-line']
SELECTION=[('27724','FactoryLathe','factory_machine',2.82,1.88),
           ('27725','FactoryMill','factory_machine',2.82,1.88),
           ('27732','FactoryCNC','factory_machine',2.82,1.88),
           ('27740','FactoryCompressor','factory_machine',2.82,1.88),
           ('27757','FactoryRack','factory_rack',2.82,.94),
           ('27768','FactoryForklift','factory_forklift',1.88,2.82),
           ('27803','FactoryRobot','factory_robot',1.88,1.88),
           ('27808','FactoryConveyor','factory_conveyor',2.82,1.88)]



def main():
    source=Path(sys.argv[1]);source.mkdir(parents=True,exist_ok=True)
    dest=ROOT/'static/scenarios/factory/models'
    entries={}
    for slug in PACKS:
        pack=json.loads(subprocess.check_output(['curl','-fsSL','--max-time','60','https://3dassets.dev/api/v1/packs/'+slug]))['data']
        entries.update({str(e['id']):e for e in pack['assets']})
    for asset_id,name,*_ in SELECTION:
        entry=entries[asset_id]
        if entry['license']['slug']!='cc0-1.0':raise ValueError('Expected CC0 asset')
        path=source/(name+'.glb')
        if not path.exists():
            subprocess.run(['curl','-fsSL','--max-time','60',entry['cdnUrl'],'-o',str(path)],check=True)
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/':
                self.send_response(200);self.end_headers()
                self.wfile.write(b'<script type="importmap">{"imports":{"three":"/vendor/three.module.js"}}</script>')
            else:super().do_GET()
        def translate_path(self,path):
            if path.startswith('/source/'):return str(source/Path(path).name)
            return super().translate_path(path)
        def log_message(self,*_args):pass
    httpd=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'static')))
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    manifest=json.loads((dest/'manifest.json').read_text())
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.goto(f'http://127.0.0.1:{httpd.server_port}')
            for asset_id,name,kind,w,d in SELECTION:
                result=page.evaluate('''async ({name,w,d})=>{
                  const T=await import('three'),{GLTFLoader}=await import('/comparison/vendor/loaders/GLTFLoader.js'),{GLTFExporter}=await import('/comparison/vendor/exporters/GLTFExporter.js');
                  const source=(await new GLTFLoader().loadAsync('/source/'+name+'.glb')).scene;
                  const bounds=new T.Box3().setFromObject(source),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3()),scale=Math.min(w/size.x,d/size.z,2.5/size.y);
                  source.scale.multiplyScalar(scale);source.position.set(-center.x*scale,-bounds.min.y*scale,-center.z*scale);
                  const group=new T.Group();group.add(source);
                  const data=await new GLTFExporter().parseAsync(group,{binary:true});
                  return {dimensions:size.multiplyScalar(scale).toArray(),data:await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.readAsDataURL(new Blob([data]));})};
                }''',dict(name=name,w=w,d=d))
                data=base64.b64decode(result['data']);(dest/(name+'.glb')).write_bytes(data)
                entry=entries[asset_id]
                record=dict(id=name,kind=kind,pack='factory',file=name+'.glb',dimensions=result['dimensions'],sha256=hashlib.sha256(data).hexdigest(),sourceSha256=hashlib.sha256((source/(name+'.glb')).read_bytes()).hexdigest(),source=entry['url'],download=entry['cdnUrl'],author='3DAssets.dev',license='CC0-1.0',aiGenerated=entry['aiGenerated'])
                manifest['models']=[e for e in manifest['models'] if e['id']!=name]+[record]
                print(name,len(data),result['dimensions'],flush=True)
            browser.close()
        manifest['packs']['factory']=['https://3dassets.dev/packs/'+slug for slug in PACKS]
        (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (dest/'LICENSE-factory.txt').write_text('Machine Shop and Factory Hall / Car Factory Production Line — 3DAssets.dev\nhttps://3dassets.dev/packs/machine-shop-and-factory-hall\nhttps://3dassets.dev/packs/car-factory-production-line\n\nCC0 1.0 Universal\nhttps://creativecommons.org/publicdomain/zero/1.0/\n\nThe publisher dedicates these models to the public domain.\nFree to use, modify, and redistribute, including commercially; attribution is not required.\nThe publisher identifies these assets as AI-generated.\nSee manifest.json for individual source URLs and SHA-256 hashes.\n')
    finally:httpd.shutdown();httpd.server_close()


if __name__=='__main__':main()
