"""Render all seven game scenarios; check HQ assets, picking, opacity and emitter cleanup.
Run with VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json on software Vulkan.
"""
import base64
import sys
import threading
from http.server import HTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from world import THEMES
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    def log_message(self, *_args):
        pass

httpd = HTTPServer(('127.0.0.1', 0), QuietHandler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{httpd.server_port}'
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chromium', headless=True, args=[
            '--no-sandbox', '--use-angle=vulkan', '--enable-features=Vulkan',
            '--disable-vulkan-surface', '--enable-unsafe-webgpu'])
        page = browser.new_page(viewport={'width':1000, 'height':800})
        page.set_default_timeout(120000)
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base+'/?mode=single')
        page.wait_for_selector('#welcome[open]')
        page.wait_for_function("document.documentElement.dataset.gpuTest==='pass'")
        page.locator('#welcome-name').fill('Scenery Tester')
        page.locator('#cookie-consent').check()
        page.locator('#welcome-form button').click()
        page.wait_for_selector('#preparation[open]')
        page.wait_for_function("!document.body.classList.contains('busy')")
        page.evaluate("async()=>{window.field=(await import('/app.js')).battlefield;field.engine.stopRenderLoop();}")
        for index, theme in enumerate(THEMES):
            g=Game(41+index,theme,size=24)
            state=g.state()
            # Reveal geometry for this visual fixture only. Production fog is untouched.
            state.update(tiles=g.tiles,heights=g.heights,buildings=g.buildings,
                         walls=list(g.walls.values()),portals=g.portals,props=g.props,
                         surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,
                         fog=dict(visible=sorted(g.surfaces),explored=sorted(g.surfaces)))
            result=page.evaluate('''state=>{
                const f=field;f.setView('exterior');f.sync(state,state.units[0]?.id,'move');
                const bg=f.nativeScene.getTransformNodeByName('scenario-background-'+state.theme);
                const outside=bg.getChildMeshes().filter(m=>m.name!=='background-ground').every(m=>{
                    m.computeWorldMatrix(true);const p=m.getAbsolutePosition();return p.x<0||p.z<0||p.x>=state.size||p.z>=state.size;
                });
                const detailed=f.nativeScene.meshes.filter(m=>m.name.endsWith('-body')||m.name.endsWith('-cabin'));
                const opaque=detailed.every(m=>!m.material.needAlphaBlendingForMesh(m)&&m.material.alpha===1&&m.material.backFaceCulling);
                const props=state.props.filter(p=>['car','tree_oak','tree_pine','tree_birch','bush'].includes(p.kind));
                const pickable=props.every(p=>f.pickables.some(o=>o.userData.structure===p.id&&o.native.getChildMeshes().some(m=>m.isPickable&&m.metadata?.pickOwner===o)));
                const bounds=state.props.filter(p=>p.kind==='car').every(p=>{
                    const owner=f.pickables.find(o=>o.userData.structure===p.id&&o.native.getChildMeshes().some(m=>m.name.endsWith('-body')));
                    const b=owner.native.getHierarchyBoundingVectors(true),s=b.max.subtract(b.min);
                    return s.x<=p.width+.01&&s.z<=p.depth+.01;
                });
                f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame();
                return {theme:state.theme,background:!!bg,outside,opaque,pickable,bounds,meshes:f.nativeScene.meshes.length};
            }''',state)
            assert all(result[k] for k in ['background','outside','opaque','pickable','bounds']), result
            print(result,flush=True)
            page.wait_for_function('field.nativeScene.isReady()')
            # Exercise floor cutaways as well as roofs, with actual GPU submission.
            page.evaluate("()=>{field.setView('0');field.sync(field.state,field.selected,'move');field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame();}")
            page.wait_for_function('field.nativeScene.isReady()')
            if theme in ('urban','airport','woods','train_station'):
                data=page.evaluate('''async()=>{
                    const f=field,B=BABYLON,c=f.camera.native,n=f.state.size;
                    c.position.set(n+14,n+18,n+16);c.setTarget(new B.Vector3(n/2,0,n/2));
                    const target=new B.RenderTargetTexture('verification',{width:900,height:700},f.nativeScene,false);
                    target.renderList=f.nativeScene.meshes.slice();target.activeCamera=c;
                    const previous=c.outputRenderTarget;c.outputRenderTarget=target;
                    f.engine.beginFrame();f.nativeScene.render();f.engine.endFrame();c.outputRenderTarget=previous;
                    const pixels=await target.readPixels();target.dispose();
                    const canvas=document.createElement('canvas');canvas.width=900;canvas.height=700;
                    const ctx=canvas.getContext('2d'),out=ctx.createImageData(900,700);
                    for(let y=0;y<700;y++)out.data.set(pixels.subarray(y*3600,(y+1)*3600),(699-y)*3600);
                    ctx.putImageData(out,0,0);return canvas.toDataURL();
                }''')
                Path('/tmp/game-'+theme+'-webgpu.png').write_bytes(base64.b64decode(data.split(',')[1]))
        effects=page.evaluate('''()=>{
            // Babylon lazily creates its scene-owned fallback material during disposal.
            const f=field;void f.nativeScene.defaultMaterial;
            const names=new Set(f.nativeScene.materials),baseline=[f.nativeScene.meshes.length,f.nativeScene.materials.length,f.nativeScene.textures.length,f.nativeScene.lights.length];
            const state={seed:400,smoke:[{x:2,y:2,z:0,radius:2}],fires:[{x:5,y:5,z:0}]};
            f.syncAtmosphere(state);const first=[...f.ambientEffects.values()][0];
            const before=first.effect.particles[0].m.position.clone();f.elapsed+=.5;f.syncAtmosphere(state);
            const stable=first===[...f.ambientEffects.values()][0],animated=!before.equals(first.effect.particles[0].m.position);
            const fire=[...f.ambientEffects.values()][1].effect.particles.some(p=>p.kind==='fire'&&p.m.isEnabled());
            f.syncAtmosphere({seed:401});
            for(let i=0;i<3;i++){f.syncAtmosphere(state);f.syncAtmosphere({seed:401});}
            const after=[f.nativeScene.meshes.length,f.nativeScene.materials.length,f.nativeScene.textures.length,f.nativeScene.lights.length];
            return {stable,animated,fire,clean:JSON.stringify(after)===JSON.stringify(baseline),baseline,after,added:f.nativeScene.materials.filter(m=>!names.has(m)).map(m=>m.name)};
        }''')
        assert all(effects[k] for k in ['stable','animated','fire','clean']),effects
        assert not errors,errors
        browser.close()
        print('PASS: seven WebGPU scenarios, opaque cars, footprints, picking, cutaways and persistent effect cleanup.')
finally:
    httpd.shutdown()
    httpd.server_close()
