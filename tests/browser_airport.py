"""Airport layout, models and continuous runway and retained scenery during fog updates."""
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
        page=browser.new_page(viewport={'width':1000,'height':750});page.set_default_timeout(120000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/airport-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><div style="width:1000px;height:750px"><canvas style="width:100%;height:100%"></canvas></div></body>'))
        page.goto(base+'/airport-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        page.evaluate('''async gpu=>{const {Battlefield}=await import('/scene.js');window.f=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await f.ready;f.engine.stopRenderLoop();}''',gpu)
        assert page.evaluate('f.transport.failures.concat(f.background.failures)')==[]
        assert page.evaluate('f.renderer')==('webgpu' if gpu else 'webgl')
        for size in (24,30,40):
            g=Game(41,'airport',size=size);state=g.state()
            state.update(buildings=g.buildings,props=g.props,walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
            result=page.evaluate('''state=>{
              f.setView('exterior');f.sync(state,'s0',null,'move');const n=state.size;f.controls.target.set((n-1)/2,0,(n-1)/2);f.camera.position.set(n+9,n+18,n+9);f.controls.update();f.background.atmosphere();
              const background=f.background.root,ground=f.terrainLayers.get('ground'),meshes=background.getChildMeshes();
              const bounds=name=>{const mesh=f.nativeScene.getMeshByName(name);mesh.computeWorldMatrix(true);return mesh.getBoundingInfo().boundingBox;};
              const main=bounds('airport-runway'),north=bounds('background-airport-north-runway'),south=bounds('background-airport-south-runway');
              const continuous=Math.abs(main.minimumWorld.z-north.maximumWorld.z)<.001&&Math.abs(main.maximumWorld.z-south.minimumWorld.z)<.001&&
                [north,south].every(b=>Math.abs(b.minimumWorld.x-main.minimumWorld.x)<.001&&Math.abs(b.maximumWorld.x-main.maximumWorld.x)<.001&&Math.abs(b.minimumWorld.y-main.minimumWorld.y)<.001);
              const road=bounds('background-airport-access-road');
              const roadConnected=Math.abs(road.maximumWorld.x+.5)<.001&&Math.abs((road.minimumWorld.z+road.maximumWorld.z)/2-state.scenery.access_y)<.001;
              const airportOwners=f.pickables.filter(p=>p.userData?.transport?.startsWith('Airport'));
              const modelsFit=airportOwners.every(owner=>{
                const prop=state.props.find(p=>p.id===owner.userData.structure);
                const bounds=owner.native.getHierarchyBoundingVectors(true),span=bounds.max.subtract(bounds.min);
                const ray=new BABYLON.Ray(new BABYLON.Vector3((bounds.min.x+bounds.max.x)/2,bounds.max.y+5,(bounds.min.z+bounds.max.z)/2),new BABYLON.Vector3(0,-1,0));
                return span.x<=prop.width*.94+.01&&span.z<=prop.depth*.94+.01&&Math.abs(bounds.min.y)<.01&&
                  !!f.nativeScene.pickWithRay(ray,m=>m.metadata?.pickOwner===owner)?.hit;
              });
              const layers=[...f.terrainLayers].filter(([id])=>id!=='fog').map(([,layer])=>layer);
              f.sync({...state,fog:{...state.fog,visible:state.fog.visible.slice(10)}},'s0',null,'move');
              return {size:n,buildings:state.buildings.length,props:state.props.length,continuous,roadConnected,modelsFit,
                backgroundProps:f.background.placements.length,
                airportModels:[...new Set(f.pickables.map(p=>p.userData?.transport).filter(id=>id?.startsWith('Airport')))],
                isolated:meshes.every(m=>!m.isPickable&&!m.metadata?.pickOwner),
                retained:background===f.background.root&&ground===f.terrainLayers.get('ground')&&layers.every(layer=>[...f.terrainLayers.values()].includes(layer))};
            }''',state)
            assert all(result[k] for k in ('continuous','roadConnected','isolated','retained','modelsFit')),result
            assert result['backgroundProps']==0,result
            assert {'AirportTug','AirportFuelBowser','AirportPowerCart','AirportWindsock'}<=set(result['airportModels']),result
            assert {'AirportLightPlane','AirportBusinessJet'}&set(result['airportModels']),result
            page.wait_for_function('f.nativeScene.isReady()');page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
            if size==30 and not gpu:page.screenshot(path='/tmp/airport.jpg',type='jpeg',quality=75)
            page.evaluate("f.setView('0');f.sync(f.state,'s0',null,'move');f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()")
            if size==30 and not gpu:page.screenshot(path='/tmp/airport-interior.jpg',type='jpeg',quality=80)
            print(result,flush=True)
        assert not errors,errors
        browser.close()
        print('PASS airport rendering, background bounds, picking isolation and retained fog updates',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
