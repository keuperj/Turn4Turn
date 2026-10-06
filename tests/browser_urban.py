"""Render dense downtown maps, street continuity, amenities and upper cutaways."""
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
        page.route('**/urban-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><div style="width:1000px;height:750px"><canvas style="width:100%;height:100%"></canvas></div></body>'))
        page.goto(base+'/urban-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        page.evaluate('''async gpu=>{const {Battlefield}=await import('/scene.js');window.field=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await field.ready;field.engine.stopRenderLoop();}''',gpu)
        assert page.evaluate('field.renderer')==('webgpu' if gpu else 'webgl')
        for size in (24,30,40):
            g=Game(41,'urban',size=size);state=g.state()
            state.update(buildings=g.buildings,props=g.props,walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),units=[],stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
            result=page.evaluate('''state=>{
              const f=field,n=state.size;f.setView('exterior');f.sync(state,null,null,'move');f.controls.target.set((n-1)/2,3,(n-1)/2);f.camera.position.set(n+24,n+34,n+28);f.controls.update();f.background.atmosphere();
              const meshes=f.nativeScene.meshes,roads=f.background.root.getChildMeshes().filter(m=>m.name==='background-road-extension');
              const outside=roads.every(m=>{m.computeWorldMatrix(true);const b=m.getBoundingInfo().boundingBox;return b.maximumWorld.x<=-.499||b.maximumWorld.z<=-.499||b.minimumWorld.x>=n-.501||b.minimumWorld.z>=n-.501;});
              const amenities=state.props.every(p=>f.pickables.some(o=>o.userData.structure===p.id));
              const vehicles=state.props.filter(p=>p.kind==='car'||p.kind==='ambulance').every(p=>{
                const owner=f.pickables.find(o=>o.userData.structure===p.id&&o.userData.transport);if(!owner)return false;
                owner.native.computeWorldMatrix(true);const b=owner.native.getHierarchyBoundingVectors(true),s=b.max.subtract(b.min);return s.x<=p.width+.01&&s.z<=p.depth+.01;
              });
              const root=f.background.root;f.sync({...state,round:state.round+1},null,null,'move');
              return {size:n,buildings:state.buildings.length,heights:[...new Set(state.buildings.map(b=>b.level))],roads:roads.length,outside,amenities,vehicles,stable:root===f.background.root,
               paving:['urban-sidewalk','urban-plaza','urban-park','urban-park_path','urban-crosswalk','urban-cafe-front','urban-shop-front'].every(name=>meshes.some(m=>m.name===name))};
            }''',state)
            assert all(result[k] for k in ('outside','amenities','vehicles','stable','paving')),result
            assert result['roads']>=8,result
            page.wait_for_function('field.nativeScene.isReady()');page.evaluate('field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()')
            if size==30 and not gpu:page.screenshot(path='/tmp/urban-downtown-exterior.jpg',type='jpeg',quality=70)
            page.evaluate("field.setView('5');field.sync(field.state,null,null,'move');field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()")
            page.wait_for_function('field.nativeScene.isReady()')
            page.evaluate("field.setView('0');field.sync(field.state,null,null,'move');field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()")
            page.wait_for_function('field.nativeScene.isReady()');page.evaluate('field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()')
            if size==30 and not gpu:page.screenshot(path='/tmp/urban-downtown-cutaway.jpg',type='jpeg',quality=70)
            print(result,flush=True)
        assert not errors,errors
        browser.close()
        print('PASS downtown rendering, amenities, continuous streets, picking and tall-building cutaways',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
