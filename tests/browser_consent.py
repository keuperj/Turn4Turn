"""Verify consent UI across reloads, browser restarts, expired sessions and capacity.

The mission response is stopped after session establishment so this UI regression
needs no renderer or assets; real session endpoints and browser cookies are used.
"""
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from playwright.sync_api import sync_playwright


class QuietHandler(server.Handler):
    def log_message(self,*_args):pass


def main():
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{httpd.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            errors=[]

            def page_for(context):
                page=context.new_page();page.set_default_timeout(30000)
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.route('**/api/new',lambda route:route.fulfill(status=400,content_type='application/json',body='{"error":"Session established; stop before rendering."}'))
                return page

            def start(page):
                page.goto(base)
                page.wait_for_function("document.querySelector('#single-game').onclick!==null")
                page.evaluate('''()=>{
                  window.consentShown=false;
                  const dialog=document.querySelector('#welcome');
                  new MutationObserver(()=>{if(dialog.open)window.consentShown=true;}).observe(dialog,{attributes:true,attributeFilter:['open']});
                }''')
                page.locator('#single-game').click()

            def accepted_without_dialog(page):
                page.wait_for_selector('#startup-error:visible')
                assert 'Session established' in page.locator('#startup-error').text_content()
                assert not page.evaluate('window.consentShown')
                assert not page.locator('#welcome').evaluate('dialog=>dialog.open')

            context=browser.new_context();page=page_for(context)
            start(page);page.wait_for_selector('#welcome[open]')
            page.locator('#welcome-name').fill('Returning Player')
            page.locator('#cookie-consent').check();page.locator('#welcome-form button').click()
            page.wait_for_selector('#startup-error:visible')
            uid=next(c['value'] for c in context.cookies() if c['name']==server.USER_COOKIE)
            session=server.registry.sessions[uid]
            start(page);accepted_without_dialog(page)
            assert server.registry.sessions[uid] is session

            saved=context.storage_state();context.close()
            context=browser.new_context(storage_state=saved);page=page_for(context)
            start(page);accepted_without_dialog(page)
            server.registry.sessions[uid].last_seen=time.monotonic()-server.SESSION_TIMEOUT-1
            start(page);accepted_without_dialog(page)
            assert server.registry.sessions[uid] is not session

            server.registry=server.SessionRegistry()
            start(page);accepted_without_dialog(page)
            assert server.registry.sessions[uid].username=='Returning Player'

            server.registry=server.SessionRegistry();server.MAX_PLAYERS=1
            server.registry.create('Other Player')
            start(page);page.wait_for_selector('#server-full:visible')
            assert not page.evaluate('window.consentShown')
            server.registry.sessions.clear()
            start(page);accepted_without_dialog(page)

            context.clear_cookies();start(page);page.wait_for_selector('#welcome[open]')
            assert page.evaluate('window.consentShown')
            assert not errors,errors
            browser.close()
            print('PASS first consent, reload, saved browser profile, timeout, restart, capacity and cleared cookies',flush=True)
    finally:httpd.shutdown();httpd.server_close()


if __name__=='__main__':main()
