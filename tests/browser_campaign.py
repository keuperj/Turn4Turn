"""Landing, campaign overview, persistence, and campaign mission launch."""
import sys
import threading
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from playwright.sync_api import sync_playwright


class QuietHandler(server.Handler):
    def log_message(self,*args):pass


httpd=HTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{httpd.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/snap/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1000});page.goto(base);page.wait_for_function("document.querySelector('#landing')&&!document.body.classList.contains('busy')")
        assert page.locator('#landing').is_visible();assert page.locator('#landing').evaluate("e=>getComputedStyle(e).backgroundImage.includes('turn4turn-landing')")
        assert page.locator('.credits a').get_attribute('href')=='https://github.com/keuperj'
        page.locator('#campaign-mode').click();assert page.locator('#campaign-screen').is_visible();assert page.locator('.campaign-node').count()==10
        assert page.locator('#campaign-screen').evaluate("e=>getComputedStyle(e).backgroundImage.includes('turn4turn-campaign')")
        page.locator('#new-campaign').click();assert page.locator('.campaign-node.current').count()==1
        page.locator('.campaign-node.current').click();page.wait_for_selector('#preparation[open]');page.wait_for_function("!document.body.classList.contains('busy')")
        assert page.locator('.mission h1').text_content()=='Broken Arrow';assert page.locator('#mission-type').input_value()=='rescue'
        assert page.locator('.mission-options select:disabled').count()==5
        assert page.locator('#body-count').text_content()=='BODY COUNT · ENEMY 0 / FRIENDLY 0'
        progress=page.evaluate("JSON.parse(localStorage.getItem('turn4turn-campaign'))")
        assert progress['index']==0 and progress['activeSeed']==41001
        browser.close();print('PASS campaign: landing art, ten-mission overview, new/resume persistence and configured launch.',flush=True)
finally:httpd.shutdown()
