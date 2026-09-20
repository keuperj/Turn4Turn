"""Landing, campaign overview, persistence, and campaign mission launch."""
import sys
import threading
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from playwright.sync_api import sync_playwright


class QuietHandler(server.Handler):
    """Group automated checks for quiethandler behavior."""
    def log_message(self,*args):
        """Suppress HTTP access logging during tests."""
        pass


httpd=HTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{httpd.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-webgpu','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(120000);page.goto(base);page.wait_for_function("document.querySelector('#campaign-mode').onclick!==null")
        assert page.locator('#landing').is_visible();assert page.locator('#landing').evaluate("e=>getComputedStyle(e).backgroundImage.includes('turn4turn-landing')")
        assert page.locator('.credits a').get_attribute('href')=='https://github.com/keuperj'
        page.locator('#campaign-mode').click();page.wait_for_selector('#campaign-screen:visible');assert page.locator('#campaign-screen').is_visible();assert page.locator('.campaign-node').count()==10
        assert page.locator('#campaign-screen').evaluate("e=>getComputedStyle(e).backgroundImage.includes('campaign-easy')")
        assert page.locator('.campaign-choice').count()==3
        for difficulty,campaign_id in [('hard','operation-iron-tide'),('medium','operation-turning-point'),('easy','operation-first-light')]:
            page.locator('[data-campaign="'+campaign_id+'"]').click()
            assert page.locator('#campaign-screen').evaluate("e=>getComputedStyle(e).backgroundImage.includes('campaign-"+difficulty+"')")
            assert page.locator('.campaign-node').count()==10
            assert page.locator('.campaign-node:disabled').count()==9
        page.locator('#new-campaign').click();assert page.locator('.campaign-node.current').count()==1
        page.locator('.campaign-node.current').click();page.wait_for_selector('#welcome[open]');page.locator('#welcome-name').fill('Campaign Tester');page.locator('#cookie-consent').check();page.locator('#welcome-form button').click();page.wait_for_selector('#preparation[open]');page.wait_for_function("!document.body.classList.contains('busy')")
        assert page.locator('.mission h1').text_content()=='Open Fields';assert page.locator('#mission-type').input_value()=='eliminate'
        assert page.locator('.mission-options select:disabled').count()==5
        assert page.locator('#body-count').text_content()=='BODY COUNT · ENEMY 0 / FRIENDLY 0'
        progress=page.evaluate("JSON.parse(decodeURIComponent(document.cookie.split('; ').find(v=>v.startsWith('turn4turn_campaign=')).split('=')[1]))")
        assert progress['v']==2
        assert progress['campaigns']['operation-first-light']['activeSeed']==51001
        assert page.locator('#mission-size').input_value()=='40'
        assert page.locator('#mission-difficulty').input_value()=='easy'
        page.locator('[data-slot="s0:primary"]').click();page.locator('[data-choice="Shotgun"]').click();page.locator('#save-loadout').check();page.locator('#deploy').click();page.wait_for_function("!document.body.classList.contains('busy')")
        page.locator('#new').click();page.wait_for_selector('#preparation[open]');page.wait_for_function("!document.body.classList.contains('busy')")
        assert 'Shotgun' in page.locator('[data-slot="s0:primary"]').text_content()
        page.locator('#deploy').click();page.wait_for_function("!document.body.classList.contains('busy')")
        # Finish the isolated test encounter and exercise the real outcome/save path.
        for unit in server.game.units:
            if unit['team']=='alien':unit['hp']=0
        page.locator('#end').click();page.wait_for_function("!document.body.classList.contains('busy')")
        page.wait_for_selector('#outcome:not([hidden])')
        progress=page.evaluate("JSON.parse(decodeURIComponent(document.cookie.split('; ').find(v=>v.startsWith('turn4turn_campaign=')).split('=')[1]))")
        assert progress['campaigns']['operation-first-light']['index']==1
        assert progress['campaigns']['operation-first-light']['activeSeed'] is None
        page.locator('#again').click()
        assert page.locator('.campaign-node.complete').count()==1
        page.locator('[data-campaign="operation-iron-tide"]').click();page.locator('#new-campaign').click()
        page.reload();page.locator('#campaign-mode').click()
        assert page.locator('[data-campaign="operation-iron-tide"]').get_attribute('aria-pressed')=='true'
        page.locator('[data-campaign="operation-first-light"]').click()
        assert page.locator('#resume-campaign').is_visible()
        assert page.locator('.campaign-node.complete').count()==1
        page.set_viewport_size({'width':390,'height':844})
        assert page.locator('#campaign-screen .campaign-shell').evaluate('e=>e.scrollWidth<=innerWidth')
        page.screenshot(path='/tmp/campaign-mobile.png')
        page.set_viewport_size({'width':1440,'height':1000})
        page.screenshot(path='/tmp/campaign-desktop.png')
        # Legacy campaign progress becomes Medium, leaving Easy and Hard untouched.
        page.evaluate("document.cookie='turn4turn_campaign='+encodeURIComponent(JSON.stringify({id:'operation-turning-point',index:4,activeSeed:41005}))+'; Path=/'")
        page.reload();page.locator('#campaign-mode').click()
        assert page.locator('[data-campaign="operation-turning-point"]').get_attribute('aria-pressed')=='true'
        assert page.locator('.campaign-node.complete').count()==4
        assert page.locator('.campaign-node.current').get_attribute('data-campaign-mission')=='4'
        page.locator('[data-campaign="operation-first-light"]').click()
        assert page.locator('.campaign-node.complete').count()==0
        page.locator('[data-campaign="operation-turning-point"]').click()
        assert page.locator('.campaign-node.complete').count()==4
        server.MAX_PLAYERS=1;other=browser.new_context();blocked=other.new_page();blocked.goto(base);blocked.locator('#single-game').click();blocked.wait_for_selector('#welcome[open]');blocked.locator('#welcome-name').fill('Late Player');blocked.locator('#cookie-consent').check();blocked.locator('#welcome-form button').click();blocked.wait_for_selector('#server-full:visible');assert 'Try again later' in blocked.locator('#server-full').text_content();other.close()
        browser.close();print('PASS campaigns: three backgrounds, 30-mission overview, fixed launch, victory, independent saves, legacy migration, and mobile layout.',flush=True)
finally:httpd.shutdown()
