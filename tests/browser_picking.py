"""Screen/grid picking and real move/fire previews at different display scales.
Run: .venv/bin/python tests/browser_picking.py [--webgpu] [--dpr 1|2]
"""
import argparse
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from test_fog import FogTests
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    def log_message(self,*_args):
        pass

PROJECT='''point=>{
 const B=BABYLON,e=b.engine,r=b.canvas.getBoundingClientRect();
 b.camera.updateMatrixWorld();b.camera.updateProjectionMatrix();
 const p=B.Vector3.Project(new B.Vector3(...point),B.Matrix.Identity(),
   b.camera.native.getViewMatrix().multiply(b.camera.native.getProjectionMatrix()),
   new B.Viewport(0,0,e.getRenderWidth(),e.getRenderHeight()));
 return {clientX:r.left+p.x/e.getRenderWidth()*r.width,clientY:r.top+p.y/e.getRenderHeight()*r.height};
}'''

def main(base,args):
    with sync_playwright() as p:
        flags=['--no-sandbox','--enable-unsafe-swiftshader']
        flags+=['--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--enable-unsafe-webgpu'] if args.webgpu else ['--use-gl=angle','--use-angle=swiftshader']
        browser=p.chromium.launch(headless=True,args=flags)
        page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=args.dpr)
        page.set_default_timeout(120000);errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.request.post(base+'/api/session',data={'consent':True,'username':'Picking Tester'})
        page.goto(base+'/?mode=single')
        page.wait_for_selector('#move-mode')
        page.wait_for_function("!document.body.classList.contains('busy')")
        page.evaluate("async()=>{window.b=(await import('/app.js')).battlefield;b.controls.target.set(14,0,25);b.camera.position.set(21,12,35);b.controls.update();}")
        assert page.evaluate('b.renderer')==('webgpu' if args.webgpu else 'webgl')
        page.locator('#map').scroll_into_view_if_needed()
        page.evaluate('()=>{window.projectPoint='+PROJECT+';}')
        # Native Babylon projection is independent of our picking adapter.
        # Exercise render scaling, a resized/offset/scrolled canvas, and floors.
        for width in [1440,1000]:
            page.set_viewport_size({'width':width,'height':1050})
            page.locator('#map').scroll_into_view_if_needed()
            for scale in [1,.8,1.5]:
                page.evaluate('scale=>{b.engine.setHardwareScalingLevel(scale);b.resize();}',scale)
                for x,y in [(14,25),(12,24),(16,26)]:
                    hit=page.evaluate('point=>b.pick(projectPoint(point))',[x,.04,y])
                    assert hit and (hit.get('x'),hit.get('y'),hit.get('z'))==(x,y,0),(args.dpr,scale,width,(x,y),hit)
                elevated=page.evaluate('''()=>{
                    const p=projectPoint([14,6.04,25]),r=b.canvas.getBoundingClientRect();
                    b.pointer.set((p.clientX-r.left)/r.width*2-1,1-(p.clientY-r.top)/r.height*2);
                    b.ray.setFromCamera(b.pointer,b.camera);
                    return b.ray.intersectTileLayers([2],new Set(['14,25,2'])).map(h=>h.object.userData);
                }''')
                assert elevated==[{'x':14,'y':25,'z':2}],elevated
        page.set_viewport_size({'width':1440,'height':1050})
        page.evaluate('b.engine.setHardwareScalingLevel(1/Math.min(devicePixelRatio,1.25));b.resize()')
        page.locator('#map').scroll_into_view_if_needed()
        def click(point,double=False):
            pixel=page.evaluate(PROJECT,point)
            if double:page.mouse.dblclick(pixel['clientX'],pixel['clientY'],delay=70)
            else:page.mouse.click(pixel['clientX'],pixel['clientY'])
        def preview(point,action):
            with page.expect_response(lambda r:r.url.endswith('/api/preview')) as response:
                click(point)
            payload=response.value.request.post_data_json
            expected={'x':point[0],'y':point[2],'z':0}
            assert payload['action']==action and all(payload[k]==v for k,v in expected.items()),payload
            result=response.value.json()
            assert all(result.get(k)==v for k,v in expected.items()),result
            page.wait_for_function("!document.body.classList.contains('busy')")
            marker=page.evaluate('b.overlay.children.at(-1).position.toArray()')
            assert abs(marker[0]-point[0])<.01 and abs(marker[2]-point[2])<.01,marker
        preview([14,.04,25],'move')
        assert server.game.position(server.game.units[0])==(14,28,0),'Preview must not move the soldier'
        with page.expect_response(lambda r:r.url.endswith('/api/action')):
            click([14,.04,25],True)
        page.wait_for_function("!document.body.classList.contains('busy')")
        assert server.game.position(server.game.units[0])==(14,25,0)
        page.click('#attack-mode');page.locator('#map').scroll_into_view_if_needed()
        ammo=server.game.units[0]['ammo']
        preview([16,.04,24],'attack')
        assert server.game.units[0]['ammo']==ammo,'Preview must not fire'
        with page.expect_response(lambda r:r.url.endswith('/api/action')):
            click([16,.04,24],True)
        page.wait_for_function("!document.body.classList.contains('busy')")
        assert server.game.units[0]['ammo']==ammo-1
        assert any(e['type']=='shot' and e['point']==[16,24,0] for e in server.game.events),server.game.events
        assert not errors,errors
        print(f'PASS {"WebGPU" if args.webgpu else "WebGL"} DPR {args.dpr}: scaled/resized picking, elevated floor, movement/fire previews and execution',flush=True)
        browser.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--webgpu',action='store_true');parser.add_argument('--dpr',type=float,default=2);args=parser.parse_args()
    server.game=FogTests().field()
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}',args)
    finally:httpd.shutdown();httpd.server_close()
