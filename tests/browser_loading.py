"""Landing stays asset-free; first mission loads once with live equipment cards."""
import asyncio
import sys
import threading
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from game import WEAPONS
from playwright.async_api import async_playwright

class QuietHandler(server.Handler):
    def log_message(self, *_args):
        pass

async def main(base):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page = await browser.new_page(viewport={'width':1280,'height':1000})
        page.set_default_timeout(120000)
        errors=[];requests=[];finished=set()
        page.on('pageerror',lambda e:(errors.append(str(e)),print('PAGE ERROR',e,flush=True)))
        page.on('request',lambda r:requests.append(r.url))
        page.on('requestfinished',lambda r:finished.add(r.url))
        await page.request.post(base+'/api/session',data={'consent':True,'username':'Loading Tester'})
        await page.goto(base,wait_until='domcontentloaded')
        await page.wait_for_function("document.querySelector('#single-game').onclick!==null")
        assert await page.locator('#landing').is_visible()
        assert not await page.locator('#mission-loading').is_visible()
        assert not any('/vendor/babylon' in u or '/assets/models/' in u or '/api/state' in u or '/api/audio' in u for u in requests),requests
        await page.click('#campaign-mode')
        await page.wait_for_selector('.campaign-node.current')
        assert not any('/vendor/babylon' in u or '/assets/models/' in u for u in requests)
        await page.click('#campaign-home')
        # Hold the engine download while checking carousel rotation and layout.
        async def slow_engine(route):
            preview=['items.png','m24.png','medikit.png','smoke-grenade.png','demolition-charge.png','shotgun.png']
            assert all(base+'/assets/'+name in finished for name in preview),finished
            await asyncio.sleep(6)
            await route.continue_()
        await page.route('**/vendor/babylon.js',slow_engine)
        print('PASS landing and campaign overview without assets',flush=True)
        await page.click('#single-game')
        await page.wait_for_selector('#loading-feature:not([hidden])')
        first=await page.locator('#loading-feature').get_attribute('data-item')
        text=await page.locator('#loading-feature').inner_text()
        assert f"{WEAPONS[first]['range']} tiles" in text,text
        await page.wait_for_function("first=>document.querySelector('#loading-feature').dataset.item!==first",arg=first)
        assert await page.locator('#loading-feature img').evaluate_all('(images)=>images.every(image=>image.complete&&image.naturalWidth>0)')
        await page.screenshot(path='/tmp/mission-loading-desktop.png')
        await page.set_viewport_size({'width':390,'height':844})
        await page.emulate_media(reduced_motion='reduce')
        assert await page.locator('#mission-loading').evaluate('(e)=>e.getBoundingClientRect().width<=innerWidth')
        assert await page.locator('.loading-item').evaluate('(e)=>getComputedStyle(e).animationName')=='none'
        await page.screenshot(path='/tmp/mission-loading-mobile.png')
        await page.wait_for_function("!document.body.classList.contains('busy')&&!document.querySelector('#mission-loading').open")
        assert await page.locator('#preparation').is_visible()
        assert await page.evaluate("async()=>!!(await import('/app.js')).battlefield")
        await page.set_viewport_size({'width':1280,'height':1000})
        await page.click('#deploy')
        await page.wait_for_function("!document.body.classList.contains('busy')&&!document.querySelector('#preparation').open")
        assert not await page.locator('#mission-loading').is_visible()
        # A second mission reuses both the engine and the loaded model containers.
        assets=Counter(u for u in requests if '/assets/models/' in u or '/vendor/babylon' in u)
        await page.click('#home');await page.click('#campaign-mode')
        await page.click('.campaign-node.current')
        await page.wait_for_function("!document.body.classList.contains('busy')&&!document.querySelector('#mission-loading').open")
        assert await page.locator('#preparation').is_visible()
        assert assets==Counter(u for u in requests if '/assets/models/' in u or '/vendor/babylon' in u)
        assert await page.locator('#loading-feature').is_hidden()
        assert not errors,errors
        print('PASS instant landing, preview images before engine, lazy assets, rotating authoritative stats, mobile/reduced motion, deployment and campaign reuse',flush=True)
        await browser.close()

if __name__=='__main__':
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:asyncio.run(main(f'http://127.0.0.1:{httpd.server_port}'))
    finally:httpd.shutdown();httpd.server_close()
