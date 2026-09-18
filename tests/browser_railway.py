"""Rail station visuals, train bounds, city continuation and cached fog updates."""
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
        page.route('**/railway-test',lambda route:route.fulfill(content_type='text/html',body='<body style="margin:0"><div style="width:1000px;height:750px"><canvas style="width:100%;height:100%"></canvas></div></body>'))
        page.goto(base+'/railway-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        page.evaluate('''async gpu=>{const {Battlefield}=await import('/scene.js');window.f=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await f.ready;f.engine.stopRenderLoop();}''',gpu)
        assert page.evaluate('f.renderer')==('webgpu' if gpu else 'webgl')
        for size in (24,30,40):
            g=Game(41,'train_station',size=size);state=g.state()
            # Exercise the real fog-filtered payload before the fully revealed fixture.
            actual=page.evaluate('''state=>{
              f.setView('exterior');f.sync(state,'s0',null,'move');
              let missing=[],unknown=0;
              for(const b of state.buildings){
                const leaves=[];f.terrainLayers.get('building:'+b.id).group.traverse(o=>{if(['building-door','building-window','station-double-door'].includes(o.native.name))leaves.push(o);});
                for(const kind of ['door','window']){
                  const expected=b.exterior_openings.filter(p=>p.kind===kind).length;
                  const count=leaves.filter(o=>kind==='window'?o.native.name==='building-window':o.native.name!=='building-window').length;
                  if(count<expected)missing.push(b.id+':'+kind);
                }
                unknown+=leaves.filter(o=>o.userData.facadeOnly&&!o.userData.portal).length;
              }
              return {missing,unknown,invalidPortal:f.portalModels.has(undefined)};
            }''',state)
            assert not actual['missing'] and actual['unknown']>0 and not actual['invalidPortal'],actual
            if size==30 and not gpu:
                page.wait_for_function('f.nativeScene.isReady()');page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
                page.screenshot(path='/tmp/railway-real-fog.jpg',type='jpeg',quality=75)
            state.update(buildings=g.buildings,props=g.props,walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
            result=page.evaluate('''state=>{
              f.setView('exterior');f.sync(state,'s0',null,'move');const n=state.size;f.controls.target.set((n-1)/2,0,(n-1)/2);f.camera.position.set(n+9,n+15,n+9);f.controls.update();f.background.atmosphere();
              const meshes=f.nativeScene.meshes,background=f.background.root,ground=f.terrainLayers.get('ground');
              const cars=state.props.filter(p=>p.kind==='train'),fits=cars.every(p=>{
                const owner=f.pickables.find(o=>o.userData.structure===p.id&&o.userData.transport);if(!owner)return false;
                owner.native.computeWorldMatrix(true);const b=owner.native.getHierarchyBoundingVectors(true),s=b.max.subtract(b.min);return s.x<=p.width+.01&&s.z<=p.depth+.01;
              });
              const roads=background.getChildMeshes().filter(m=>m.name==='background-railway-rails');
              const outside=roads.every(m=>{m.computeWorldMatrix(true);const b=m.getBoundingInfo().boundingBox;return b.maximumWorld.x<=-.499||b.maximumWorld.z<=-.499||b.minimumWorld.x>=n-.501||b.minimumWorld.z>=n-.501;});
              f.sync({...state,fog:{...state.fog,visible:state.fog.visible.slice(10)}},'s0',null,'move');
              return {size:n,buildings:state.buildings.length,trains:cars.length,fits,outside,roads:roads.length,
                surfaces:['station-platform','station-plaza','railway-ballast','railway-sleepers','railway-rails','station-platform-safety','station-track-crossings'].every(name=>meshes.some(m=>m.name===name)),
                housing:f.background.placements.filter(p=>['House2','House3','Flat','Flat2','Shop'].includes(p.id)).length,
                city:f.background.placements.some(p=>p.id==='Flat')&&f.background.placements.some(p=>p.id==='House2'),
                doubleDoors:meshes.filter(m=>m.name==='station-double-door').length===4,
                furniture:['bench','ticket_counter','cafe_table','trash'].every(kind=>state.props.some(p=>p.kind===kind&&p.interior)),
                trees:state.props.filter(p=>p.kind.startsWith('tree_')).length>=3,
                backgroundMeshes:background.getChildMeshes().length,isolated:background.getChildMeshes().every(m=>!m.isPickable&&!m.metadata?.pickOwner),
                retained:background===f.background.root&&ground===f.terrainLayers.get('ground')};
            }''',state)
            assert all(result[k] for k in ('fits','outside','surfaces','city','isolated','retained','doubleDoors','furniture','trees')),result
            assert result['roads']==2 and result['housing']>=15 and result['backgroundMeshes']<1500,result
            page.wait_for_function('f.nativeScene.isReady()');page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
            if size==30 and not gpu:page.screenshot(path='/tmp/railway-station.jpg',type='jpeg',quality=75)
            page.evaluate("f.setView('0');f.sync(f.state,'s0',null,'move');f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()")
            page.wait_for_function('f.nativeScene.isReady()')
            if size==30 and not gpu:
                page.wait_for_function('f.nativeScene.isReady()');page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
                page.screenshot(path='/tmp/railway-hall.jpg',type='jpeg',quality=75)
            print(result,flush=True)
        assert not errors,errors
        browser.close()
        print('PASS railway station: all sizes, train bounds, platforms, city background and retained fog updates',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
