"""Browser regression for hover-only openings/ladders and smoke navigation."""
import copy
import sys
import threading
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game
import test_fog
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    def log_message(self,*args):pass
httpd=HTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{httpd.server_port}'
g=Game(41,'urban');g.explored=set(g.surfaces)
g.known_buildings={b['id']:copy.deepcopy(b) for b in g.buildings}
g.known_walls={key:copy.deepcopy(w) for key,w in g.walls.items()}
server.game=g
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/snap/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1050});page.set_default_timeout(60000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/?mode=single');page.wait_for_selector('#move-mode');page.wait_for_function("!document.body.classList.contains('busy')")
        def aim(point,offset=(7,4,7),view='exterior',building='b0'):
            page.locator('#map').scroll_into_view_if_needed()
            page.evaluate('''async args=>{const {battlefield:b}=await import('/app.js');b.testWorld??={...b.state};const building=b.testWorld.buildings.find(v=>v.id===args.building);b.state={...b.testWorld,props:[],buildings:[building],walls:b.testWorld.walls.filter(w=>w.building===args.building),ladders:b.testWorld.ladders.filter(([a,d])=>d[0]>=building.x&&d[0]<building.x+building.width&&d[1]>=building.y&&d[1]<building.y+building.depth)};b.setView(args.view);b.sync(b.state,b.selected,null,'move',null);b.controls.target.set(...args.point);b.camera.position.set(...args.point.map((v,i)=>v+args.offset[i]));b.controls.update();b.camera.updateMatrixWorld();}''',dict(point=point,offset=offset,view=view,building=building))
        def hover_point(point):
            pixel=page.evaluate('''async point=>{const {battlefield:b}=await import('/app.js');const T=await import('/rendering.js');b.camera.updateMatrixWorld();const v=new T.Vector3(...point).project(b.camera),r=b.canvas.getBoundingClientRect();return [r.left+(v.x+1)*r.width/2,r.top+(1-v.y)*r.height/2];}''',point)
            page.mouse.move(*pixel)
        def hover_key():return page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.hoverKey}")
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let n=0;b.terrain.traverse(o=>{if(o.userData.hoverFor&&o.visible)n++});return n}")==0
        exterior_offset={'north':(0,4,-8),'south':(0,4,8),'west':(-8,4,0),'east':(8,4,0)}
        door=next(p for p in g.portals if p['building']=='b0' and p['kind']=='door' and p['side']!='interior')
        point=[(door['a'][0]+door['b'][0])/2,1.3,(door['a'][1]+door['b'][1])/2]
        aim(point,exterior_offset[door['side']]);hover_point(point)
        assert hover_key()=='portal:'+door['id'],hover_key()
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let n=0;b.terrain.traverse(o=>{if(o.userData.hoverFor&&o.visible&&o.material.depthTest)n++});return n}")==1
        page.mouse.move(5,5);assert hover_key() is None
        window=next(p for p in g.portals if p['building']=='b0' and p['kind']=='window' and p['side']!='interior' and p['a'][2]==1)
        point=[(window['a'][0]+window['b'][0])/2,4.6,(window['a'][1]+window['b'][1])/2]
        aim(point,exterior_offset[window['side']]);hover_point(point)
        assert hover_key()=='portal:'+window['id'],hover_key()
        page.screenshot(path='/tmp/ground-control-upper-window.png')
        # Same interior rung: exterior wall occludes both picking and label; cutaway exposes it.
        a,b=next((a,b) for a,b in g.ladders if a[:2]==b[:2])
        point=[a[0]-.30,a[2]*3+1.1,a[1]];key='ladder:'+','.join(map(str,a))+':'+','.join(map(str,b))
        aim(point,(5,8,5),building=g.building_at(*a)['id']);hover_point(point)
        assert hover_key()!=key,hover_key()
        aim(point,(5,8,5),'0',building=g.building_at(*a)['id']);hover_point(point)
        assert hover_key()==key,hover_key()
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let good=true;b.terrain.traverse(o=>{if(o.userData.transition?.startsWith('ladder:'))good&&=o.material.depthTest});return good}")
        page.screenshot(path='/tmp/ground-control-multiroom.png')
        # Native single-click preview / double-click execution works on smoke-covered known tiles.
        g=test_fog.FogTests().field();server.game=g;g.smoke=[dict(x=14,y=26,z=0,radius=3,turns=3)];g.geometry_revision+=1;g.refresh_visibility()
        page.reload();page.wait_for_selector('#move-mode');page.wait_for_function("!document.body.classList.contains('busy')")
        page.locator('#map').scroll_into_view_if_needed()
        pixel=page.evaluate('''async()=>{const {battlefield:b}=await import('/app.js');const T=await import('/rendering.js');b.camera.updateMatrixWorld();const v=new T.Vector3(14,.1,25).project(b.camera),r=b.canvas.getBoundingClientRect();return [r.left+(v.x+1)*r.width/2,r.top+(1-v.y)*r.height/2];}''')
        page.mouse.click(*pixel);page.wait_for_function("!document.body.classList.contains('busy')")
        assert 'PREVIEW' in page.locator('#message').text_content()
        page.mouse.dblclick(*pixel,delay=60);page.wait_for_function("!document.body.classList.contains('busy')")
        assert g.position(g.units[0])==(14,25,0)
        assert not errors,errors
        print('PASS browser interiors: hover doors/windows/ladders, upper windows, wall occlusion, multi-room rendering and smoke double-click movement.',flush=True)
        browser.close()
finally:httpd.shutdown()
