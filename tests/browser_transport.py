"""Verify every imported transport in the actual renderer, including scale and cleanup.
Run: .venv/bin/python tests/browser_transport.py [--webgpu]
Software Vulkan: VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
"""
import base64
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from world import THEMES, PROP_SIZE
from playwright.sync_api import sync_playwright


class QuietHandler(server.Handler):
    def log_message(self, *_args):
        pass


def main():
    gpu = '--webgpu' in sys.argv
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            args = ['--no-sandbox', '--disable-dev-shm-usage', '--enable-unsafe-swiftshader']
            args += (['--use-angle=vulkan', '--enable-features=Vulkan', '--disable-vulkan-surface', '--enable-unsafe-webgpu']
                     if gpu else ['--use-gl=angle', '--use-angle=swiftshader'])
            browser = p.chromium.launch(headless=True, args=args)
            page = browser.new_page(viewport={'width':1500, 'height':1050})
            page.set_default_timeout(120000)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            # A bare same-origin page avoids starting a second application scene.
            page.route('**/transport-test', lambda route: route.fulfill(content_type='text/html', body='<body style="margin:0"><div style="width:1500px;height:1050px"><canvas style="width:100%;height:100%"></canvas></div></body>'))
            page.goto(f'http://127.0.0.1:{httpd.server_port}/transport-test')
            page.add_script_tag(url='/vendor/babylon.js')
            page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
            result = page.evaluate('''async gpu=>{
                const {Battlefield}=await import('/scene.js');
                window.field=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{},{ok:gpu});
                await field.ready;field.engine.stopRenderLoop();
                return {renderer:field.renderer,failures:field.transport.failures,count:field.transport.sources.size};
            }''', gpu)
            assert result['renderer'] == ('webgpu' if gpu else 'webgl'), result
            assert not result['failures'] and result['count'] == len(json.loads((server.ROOT/'assets/models/transport/manifest.json').read_text())['models']), result
            for index, theme in enumerate(THEMES):
                game = Game(41 + index, theme, size=24)
                state = game.state()
                state.update(tiles=game.tiles, heights=game.heights, buildings=game.buildings,
                             walls=list(game.walls.values()), portals=game.portals, props=game.props,
                             surfaces=sorted(game.surfaces), stairs=game.stairs, ladders=game.ladders,
                             fog=dict(visible=sorted(game.surfaces), explored=sorted(game.surfaces)))
                # Raw world props have health initialized by Game.
                report = page.evaluate('''state=>{
                    field.sync(state,state.units[0]?.id,null,'move');
                    field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame();
                    const models=state.props.filter(p=>p.model);
                    return {theme:state.theme,expected:models.length,actual:field.pickables.filter(o=>o.userData.transport).length};
                }''', state)
                assert report['expected'] == report['actual'], report
                print(report, flush=True)
            dimensions = page.evaluate('''async sizes=>{
                const {addProp}=await import('/environment.js');
                field.clear(field.terrain);field.clear(field.actors);field.clear(field.overlay);field.pickables=[];
                const reports=[];let i=0;
                for(const entry of field.transport.models){
                    const [width,depth]=sizes[entry.kind],x=4+(i%4)*10,y=4+Math.floor(i/4)*13;
                    const p={id:'fixture'+i,kind:entry.kind,model:entry.id,width,depth,x,y,hp:100,max_hp:100};
                    const owner=addProp(field,p),bounds=owner.native.getHierarchyBoundingVectors(true),span=bounds.max.subtract(bounds.min);
                    const ray=new BABYLON.Ray(new BABYLON.Vector3((bounds.min.x+bounds.max.x)/2,bounds.max.y+5,(bounds.min.z+bounds.max.z)/2),new BABYLON.Vector3(0,-1,0));
                    const hit=field.nativeScene.pickWithRay(ray,m=>m.metadata?.pickOwner===owner);
                    reports.push({id:entry.id,span:span.asArray(),bottom:bounds.min.y,uniform:Math.max(...span.asArray().map((v,j)=>v/entry.dimensions[j]))-Math.min(...span.asArray().map((v,j)=>v/entry.dimensions[j])),fits:span.x<=width*.94+.01&&span.z<=depth*.94+.01,picked:!!hit?.hit});
                    const unit={...field.state.units[0],id:'scale-human'+i,x:x+width+1,y:y+depth/2,z:0,stance:'standing',team:'soldier',hp:100};
                    field.actors.add(field.figure(unit));
                    i++;
                }
                field.sky.intensity=.85;field.sun.intensity=2.6;field.sun.diffuse=BABYLON.Color3.FromHexString('#fff1db');
                // A three-metre building floor and door alongside the human/vehicle lineup.
                field.box(field.terrain,8,3,.2,17,1.5,0,0xbca98f);
                field.box(field.terrain,1,2.2,.1,17,1.1,.15,0x4f665f);
                field.box(field.terrain,48,.08,55,20,-.05,23,0x85897e);
                field.camera.position.set(59,57,78);field.controls.target.set(19,0,23);field.controls.update();
                field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame();
                return reports;
            }''', PROP_SIZE)
            for report in dimensions:
                assert report['fits'] and report['picked'], report
                assert report['uniform'] < .001, report
                assert -.005 <= report['bottom'] <= .09, report
                print(report, flush=True)
            page.wait_for_function('field.nativeScene.isReady()')
            page.evaluate('field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()')
            if gpu:
                # Headless Chromium may not composite WebGPU into page screenshots.
                # Read the rendered target explicitly, as in the scenery regression.
                data=page.evaluate("""async()=>{
                    const f=field,B=BABYLON,c=f.camera.native;
                    const target=new B.RenderTargetTexture('transport-review',{width:1200,height:840},f.nativeScene,false);
                    target.renderList=f.nativeScene.meshes.slice();target.activeCamera=c;
                    const previous=c.outputRenderTarget;c.outputRenderTarget=target;
                    f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame();c.outputRenderTarget=previous;
                    const pixels=await target.readPixels();target.dispose();
                    const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=840;
                    const ctx=canvas.getContext('2d'),out=ctx.createImageData(1200,840);
                    for(let y=0;y<840;y++)out.data.set(pixels.subarray(y*4800,(y+1)*4800),(839-y)*4800);
                    ctx.putImageData(out,0,0);return canvas.toDataURL();
                }""")
                Path('/tmp/transport-webgpu.png').write_bytes(base64.b64decode(data.split(',')[1]))
            else:
                page.screenshot(path='/tmp/transport-webgl.png')
            cleanup = page.evaluate('''async()=>{
                const {addProp}=await import('/environment.js');
                field.clear(field.terrain);field.clear(field.actors);field.pickables=[];
                const baseline=field.nativeScene.meshes.length,materials=field.nativeScene.materials.length;
                for(let i=0;i<3;i++){
                    const owner=addProp(field,{id:'reuse',kind:'car',model:'SUV',width:2,depth:5,x:2,y:2,hp:100,max_hp:100});
                    if(!owner.userData.transport)throw Error('Clone failed after cleanup');
                    field.clear(field.terrain);field.pickables=[];
                }
                const after=field.nativeScene.meshes.length,afterMaterials=field.nativeScene.materials.length;
                const fallback=addProp({...field,transport:{add:()=>false},renderer:'webgl',terrain:field.terrain,pickables:field.pickables,box:field.box.bind(field),material:field.material.bind(field),healthLabel:field.healthLabel.bind(field)},{id:'fallback',kind:'bus',width:3,depth:7,x:2,y:2,hp:100,max_hp:100});
                return {baseline,after,materials,afterMaterials,fallback:fallback.native.getChildMeshes().length>0};
            }''')
            assert cleanup['baseline'] == cleanup['after'] and cleanup['fallback'], cleanup
            assert cleanup['materials'] == cleanup['afterMaterials'], cleanup
            # A missing asset must finish loading and leave the procedural path usable.
            page.route('**/assets/models/transport/manifest.json', lambda route: route.fulfill(
                content_type='application/json', body=json.dumps({'models':[{'id':'missing-bus','kind':'bus','file':'missing-bus.glb'}]})))
            failed = page.evaluate('''async()=>{
                const {TransportAssets}=await import('/transport.js'),{addProp}=await import('/environment.js');
                const assets=new TransportAssets(field);await assets.load();field.transport=assets;
                const owner=addProp(field,{id:'missing',kind:'bus',model:'missing-bus',width:3,depth:7,x:8,y:2,hp:65,max_hp:65});
                return {failures:assets.failures,procedural:!owner.userData.transport&&owner.native.getChildMeshes().length>0};
            }''')
            assert failed == {'failures':['missing-bus'],'procedural':True}, failed
            assert not errors, errors
            print(result, cleanup, flush=True)
            browser.close()
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    main()
