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
        browser=p.chromium.launch(headless=True,executable_path='/snap/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1000});page.goto(base);page.wait_for_selector('#welcome[open]');page.locator('#welcome-name').fill('Campaign Tester');page.locator('#cookie-consent').check();page.locator('#welcome-form button').click();page.wait_for_function("document.querySelector('#landing')&&!document.body.classList.contains('busy')&&document.querySelector('#phase').textContent!=='CONNECTING'")
        assert page.locator('#landing').is_visible();assert page.locator('#landing').evaluate("e=>getComputedStyle(e).backgroundImage.includes('turn4turn-landing')")
        assert page.locator('.credits a').get_attribute('href')=='https://github.com/keuperj'
        page.locator('#campaign-mode').click();assert page.locator('#campaign-screen').is_visible();assert page.locator('.campaign-node').count()==10
        assert page.locator('#campaign-screen').evaluate("e=>getComputedStyle(e).backgroundImage.includes('turn4turn-campaign')")
        page.locator('#new-campaign').click();assert page.locator('.campaign-node.current').count()==1
        page.locator('.campaign-node.current').click();page.wait_for_selector('#preparation[open]');page.wait_for_function("!document.body.classList.contains('busy')")
        assert page.locator('.mission h1').text_content()=='Broken Arrow';assert page.locator('#mission-type').input_value()=='rescue'
        assert page.locator('.mission-options select:disabled').count()==5
        assert page.locator('#body-count').text_content()=='BODY COUNT · ENEMY 0 / FRIENDLY 0'
        progress=page.evaluate("JSON.parse(decodeURIComponent(document.cookie.split('; ').find(v=>v.startsWith('turn4turn_campaign=')).split('=')[1]))")
        assert progress['index']==0 and progress['activeSeed']==41001
        page.locator('[data-slot="s0:primary"]').click();page.locator('[data-choice="Shotgun"]').click();page.locator('#save-loadout').check();page.locator('#deploy').click();page.wait_for_function("!document.body.classList.contains('busy')")
        page.locator('#new').click();page.wait_for_selector('#preparation[open]');page.wait_for_function("!document.body.classList.contains('busy')")
        assert 'Shotgun' in page.locator('[data-slot="s0:primary"]').text_content()
        server.MAX_PLAYERS=1;other=browser.new_context();blocked=other.new_page();blocked.goto(base);blocked.wait_for_selector('#welcome[open]');blocked.locator('#welcome-name').fill('Late Player');blocked.locator('#cookie-consent').check();blocked.locator('#welcome-form button').click();blocked.wait_for_selector('#server-full:visible');assert 'Try again later' in blocked.locator('#server-full').text_content();other.close()
        browser.close();print('PASS campaign: landing art, ten-mission overview, new/resume persistence and configured launch.',flush=True)
finally:httpd.shutdown()
