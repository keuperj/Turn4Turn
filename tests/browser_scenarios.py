"""Smoke-test all registered scenario modules and background recipes in Chromium."""
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from scenarios import registry
from scenarios.assets import model_catalog
from game import Game
from playwright.sync_api import sync_playwright


class QuietHandler(server.Handler):
    def log_message(self,*_args):pass


def main():
    httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
            page=browser.new_page();page.set_default_timeout(120000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.route('**/scenario-test',lambda route:route.fulfill(content_type='text/html',body='<canvas width="800" height="600"></canvas>'))
            page.goto(f'http://127.0.0.1:{httpd.server_port}/scenario-test')
            page.add_script_tag(url='/vendor/babylon.js');page.add_script_tag(url='/vendor/babylonjs.loaders.min.js')
            loaded=page.evaluate('''async()=>{
              const {Battlefield}=await import('/scene.js');
              window.field=await Battlefield.create(document.querySelector('canvas'),()=>{},()=>{});
              await field.ready;field.engine.stopRenderLoop();
              return {scenarios:[...field.scenarios.entries.keys()].sort(),models:field.transport.sources.size,failures:[...field.transport.failures,...field.background.failures]};
            }''')
            assert loaded==dict(scenarios=sorted(s.id for s in registry),models=len(model_catalog()['models']),failures=[]),loaded
            for scenario in registry:
                g=Game(41,scenario.id,size=24);state=g.state()
                state.update(buildings=g.buildings,props=g.props,walls=list(g.walls.values()),portals=g.portals,tiles=g.tiles,heights=g.heights,surfaces=sorted(g.surfaces),stairs=g.stairs,ladders=g.ladders,fog=dict(visible=sorted(g.surfaces),explored=sorted(g.surfaces)))
                result=page.evaluate('''state=>{
                  field.sync(state,null,null,'move');
                  const bg=field.background,root=bg.root,placements=JSON.stringify(bg.placements),meshes=root.getChildMeshes();
                  field.sync({...state,round:state.round+1},null,null,'move');
                  field.engine.beginFrame();field.nativeScene.render();field.engine.endFrame();
                  return {stable:bg.root===root&&JSON.stringify(bg.placements)===placements,
                    isolated:meshes.every(m=>!m.isPickable&&!m.metadata?.pickOwner),ground:meshes.some(m=>m.name==='background-ground')};
                }''',state)
                assert all(result.values()),(scenario.id,result)
                page.wait_for_function('field.nativeScene.isReady()')
                print('PASS',scenario.id,'renderer, props, background and retained updates',flush=True)
            assert not errors,errors
            browser.close()
    finally:httpd.shutdown();httpd.server_close()


if __name__=='__main__':main()
