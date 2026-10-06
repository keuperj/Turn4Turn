"""Approach stairs from an upper floor, descend, and climb through the real UI/API."""
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from browser_background import QuietHandler
from playwright.sync_api import sync_playwright


def main(base):
    g=server.game=Game(41,'factory')
    a,d=g.stairs[-1]
    u=g.units[0]
    adjacent=next((d[0]+dx,d[1]+dy,d[2]) for dx,dy in [(1,0),(0,1),(-1,0),(0,-1)] if (d[0]+dx,d[1]+dy,d[2]) in g.surfaces-g.blocked)
    u.update(x=adjacent[0],y=adjacent[1],z=adjacent[2],ap=20)
    for other in g.units[1:]:other.update(x=0,y=g.size-1,z=0)
    g.init_fog()
    hit=dict(transition='stairs:test',ends=[a,d])
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page();page.set_default_timeout(120000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.request.post(base+'/api/session',data={'consent':True,'username':'Factory Access Tester'})
        page.goto(base+'/?mode=single&renderer=webgl')
        page.wait_for_function("!document.body.classList.contains('busy')&&document.querySelector('#move-mode')")
        page.evaluate("async()=>{window.b=(await import('/app.js')).battlefield;b.engine.stopRenderLoop();}")
        with page.expect_response(lambda response:response.url.endswith('/api/preview')) as response:
            page.evaluate('hit=>b.onPick(hit,false)',hit)
        payload=response.value.request.post_data_json
        assert (payload['x'],payload['y'],payload['z'])==d,payload
        assert response.value.ok,response.value.text()
        page.wait_for_function("!document.body.classList.contains('busy')")
        # First approach the upper landing, then descend and climb back up.
        for destination in (d,a,d):
            with page.expect_response(lambda response:response.url.endswith('/api/action')) as response:
                page.evaluate('hit=>b.onPick(hit,true)',hit)
            assert response.value.ok,response.value.text()
            page.wait_for_function("!document.body.classList.contains('busy')")
            assert g.position(u)==destination,(g.position(u),destination)
        assert not errors,errors
        browser.close()
        print('PASS upstairs stair approach, descent, and ascent through UI and server',flush=True)


if __name__=='__main__':
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:main(f'http://127.0.0.1:{httpd.server_port}')
    finally:httpd.shutdown();httpd.server_close()
