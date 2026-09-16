"""Integration checks for the WebGL baselines and WebGPU quality study.
Requires a running server: python3 server.py --port 8002.
"""
import argparse
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--engine',choices=['babylon','playcanvas','three','webgpu'])
args=parser.parse_args()

with sync_playwright() as p:
    gpu_args=['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if args.engine=='webgpu' else ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']
    browser=p.chromium.launch(channel='chromium',headless=True,args=['--no-sandbox',*gpu_args])
    page=browser.new_page(viewport={'width':1280,'height':900},accept_downloads=True)
    errors=[];remote=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:print('CONSOLE',m.type,m.text[:400]) if m.type=='error' else None)
    page.on('request',lambda r:remote.append(r.url) if not r.url.startswith(('http://localhost:8002/','data:','blob:')) else None)
    page.goto('http://localhost:8002/comparison/'+('?engine=webgpu' if args.engine=='webgpu' else ''))
    for engine in ([args.engine] if args.engine else ['babylon','playcanvas','three']):
        if engine!='babylon' and not (engine=='webgpu' and args.engine=='webgpu'):page.locator(f'[data-engine="{engine}"]').click()
        page.locator('#status').wait_for(state='hidden',timeout=120000)
        frame=page.frame_locator('#view')
        child=page.frames[1]
        child.wait_for_function('window.comparison && window.comparison.time > .2',timeout=60000)
        print(engine,child.evaluate('({version:comparison.api.version,clips:comparison.api.clips,stats:comparison.api.stats()})'),flush=True)
        assert child.evaluate('comparison.api.clips.length')>0
        if engine=='webgpu':
            assert child.evaluate('comparison.api.backend')=='webgpu'
            assert child.evaluate('comparison.api.scene.getEngine().isWebGPU')
            assert child.evaluate("comparison.api.scene.meshes.some(m=>m.name==='ammo-pouch')")
            assert child.evaluate("['red-hatchback','blue-estate'].every(n=>comparison.api.scene.getTransformNodeByName(n))")
            assert child.evaluate("comparison.api.scene.getMaterialByName('red-hatchback-paint').albedoTexture.url !== comparison.api.scene.getMaterialByName('blue-estate-paint').albedoTexture.url")
            assert child.evaluate('''() => ['red-hatchback','blue-estate'].every(name=>['body','cabin'].every(part=>{
                const mesh=comparison.api.scene.getMeshByName(name+'-'+part);
                const positions=mesh.getVerticesData('position'),normals=mesh.getVerticesData('normal'),indices=mesh.getIndices();
                const center=mesh.getBoundingInfo().boundingBox.center;
                if(mesh.material.needAlphaBlendingForMesh(mesh)||mesh.material.alpha!==1||!mesh.material.backFaceCulling)return false;
                // These convex solids must face outwards on every cap and panel.
                for(let i=0;i<indices.length;i+=3){
                    let dot=0;
                    for(let j=0;j<3;j++){const k=indices[i+j]*3;
                        dot+=(positions[k]-center.x)*normals[k]+(positions[k+1]-center.y)*normals[k+1]+(positions[k+2]-center.z)*normals[k+2];
                    }
                    if(dot<=0)return false;
                }
                return true;
            }))'''), 'Car body and cabin faces must point outwards with opaque, culled materials'

            assert child.evaluate("comparison.api.scene.meshes.filter(m=>m.name==='background-building').every(m=>m.material.albedoTexture)")
            assert child.evaluate("comparison.api.scene.meshes.filter(m=>m.name==='bookcase-shelf').length === 8")
            assert child.evaluate("comparison.api.scene.meshes.filter(m=>m.name==='tree-leaves').length === 7")
        assert child.evaluate('document.querySelector("canvas").width === innerWidth && document.querySelector("canvas").height === innerHeight'), 'Mismatched render resolution'
        if engine=='webgpu':
            child.wait_for_function('comparison.api.scene.isReady()',timeout=120000)
            image=child.evaluate('comparison.api.capture()')
            Path('/tmp/comparison-webgpu-render.png').write_bytes(base64.b64decode(image.split(',')[1]))
            assert child.evaluate('''async data => {
                const bitmap=await createImageBitmap(await (await fetch(data)).blob());
                const canvas=document.createElement('canvas');canvas.width=canvas.height=32;
                const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0,32,32);
                const pixels=ctx.getImageData(0,0,32,32).data,colors=new Set();
                for(let i=0;i<pixels.length;i+=4)if(pixels[i+3]>0)colors.add(pixels.slice(i,i+3).join(','));
                bitmap.close();return colors.size>100;
            }''',image), 'WebGPU capture must contain rendered scene detail'
        page.screenshot(path=f'/tmp/comparison-{engine}.png')
        page.locator('#preset').select_option('interior')
        page.locator('#cutaway').select_option('ground')
        child.wait_for_function('comparison.state.cutaway === "ground"')
        if engine=='webgpu':
            assert child.evaluate("comparison.api.scene.meshes.filter(m=>m.name==='window-architrave').every(m=>!m.isEnabled())"), 'Facade detail must follow cutaways'
        page.locator('#explosion').click()
        child.wait_for_function('comparison.effect?.kind === "explosion"')
        page.locator('#pause').click()
        child.wait_for_function('comparison.state.paused')
        if engine=='webgpu':
            child.evaluate('comparison.effect.start=comparison.time-.3')
            page.wait_for_timeout(400)
            assert child.evaluate("comparison.api.effects.particles.some(p=>p.kind==='spark'&&p.m.isEnabled())")
            positions=child.evaluate("comparison.api.effects.particles.map(p=>p.m.position.asArray())")
            page.wait_for_timeout(400)
            assert child.evaluate("comparison.api.effects.particles.map(p=>p.m.position.asArray())")==positions, 'Paused effects must remain fixed'
        t=child.evaluate('comparison.time');page.wait_for_timeout(400)
        assert child.evaluate('comparison.time')==t
        page.screenshot(path=f'/tmp/comparison-{engine}-interior.png')
        page.locator('#pause').click()
        page.locator('#motion').select_option('run')
        child.wait_for_function('comparison.state.motion === "run"')
        page.locator('#preset').select_option('soldier')
        page.locator('#cutaway').select_option('exterior')
        page.locator('#reset').click()
        page.wait_for_timeout(800)
        pose=child.evaluate('comparison.api.capture()')
        page.wait_for_timeout(600)
        assert child.evaluate('comparison.api.capture()')!=pose, 'Stationary character must animate'
        page.screenshot(path=f'/tmp/comparison-{engine}-soldier.png')
        with page.expect_download(timeout=120000 if engine=='webgpu' else 30000) as download:page.locator('#capture').click()
        assert download.value.suggested_filename==f'{engine}-soldier.png'
        page.locator('#preset').select_option('hero')
        page.locator('#motion').select_option('walk')
    assert not errors,errors
    assert not remote,remote
    print('PASS: selected engines load local assets, animate, cut away, pause, trigger effects and capture.')
    browser.close()
