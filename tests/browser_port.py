"""Render Port in WebGL or WebGPU and verify scenery bounds and lifecycle."""
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
    """Exercise all map sizes, lighting, water continuity and asset loading."""
    with sync_playwright() as p:
        flags=['--no-sandbox','--enable-unsafe-swiftshader']+(['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if gpu else ['--use-gl=angle','--use-angle=swiftshader'])
        browser=p.chromium.launch(headless=True,args=flags)
        page=browser.new_page(viewport={'width':1200,'height':850});page.set_default_timeout(120000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/port-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><canvas style="width:1200px;height:850px"></canvas></body>'))
        page.goto(base+'/port-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        page.evaluate('''async gpu=>{const {Battlefield}=await import('/scene.js');window.f=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await f.ready;f.engine.stopRenderLoop();}''',gpu)
        assert page.evaluate('f.transport.failures.concat(f.background.failures)')==[]
        assert page.evaluate('f.renderer')==('webgpu' if gpu else 'webgl')
        for size in (24,30,40):
            g=Game(41,'port',size=size);state=g.state()
            state.update(buildings=g.buildings,props=g.props,walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
            result=page.evaluate('''state=>{
              f.setView('exterior');f.sync(state,'s0',null,'move');const n=state.size;f.controls.target.set((n-1)/2,0,(n-1)/2-2);f.camera.position.set(n+12,n+23,n+16);f.controls.update();f.background.atmosphere();
              const background=f.background.root,ground=f.terrainLayers.get('ground'),meshes=background.getChildMeshes();
              const land=f.nativeScene.getMeshByName('background-port-land');land.computeWorldMatrix(true);
              const landBound=land.getBoundingInfo().boundingBox.minimumWorld.z;
              const dockModels=ground.group.native.getChildMeshes().filter(m=>m.metadata?.asset==='PortPontoon');
              const boatModels=ground.group.native.getChildMeshes().filter(m=>m.metadata?.asset?.startsWith('PortCruiser'));
              const dockBounds=dockModels.filter(m=>m.getTotalVertices()).map(m=>{m.computeWorldMatrix(true);return m.getBoundingInfo().boundingBox;});
              const dockAligned=Math.abs(Math.max(...dockBounds.map(b=>b.maximumWorld.y)))<.01&&dockBounds.every(b=>b.maximumWorld.y<.01&&b.minimumWorld.z>=1.49&&b.maximumWorld.z<=state.scenery.shore_y-.49);
              const fogPoints=[],originalTiles=f.tiles;try{f.tiles=(_parent,points)=>fogPoints.push(...points);f.buildFog(state);}finally{f.tiles=originalTiles;}
              const water=new Set(state.scenery.water.map(p=>p.join(','))),waterClear=fogPoints.every(p=>!water.has(`${p.x},${p.z}`));
              const isolated=meshes.every(m=>!m.isPickable&&!m.metadata?.pickOwner)&&dockModels.concat(boatModels).every(m=>!m.isPickable);
              const industrial=meshes.filter(m=>m.metadata?.industrial);
              const inland=industrial.every(m=>{m.computeWorldMatrix(true);return m.getBoundingInfo().boundingBox.minimumWorld.z>=state.scenery.shore_y-.5;});
              f.sync({...state,fog:{...state.fog,visible:state.fog.visible.slice(10)}},'s0',null,'move');
              return {size:n,waterClear,continuous:Math.abs(landBound-(state.scenery.shore_y-.5))<.001,dockAligned,isolated,inland,docks:dockModels.length,boats:boatModels.length,ships:f.background.placements.length,industrial:industrial.length,retained:background===f.background.root&&ground===f.terrainLayers.get('ground')};
            }''',state)
            assert all(result[k] for k in ('waterClear','continuous','dockAligned','isolated','inland','retained')),result
            assert result['docks']>0 and result['boats']>0 and result['ships']>=8 and result['industrial']>10,result
            page.wait_for_function('f.nativeScene.isReady()');page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
            if size==30 and not gpu:page.screenshot(path='/tmp/port.jpg',type='jpeg',quality=85)
            page.evaluate("f.sync({...f.state,lighting:'night'},'s0',null,'move');f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()")
            assert page.evaluate('f.nativeScene.fogColor.r<.1')
            print(result,flush=True)
        assert page.evaluate('''()=>{
          const source=f.transport.sources.get('PortPontoon');f.transport.sources.delete('PortPontoon');
          try{f.sync({...f.state,seed:f.state.seed+1},'s0',null,'move');return f.terrainLayers.get('ground').group.native.getChildMeshes().filter(m=>m.name==='port-pier-fallback').length===4;}
          finally{f.transport.sources.set('PortPontoon',source);}
        }''')
        assert not errors,errors
        browser.close();print('PASS Port rendering, connected waterfront, models, inland industry, isolation, lighting and retained fog updates')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
