"""Verify statistics cookies, deduplication, trimming, reloads and navigation."""
import sys,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    def log_message(self,*args):pass

httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{httpd.server_port}')
        page.wait_for_function("document.querySelector('#statistics-mode').onclick!==null")
        page.locator('#statistics-mode').click()
        assert 'Complete your first mission' in page.locator('#statistics-content').inner_text()
        page.locator('#statistics-home').click()
        page.evaluate('''async()=>{
          const m=await import('/statistics.js');
          document.cookie='turn4turn_name=Test%20Player; Path=/';
          const state={status:'victory',mission:{label:'Test <mission>'},theme:'woods',difficulty:'easy',summary:Object.fromEntries(Object.keys(m.fields).map(k=>[k,2]))};
          for(let i=0;i<40;i++){state.summary.id=String(i);m.recordMission(state);m.recordMission(state);}
          const s=m.loadStatistics();if(s.count!==40||s.totals[0]!==80||s.history.length>20)throw Error('Bad totals or deduplication');
          if(document.cookie.split('; ').find(c=>c.startsWith('turn4turn_statistics=')).length>3800)throw Error('Cookie too large');
        }''')
        page.reload();page.locator('#statistics-mode').click()
        assert page.locator('#statistics-name').inner_text()=='Test Player'
        assert '40 missions completed' in page.locator('#statistics-content').inner_text()
        assert 'Test <mission>' in page.locator('.history-table').inner_text()
        page.locator('#statistics-home').click();assert page.locator('#landing').is_visible()
        page.evaluate("document.cookie='turn4turn_statistics=broken; Path=/'")
        page.locator('#statistics-mode').click()
        assert '0 missions completed' in page.locator('#statistics-content').inner_text()
        assert not errors,errors
        browser.close();print('PASS statistics persistence, deduplication, history limits, escaping, navigation and malformed cookies')
finally:httpd.shutdown();httpd.server_close()
