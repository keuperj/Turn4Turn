"""Themed imported surroundings, fog, isolation, and stable resource counts."""
import argparse
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from world import THEMES
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    def log_message(self,*_args):pass

def main(base,gpu):
    with sync_playwright() as p:
        flags=['--no-sandbox','--enable-unsafe-swiftshader']+(['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if gpu else ['--use-gl=angle','--use-angle=swiftshader'])
        browser=p.chromium.launch(headless=True,args=flags)
        page=browser.new_page(viewport={'width':1200,'height':850});page.set_default_timeout(120000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/background-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><div style="width:1200px;height:850px"><canvas style="width:100%;height:100%"></canvas></div></body>'))
        page.goto(base+'/background-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        result=page.evaluate('''async gpu=>{
         const {Battlefield}=await import('/scene.js');window.field=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await field.ready;
         field.engine.stopRenderLoop();return {renderer:field.renderer,loaded:field.background.sources.size,failures:field.background.failures};
        }''',gpu)
        assert result==dict(renderer='webgpu' if gpu else 'webgl',loaded=19,failures=[]),result
        states=[]
        for theme in THEMES:
            g=Game(41,theme,size=24);state=g.state()
            state.update(buildings=g.buildings,props=[],walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),units=[],stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
            states.append(state)
        for run in range(2):
            counts=[]
            for state in states:
                result=page.evaluate('''state=>{
                 const f=field;f.sync(state,null,null,'move');f.controls.target.set(11.5,0,11.5);f.camera.position.set(48,42,52);f.controls.update();f.background.atmosphere();
                 const bg=f.background,root=bg.root,meshes=root.getChildMeshes(),decor=meshes.filter(m=>m.metadata?.asset);
                 const outside=decor.every(m=>{m.computeWorldMatrix(true);const b=m.getBoundingInfo().boundingBox;return b.maximumWorld.x<-.5||b.maximumWorld.z<-.5||b.minimumWorld.x>state.size-.5||b.minimumWorld.z>state.size-.5;});
                 const placements=JSON.stringify(bg.placements);f.sync({...state,round:state.round+1},null,null,'move');
                 f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame();
                 return {theme:state.theme,outside,isolated:meshes.every(m=>!m.isPickable&&!m.metadata?.pickOwner),stable:bg.root===root&&JSON.stringify(bg.placements)===placements,
                  variants:new Set(bg.placements.map(p=>p.id)).size,meshes:meshes.length,materials:f.nativeScene.materials.length,textures:f.nativeScene.textures.length,
                  floor:meshes.find(m=>m.name==='background-ground').material.albedoColor.asArray(),fog:[f.nativeScene.fogStart,f.nativeScene.fogEnd]};
                }''',state)
                assert result['outside'] and result['isolated'] and result['stable'],result
                assert result['variants']=={'urban':10,'factory':11,'train_station':11,'airport':11,'streets':9,'woods':6,'farm':12}[state['theme']],result
                assert 0<result['fog'][0]<result['fog'][1]<180,result
                page.wait_for_function('field.nativeScene.isReady()')
                page.evaluate('field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()')
                if run==0:
                    print(result,flush=True)
                    if not gpu:
                        page.screenshot(path=f"/tmp/background-{state['theme']}-webgl.png")
                counts.append((result['meshes'],result['materials'],result['textures']))
            if run==0:baseline=counts[-1]
            else:assert counts[-1]==baseline,(baseline,counts[-1])
        assert page.evaluate('''()=>{const bg=field.background;field.sync({...field.state,lighting:'night'},null,null,'move');return field.nativeScene.fogColor.r<.1&&bg.root===field.background.root;}''')
        assert page.evaluate('''()=>['House','House2','House3','Flat','Flat2','Shop'].every(id=>field.background.sources.get(id).materials.some(m=>m.albedoTexture))''')
        assert not errors,errors
        print('PASS background assets, all seven themes, outside-grid bounds, picking isolation, fog and stable cleanup',flush=True)
        browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
