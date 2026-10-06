"""Real move latency, retained meshes/skeletons, fog isolation and cache invalidation.

Run with --webgpu to exercise the same updates on WebGPU.
Timing is reported, not used as a hardware-dependent pass/fail threshold.
"""
import argparse
import copy
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from game import Game
from browser_background import QuietHandler
from playwright.sync_api import sync_playwright


def main(base,gpu):
    g=Game(41,'urban',size=30);before=copy.deepcopy(g.state());u=g.units[0]
    paths=g.paths(u,5,known_units=True)
    dest=min((p for p in paths if p in g.explored),key=lambda p:(p[1],abs(p[0]-u['x'])))
    start=time.perf_counter();g.action(dict(action='move',unit=u['id'],x=dest[0],y=dest[1],z=dest[2]));after=g.state()
    print('server move and state: %.1f ms'%((time.perf_counter()-start)*1000),flush=True)
    with sync_playwright() as p:
        flags=['--no-sandbox','--enable-unsafe-swiftshader']+(['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if gpu else ['--use-gl=angle','--use-angle=swiftshader'])
        browser=p.chromium.launch(headless=True,args=flags)
        page=browser.new_page(viewport={'width':1000,'height':750});page.set_default_timeout(120000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/incremental-test',lambda route:route.fulfill(content_type='text/html',body='<div style="width:1000px;height:750px"><canvas style="width:100%;height:100%"></canvas></div>'))
        page.goto(base+'/incremental-test');page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
        page.evaluate('''async gpu=>{
          const {Battlefield}=await import('/scene.js');window.f=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});await f.ready;f.engine.stopRenderLoop();
          window.apply=s=>{const start=performance.now();f.sync(s,'s0',null,'move');return performance.now()-start;};
          window.counts=()=>[f.nativeScene.meshes.length,f.nativeScene.materials.length,f.nativeScene.textures.length,f.nativeScene.skeletons.length,f.nativeScene.animationGroups.length];
        }''',gpu)
        assert page.evaluate('f.renderer')==('webgpu' if gpu else 'webgl')
        page.evaluate('apply',before);page.wait_for_function('f.nativeScene.isReady()')
        page.evaluate('''()=>{window.oldModels=new Map(f.models);window.oldBackground=f.background.root;}''')
        elapsed=page.evaluate('apply',after)
        assert page.evaluate('''()=>[...oldModels].every(([id,m])=>!f.models.has(id)||f.models.get(id)===m)&&oldBackground===f.background.root''')
        assert page.evaluate('''()=>{const u=f.state.units.find(u=>u.id==='s0'),m=f.models.get('s0');return m.position.x===u.x&&m.position.z===u.y&&m.position.y===u.z*3;}''')
        print('move synchronization: %.1f ms'%elapsed,flush=True)
        fog_result=page.evaluate('''()=>{
          const s=structuredClone(f.state),old=new Map(f.terrainLayers),models=new Map(f.models);s.fog.visible=s.fog.visible.slice(8);
          const removed=[];const watch=f.nativeScene.onMeshRemovedObservable.add(m=>removed.push(m));const ms=apply(s);f.nativeScene.onMeshRemovedObservable.remove(watch);
          return {ms,removed:removed.length,retained:[...old].every(([key,e])=>key==='fog'||f.terrainLayers.get(key)===e),actors:[...models].every(([id,m])=>f.models.get(id)===m)};
        }''')
        assert fog_result['retained'] and fog_result['actors'] and fog_result['removed']<=6,fog_result
        print('fog-only synchronization:',fog_result,flush=True)
        # Opening a portal changes its building, not every neighboring structure.
        assert page.evaluate('''()=>{
          const s=structuredClone(f.state),door=s.walls.find(w=>w.kind==='door');if(!door)throw Error('No door fixture');
          const previous=new Map(f.terrainLayers);door.open=!door.open;const p=s.portals.find(p=>p.id===door.id);if(p)p.open=door.open;apply(s);
          return previous.get('building:'+door.building)!==f.terrainLayers.get('building:'+door.building)&&
            [...previous].filter(([key])=>key.startsWith('building:')&&key!=='building:'+door.building).every(([key,e])=>f.terrainLayers.get(key)===e)&&
            Math.abs(f.portalModels.get(door.id).rotation.y-(door.open?Math.PI*.48:0))<.001;
        }''')
        # HP/destruction and authoritative removal must invalidate cached props.
        assert page.evaluate('''()=>{
          const s=structuredClone(f.state),p=s.props[0],key='prop:'+p.id,previous=f.terrainLayers.get(key);p.hp=0;p.destroyed=true;apply(s);
          const replaced=previous!==f.terrainLayers.get(key)&&previous.group.native.isDisposed();
          const removed=f.terrainLayers.get(key);s.props=s.props.filter(v=>v.id!==p.id);apply(structuredClone(s));
          return replaced&&!f.terrainLayers.has(key)&&removed.group.native.isDisposed()&&!f.pickables.some(o=>o.userData.structure===p.id);
        }''')
        # Revealed and then hidden contacts release their skeleton and pick targets.
        assert page.evaluate('''()=>{
          const s=structuredClone(f.state),contact={...s.units[0],id:'test-contact',team:'alien',x:0,y:s.size-1};s.units.push(contact);apply(s);
          const model=f.models.get(contact.id);if(!model)throw Error('No visible contact');
          s.units=s.units.filter(u=>u.id!==contact.id);s.last_seen=[{id:contact.id,name:contact.name,x:contact.x,y:contact.y,z:0,round:1}];apply(structuredClone(s));
          return !f.models.has(contact.id)&&!f.characters.instances.has(model)&&model.native.isDisposed()&&f.memoryLayer.children.length===1;
        }''')
        # Reveal a building's floor data, cut it open, then restore its exterior.
        revealed=copy.deepcopy(after)
        revealed.update(buildings=copy.deepcopy(g.buildings),props=copy.deepcopy(g.props),walls=copy.deepcopy(list(g.walls.values())),portals=copy.deepcopy(g.portals),tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,fog={'visible':sorted(g.surfaces),'explored':sorted(g.surfaces)})
        page.evaluate('apply',revealed)
        assert page.evaluate('''()=>{
          f.setView('exterior');apply(f.state);const ground=f.terrainLayers.get('ground'),props=f.terrainLayers.get('prop:'+f.state.props[0].id);
          f.setView('0');apply(f.state);const b=f.state.buildings[0],inside=f.pickSurfaceSet.has(`${b.x},${b.y},0`);
          f.setView('exterior');apply(f.state);return inside&&f.pickSurfaceSet.has(`${b.x},${b.y},${b.level}`)&&f.terrainLayers.get('ground')===ground&&f.terrainLayers.get('prop:'+f.state.props[0].id)===props;
        }''')
        page.wait_for_function('f.nativeScene.isReady()')
        page.evaluate('f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame()')
        # Alternate discovery snapshots and mission resets; caches must not grow.
        page.evaluate('apply',before);page.wait_for_function('f.nativeScene.isReady()')
        page.evaluate('void f.nativeScene.defaultMaterial')
        baseline=page.evaluate('counts()')
        page.evaluate('window.startTextures=new Set(f.nativeScene.textures)')
        for _ in range(2):
            page.evaluate('apply',after)
            page.evaluate('apply',{**before,'seed':before['seed']+1})
            page.evaluate('apply',before)
        page.wait_for_function('f.nativeScene.isReady()')
        final=page.evaluate('counts()')
        assert final==baseline,(baseline,final,page.evaluate('f.nativeScene.textures.filter(t=>!startTextures.has(t)).map(t=>({name:t.name,url:t.url}))'))
        assert not errors,errors
        print('PASS retained scenery/characters, fog, portal and prop invalidation, hidden contacts, cutaways and resource cleanup',flush=True)
        browser.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');args=parser.parse_args()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args.webgpu)
    finally:httpd.shutdown();httpd.server_close()
