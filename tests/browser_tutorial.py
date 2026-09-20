"""Play the tutorial through real UI controls and projected battlefield clicks."""
import sys
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    def log_message(self,*args):pass


def main():
    """Verify onboarding, all lessons, resume, restart, completion and statistics."""
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{httpd.server_port}'
    try:
        with sync_playwright() as p:
            flags=['--no-sandbox','--disable-webgpu','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader']
            browser=p.chromium.launch(headless=True,args=flags)
            page=browser.new_page(viewport={'width':1500,'height':1100});page.set_default_timeout(120000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base);page.locator('#tutorial-mode').click()
            page.locator('#welcome-name').fill('Tutorial Tester');page.locator('#cookie-consent').check();page.locator('#welcome-form button').click()
            def ready(step):
                page.wait_for_function("step=>!document.body.classList.contains('busy')&&document.querySelector('#tutorial-progress').textContent.includes('STEP '+step+' OF')",arg=step)
                page.wait_for_selector('#mission-loading',state='hidden')
                page.evaluate("async()=>{window.f=(await import('/app.js')).battlefield;}")
                print('Ready step',step,flush=True)
            def target(x,y,unit=False):
                page.locator('#tutorial-focus').click()
                point=page.evaluate('''({x,y,unit})=>{
                  f.controls.update();f.camera.updateMatrixWorld();f.camera.updateProjectionMatrix();const B=BABYLON,c=f.engine.getRenderingCanvas(),r=c.getBoundingClientRect();
                  const p=B.Vector3.Project(new B.Vector3(x,unit?.8:.04,y),B.Matrix.Identity(),f.camera.native.getViewMatrix().multiply(f.camera.native.getProjectionMatrix()),f.camera.native.viewport.toGlobal(f.engine.getRenderWidth(),f.engine.getRenderHeight()));
                  const pixel={x:r.x+p.x*r.width/f.engine.getRenderWidth(),y:r.y+p.y*r.height/f.engine.getRenderHeight()};return pixel;
                }''',dict(x=x,y=y,unit=unit))
                print('Click',x,y,point,flush=True)
                page.mouse.click(point['x'],point['y']);page.wait_for_function("!document.body.classList.contains('busy')")
                assert 'PREVIEW' in page.locator('#message').inner_text(),page.locator('#message').inner_text()
                page.mouse.dblclick(point['x'],point['y'])
            ready(1)
            assert not page.locator('#preparation').is_visible()
            assert page.locator('#move-mode').evaluate("e=>e.classList.contains('tutorial-highlight')")
            assert page.locator('#end').is_disabled()
            target(6,15);ready(2)
            # Reopen with the saved profile to test resume while releasing the
            # software renderer's GPU resources before starting another scene.
            saved=page.context.storage_state();browser.close()
            browser=p.chromium.launch(headless=True,args=flags)
            page=browser.new_page(viewport={'width':1500,'height':1100},storage_state=saved);page.set_default_timeout(120000)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/?mode=tutorial');ready(2)
            page.locator('#attack-mode').click();target(6,10,True);ready(3)
            page.locator('#end').click();ready(4)
            page.locator('#reload').click();ready(5)
            page.locator('[data-weapon="M9"]').click();ready(6)
            target(10,13,True);ready(7)
            page.locator('#end').click();ready(8)
            page.locator('[data-weapon="Frag grenade"]').click();ready(9)
            page.screenshot(path='/tmp/tutorial.jpg',type='jpeg',quality=80)
            target(11,10,True)
            page.wait_for_selector('#tutorial-play');page.wait_for_function("!document.body.classList.contains('busy')")
            assert 'Training complete' in page.locator('#outcome').inner_text()
            assert not page.locator('#tutorial-guide').is_visible()
            assert not any(c['name']=='turn4turn_statistics' for c in page.context.cookies())
            page.locator('#tutorial-replay').click();ready(1)
            page.locator('#tutorial-exit').click();assert page.locator('#landing').is_visible()
            page.locator('#tutorial-mode').click();ready(1)
            target(6,15);ready(2)
            page.locator('#tutorial-restart').click();ready(1)
            page.locator('#tutorial-exit').click();page.locator('#single-game').click()
            page.wait_for_selector('#preparation[open]')
            assert not page.locator('#tutorial-guide').is_visible()
            assert not errors,errors
            browser.close();print('PASS real tutorial clicks, lesson progression, previews, resume, replay, restart, exit, normal mission and statistics isolation')
    finally:httpd.shutdown();httpd.server_close()


if __name__=='__main__':main()
