"""Factory model elevation, open walls, cutaways, background and retained scenery."""
import argparse
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game import Game
from browser_background import QuietHandler
from playwright.sync_api import sync_playwright


def main(base,gpu):
    with sync_playwright() as p:
        flags=['--no-sandbox','--enable-unsafe-swiftshader']+(['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if gpu else ['--use-gl=angle','--use-angle=swiftshader'])
        browser=p.chromium.launch(headless=True,args=flags)
        page=browser.new_page(viewport={'width':1100,'height':800});page.set_default_timeout(120000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/factory-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><canvas style="width:1100px;height:800px"></canvas></body>'))
        page.goto(base+'/factory-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        page.evaluate('''async gpu=>{const {Battlefield}=await import('/scene.js');window.f=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await f.ready;f.engine.stopRenderLoop();}''',gpu)
        assert page.evaluate('f.renderer')==('webgpu' if gpu else 'webgl')
        assert page.evaluate('f.transport.failures.concat(f.background.failures)')==[]
        for size in (24,30,40):
            g=Game(41,'factory',size=size);state=g.state()
            state.update(buildings=g.buildings,props=g.props,walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
            seen=set()
            for mode in ('exterior','0','1','2'):
                result=page.evaluate('''({state,mode})=>{
                  f.setView(mode);f.sync(state,'s0',null,'move');const n=state.size;f.controls.target.set((n-1)/2,1,(n-1)/2);f.camera.position.set(n+9,n+18,n+9);f.controls.update();
                  const background=f.background.root,ground=f.terrainLayers.get('ground'),models=f.pickables.filter(p=>p.userData?.transport?.startsWith('Factory'));
                  const fits=models.every(owner=>{const prop=state.props.find(p=>p.id===owner.userData.structure),b=owner.native.getHierarchyBoundingVectors(true),span=b.max.subtract(b.min);return span.x<=prop.width*.94+.01&&span.z<=prop.depth*.94+.01&&Math.abs(b.min.y-prop.z*3)<.01&&f.surfaceVisible(prop.x,prop.y,prop.z);});
                  const allExpected=state.props.filter(p=>f.surfaceVisible(p.x,p.y,p.z)).length===models.length;
                  const meshes=f.nativeScene.meshes,wallNames=[...new Set(meshes.filter(m=>m.name.startsWith('factory-wall-')&&!['factory-wall-column','factory-wall-trim'].includes(m.name)).map(m=>m.name))];
                  const layers=[...f.terrainLayers].filter(([id])=>id!=='fog').map(([,layer])=>layer);
                  f.sync({...state,fog:{...state.fog,visible:state.fog.visible.slice(10)}},'s0',null,'move');
                  return {mode,fits,allExpected,models:models.map(p=>p.userData.transport),walls:wallNames,plain:background.getChildMeshes().length===1&&f.background.placements.length===0,
                    floors:meshes.filter(m=>m.name==='factory-floor').length,stairs:meshes.filter(m=>m.name==='factory-stair').length,
                    retained:background===f.background.root&&ground===f.terrainLayers.get('ground')&&layers.every(layer=>[...f.terrainLayers.values()].includes(layer))};
                }''',dict(state=state,mode=mode))
                assert all(result[k] for k in ('fits','allExpected','plain','retained')),result
                assert set(result['walls'])=={'factory-wall-north','factory-wall-west'},result
                assert result['stairs']>0,result
                assert result['floors']==(4 if mode=='0' else 7 if mode=='1' else 8),result
                seen.update(result['models'])
                page.wait_for_function('f.nativeScene.isReady()');page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
                if size==30 and not gpu and mode in ('exterior','0'):
                    page.screenshot(path=f'/tmp/factory-{mode}.jpg',type='jpeg',quality=85)
            assert seen=={'FactoryLathe','FactoryMill','FactoryCNC','FactoryCompressor','FactoryRack','FactoryForklift','FactoryRobot','FactoryConveyor'},seen
            print('PASS',size,'all three levels, eight models, two walls, plain background, retained fog updates',flush=True)
        assert not errors,errors
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
