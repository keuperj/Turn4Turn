"""Capture staged combat screenshots using the real game renderer and effects.

Run with .venv/bin/python tools/capture_readme.py (Playwright/Chromium required).
Unit placement and revealed terrain are staged for legible documentation images.
"""
import json
import math
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from playwright.sync_api import sync_playwright

OUTPUT=Path(__file__).resolve().parents[1]/'docs/screenshots'


class QuietHandler(server.Handler):
    def log_message(self,*_args):pass


def combat_state(theme):
    game=Game(41,theme,size=24,mission='eliminate')
    n=game.size
    # Exterior cutaways show the highest remaining surface at each coordinate.
    visible={}
    for x,y,z in sorted(game.surfaces):
        visible[x,y]=max(z,visible.get((x,y),0))
    open_cells=[(x,y,z) for (x,y),z in visible.items() if (x,y,z) not in game.blocked and (theme=='factory' or z==0)]
    cx=game.scenery.get('apron_x',game.road_x) if theme=='airport' else n/2
    cy=n/2
    wanted=[(cx-3,cy+5),(cx,cy+6),(cx+3,cy+5),(cx+5,cy+3),
            (cx-3,cy-4),(cx,cy-5),(cx+3,cy-3),(cx+5,cy-5)]
    units=game.alive('soldier')[:4]+game.alive('alien')[:4]
    used=set()
    for unit,(tx,ty) in zip(units,wanted):
        cell=min((p for p in open_cells if p not in used),key=lambda p:(p[0]-tx)**2+(p[1]-ty)**2)
        used.add(cell);unit.update(x=cell[0],y=cell[1],z=cell[2],stance='kneeling' if unit['id']=='s1' else 'standing',facing=0 if unit['team']=='soldier' else math.pi)
    game.units=units;game.init_fog()
    state=game.state()
    state.update(units=units,buildings=game.buildings,props=game.props,tiles=game.tiles,
                 heights=game.heights,surfaces=sorted(game.surfaces),walls=list(game.walls.values()),
                 portals=game.portals,stairs=game.stairs,ladders=game.ladders,
                 fog=dict(visible=sorted(game.surfaces),explored=sorted(game.surfaces)))
    blast=min((p for p in open_cells if p not in used),key=lambda p:(p[0]-cx)**2+(p[1]-(cy-1))**2)
    return state,dict(type='blast',kind='grenade',unit='s0',x=blast[0],y=blast[1],z=blast[2],radius=3)


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
            base=f'http://127.0.0.1:{httpd.server_port}'
            landing=browser.new_page(viewport=dict(width=1600,height=1000),device_scale_factor=1)
            landing.goto(base+'/')
            landing.wait_for_function("['pass','fail'].includes(document.documentElement.dataset.gpuTest)")
            landing.evaluate('document.fonts.ready')
            landing.screenshot(path=str(OUTPUT/'landing.png'),full_page=True)
            landing.close();print('Captured landing page',flush=True)
            for theme in ('airport','factory','farm'):
                page=browser.new_page(viewport=dict(width=1600,height=1200),device_scale_factor=1)
                page.set_default_timeout(120000);errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                state,event=combat_state(theme)
                # Feed the staged mission through the real app so every menu,
                # squad card, minimap and equipment control matches the scene.
                page.route('**/api/state',lambda route,request,state=state:route.fulfill(
                    content_type='application/json',body=json.dumps(state)))
                response=page.request.post(base+'/api/session',data=dict(consent=True,username='Screenshot capture'))
                assert response.ok,response.text()
                page.goto(base+'/?mode=single&renderer=webgl')
                page.wait_for_selector('#attack-mode')
                page.wait_for_function("!document.body.classList.contains('busy')&&!document.querySelector('dialog[open]')")
                page.locator('#view-level').select_option('exterior')
                page.locator('#attack-mode').click()
                page.evaluate('''async()=>{
                  const {battlefield}=await import('/app.js');window.field=battlefield;
                  await field.ready;field.engine.stopRenderLoop();
                  if(field.transport.failures.length||field.background.failures.length)throw Error('Missing screenshot assets');
                  field.controls.target.set(11.5,1.7,11.5);
                  if(field.state.theme==='farm')field.camera.position.set(16,32,41);
                  else field.camera.position.set(34,30,39);
                  field.controls.update();field.background.atmosphere();
                  field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame();
                }''')
                page.wait_for_function('field.nativeScene.isReady()')
                page.wait_for_function("[...document.images].every(image=>image.complete)")
                page.evaluate('''event=>{
                  field.tween=async(duration,update)=>{update(.32);window.captureReady=true;await new Promise(()=>{});};
                  field.animate([event]);
                }''',event)
                page.wait_for_function('window.captureReady===true')
                page.evaluate('window.scrollTo(0,0);field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame()')
                assert page.locator('#squad .soldier').count()==4
                assert page.locator('#details').is_visible() and page.locator('#end').is_visible()
                page.screenshot(path=str(OUTPUT/f'{theme}-combat.jpg'),type='jpeg',quality=88,full_page=True)
                assert not errors,errors
                print('Captured full interface:',theme,flush=True);page.close()
            browser.close()
    finally:httpd.shutdown();httpd.server_close()


if __name__=='__main__':main()
