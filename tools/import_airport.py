"""Bundle selected CC0 airport GLBs, normalized to tactical prop footprints.

Usage: .venv/bin/python tools/import_airport.py /tmp/airport-sources
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
PACK='https://3dassets.dev/api/v1/packs/aircraft-fleet-and-airfield'
SELECTION=[('32563','AirportLightPlane','aircraft',9.4,9.4),
           ('32589','AirportBusinessJet','aircraft',9.4,9.4),
           ('32825','AirportFuelBowser','airport_fuel',1.88,2.82),
           ('32834','AirportTug','airport_tug',1.88,2.82),
           ('32839','AirportPowerCart','airport_cart',1.88,1.88),
           ('32827','AirportWindsock','windsock',1.88,1.88)]


def main():
    source=Path(sys.argv[1]);source.mkdir(parents=True,exist_ok=True)
    dest=ROOT/'static/assets/models/transport'
    pack=json.loads(subprocess.check_output(['curl','-fsSL','--max-time','60',PACK]))['data']
    entries={str(e['id']):e for e in pack['assets']}
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
                  const bounds=new T.Box3().setFromObject(source),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3()),scale=Math.min(w/size.x,d/size.z);
                  source.scale.multiplyScalar(scale);source.position.set(-center.x*scale,-bounds.min.y*scale,-center.z*scale);
                  const group=new T.Group();group.add(source);
                  const data=await new GLTFExporter().parseAsync(group,{binary:true});
                  return {dimensions:size.multiplyScalar(scale).toArray(),data:await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.readAsDataURL(new Blob([data]));})};
                }''',dict(name=name,w=w,d=d))
                data=base64.b64decode(result['data']);(dest/(name+'.glb')).write_bytes(data)
                entry=entries[asset_id]
                record=dict(id=name,kind=kind,pack='airport',file=name+'.glb',dimensions=result['dimensions'],sha256=hashlib.sha256(data).hexdigest(),sourceSha256=hashlib.sha256((source/(name+'.glb')).read_bytes()).hexdigest(),source=entry['url'],download=entry['cdnUrl'],author='3DAssets.dev',license='CC0-1.0',aiGenerated=entry['aiGenerated'])
                manifest['models']=[e for e in manifest['models'] if e['id']!=name]+[record]
                print(name,len(data),result['dimensions'],flush=True)
            browser.close()
        manifest['packs']['airport']='https://3dassets.dev/packs/aircraft-fleet-and-airfield'
        (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (dest/'LICENSE-airport.txt').write_text('Aircraft Fleet and Airfield — 3DAssets.dev\nhttps://3dassets.dev/packs/aircraft-fleet-and-airfield\n\nCC0 1.0 Universal\nhttps://creativecommons.org/publicdomain/zero/1.0/\n\nThe publisher dedicates these models to the public domain.\nFree to use, modify, and redistribute, including commercially; attribution is not required.\nThe publisher identifies these assets as AI-generated.\nSee manifest.json for individual source URLs and SHA-256 hashes.\n')
    finally:httpd.shutdown();httpd.server_close()


if __name__=='__main__':main()
