"""WebGL integration: visual equipment, previews, minimap, effects, structure picks."""
import argparse
import random
import sys
import threading
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game, WEAPONS
from playwright.sync_api import sync_playwright


def fixture():
    g=Game(41,'urban');n=g.size
    g.tiles=[['grass']*n for _ in range(n)];g.heights=[[0]*n for _ in range(n)]
    g.surfaces={(x,y,0) for y in range(n) for x in range(n)}
    g.walls={};g.buildings=[];g.props=[];g.portals=[];g.ladders=[];g.stairs=[];g.blocked=set()
    for i,u in enumerate(g.alive('soldier')):u.update(x=14+i*2,y=27,z=0)
    for i,u in enumerate(g.alive('alien')):u.update(x=i+1,y=1,z=0,stance='standing')
    g.alive('alien')[0].update(x=14,y=23,hp=30,max_hp=30)
    for name in ['Smoke grenade','Demolition charge']:
        g.units[1]['inventory'][name]=dict(ammo=WEAPONS[name]['capacity'],reserve=0)
    g.units=[u for u in g.units if u['team']!='civilian']
    g.geometry_revision+=1;g._los_cache.clear();g.init_fog();g.rng=random.Random(1)
    return g

parser=argparse.ArgumentParser();parser.add_argument('--browser',default='/snap/bin/chromium');args=parser.parse_args()
class QuietHandler(server.Handler):
    def log_message(self,*args):pass
httpd=HTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{httpd.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=args.browser,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'],timeout=20000)
        page=browser.new_page(viewport={'width':1440,'height':1050});page.set_default_timeout(45000)
        errors=[];requests=[]
        page.on('pageerror',lambda e:(errors.append(str(e)),print('BROWSER ERROR:',e,flush=True)))
        page.on('request',lambda r:requests.append(r.url))
        def ready():page.wait_for_function("!document.body.classList.contains('busy')")
        def click_point(x,y,z=0,height=.1,double=False):
            page.locator('#map').scroll_into_view_if_needed()
            point=page.evaluate('''async p=>{const {battlefield:b}=await import('/app.js');const T=await import('/rendering.js');b.camera.updateMatrixWorld();const r=b.canvas.getBoundingClientRect(),v=new T.Vector3(p.x,p.z*3+p.height,p.y).project(b.camera);return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};}''',dict(x=x,y=y,z=z,height=height))
            (page.mouse.dblclick(point['x'],point['y'],delay=60) if double else page.mouse.click(point['x'],point['y']));ready()
        server.game=Game(83,'urban',deployed=False)
        page.goto(base);page.wait_for_selector('#deploy');ready()
        assert not any('/software.js' in r or 'three.module' in r or 'OrbitControls.js' in r for r in requests)
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.engine instanceof BABYLON.Engine && b.characters.instances.size>0}")
        page.locator('#mission-theme').select_option('airport');ready()
        page.locator('#mission-size').select_option('24');ready()
        assert server.game.size==24 and server.game.theme=='airport'
        page.locator('#mission-size').select_option('40');ready()
        assert server.game.size==40
        page.locator('#mission-theme').select_option('urban');ready()
        page.locator('#mission-size').select_option('30');ready()
        for slot,name in [('s0:primary','Shotgun'),('s0:utility1','Medikit'),('s0:utility2','Demolition charge'),('s0:sidearm','M24 sniper')]:
            page.locator(f'[data-slot="{slot}"]').click()
            assert page.locator('[data-choice]').count()==12
            page.locator(f'[data-choice="{name}"]').click()
        assert page.locator('[data-slot="s0:primary"] img').get_attribute('src')=='/assets/shotgun.png'
        page.wait_for_function("[...document.querySelectorAll('#preparation img')].every(i=>i.complete&&i.naturalWidth>0)")
        page.screenshot(path='/tmp/ground-control-v6-loadout.png')
        page.set_viewport_size({'width':600,'height':900});page.screenshot(path='/tmp/ground-control-v6-mobile.png')
        page.set_viewport_size({'width':1440,'height':1050});page.locator('#deploy').click();ready()
        assert server.game.status=='active';assert server.game.units[0]['weapon']=='Shotgun'
        page.locator('#map').scroll_into_view_if_needed();page.screenshot(path='/tmp/ground-control-v6-city.png')
        page.locator('#armory').click();assert page.locator('#equipment-grid .catalog-item').count()==12
        page.wait_for_function("[...document.querySelectorAll('#equipment img')].every(i=>i.complete&&i.naturalWidth>0)")
        page.locator('#close-equipment').click()
        assert page.evaluate("[...document.querySelectorAll('button')].every(b=>b.title && (b.querySelector('svg,img,.item-art,.portrait')!==null))")
        # Minimap changes the camera, never unit positions or AP.
        before=server.game.position(server.game.units[0]);camera=page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.controls.target.toArray()}")
        page.locator('#minimap').click(position={'x':25,'y':25})
        assert camera!=page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.controls.target.toArray()}")
        assert before==server.game.position(server.game.units[0])
        server.game=fixture();page.reload();page.wait_for_selector('#move-mode');ready()
        page.locator('[data-unit="s2"]').click()
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.controls.target.distanceTo({x:18,y:0,z:27})}")<.001
        page.locator('[data-unit="s0"]').click()
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.controls.minDistance===2&&b.controls.maxDistance===220}")
        # Hover labels survive state refreshes and disappear on leaving the canvas.
        click_point(14,27,height=.8)
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let n=0;b.actors.traverse(o=>{if(o.userData.health&&o.visible)n++});return n}")==1
        page.mouse.move(5,5)
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let n=0;b.actors.traverse(o=>{if(o.userData.health&&o.visible)n++});return n}")==0
        # Public enemy movement is followed; a redacted impact cannot reveal its source.
        page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');const u=b.state.units.find(u=>u.team==='alien');await b.animate([{type:'move',unit:u.id,actor:u,origin:[14,23,0],x:15,y:23,z:0}],true)}")
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.controls.target.distanceTo({x:15,y:0,z:23})}")<.001
        page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');await b.animate([{type:'impact',unit:null,point:[14,27,0],hit:false}],true)}")
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.controls.target.distanceTo({x:15,y:0,z:23})}")<.001
        page.reload();page.wait_for_selector('#move-mode');ready()
        old=server.game.position(server.game.units[0]);click_point(12,25)
        assert 'PREVIEW' in page.locator('#message').text_content();assert server.game.position(server.game.units[0])==old
        page.keyboard.press('Escape');assert server.game.position(server.game.units[0])==old
        click_point(12,25,double=True);ready()
        assert server.game.position(server.game.units[0])==(12,25,0)
        page.locator('#auto-mode').click();ready();page.locator('#attack-mode').click();click_point(14,23,height=.8)
        assert 'PREVIEW' in page.locator('#message').text_content();assert server.game.units[0]['ammo']==6
        click_point(14,23,height=.8,double=True);ready();assert server.game.units[0]['ammo']==3
        assert page.evaluate("async()=>{const {actionAudio}=await import('/audio.js');return actionAudio.context.state}")=='running'
        page.locator('[data-unit="s1"]').click();page.locator('[data-weapon="Smoke grenade"]').click();ready()
        click_point(17,25,double=True);ready();assert server.game.smoke
        page.screenshot(path='/tmp/ground-control-v6-smoke.png')
        # Clicking a corpse selects its ground tile and movement waits for confirmation.
        server.game=fixture();server.game.alive('alien')[0].update(x=14,y=25,hp=0);page.reload();page.wait_for_selector('#move-mode');ready()
        click_point(14,25,double=True);ready();assert server.game.position(server.game.units[0])==(14,25,0)
        # Exposed vehicle mesh is clickable; attack preview includes its actual health.
        server.game=fixture();g=server.game;g.props=[dict(id='car',kind='car',x=12,y=23,width=2,depth=3,color='#ad9b6a')];g.init_structures();g.blocked=set(g.footprint(g.props[0]));g.geometry_revision+=1;g.init_fog()
        page.reload();page.wait_for_selector('#attack-mode');ready();page.locator('#attack-mode').click()
        click_point(12.5,24,height=.8)
        assert 'HP' in page.locator('#message').text_content()
        assert 'car' in page.locator('#message').text_content()
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let n=0;b.terrain.traverse(o=>{if(o.userData.health&&o.visible&&o.userData.structure==='car')n++});return n}")==1
        page.mouse.move(5,5)
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');let n=0;b.terrain.traverse(o=>{if(o.userData.health&&o.visible)n++});return n}")==0
        g.rng.randint=lambda a,b:1;click_point(12.5,24,height=.8,double=True);ready();assert g.props[0]['hp']<35
        page.locator('[data-unit="s1"]').click();page.locator('[data-weapon="RPG-7"]').click();ready()
        click_point(12.5,24,height=.8,double=True);ready();assert g.props[0]['destroyed']
        assert page.locator('#structure-target').count()==0
        # Free facing remains available at zero AP.
        server.game=fixture();g=server.game;g.units[0]['ap']=0
        page.reload();page.wait_for_selector('#face-mode');ready();page.locator('#face-mode').click();click_point(12,25)
        assert g.units[0]['ap']==0 and g.units[0]['facing']!=0
        # Double-click healing selects a teammate, never switches the selected fighter.
        server.game=fixture();g=server.game;g.units[1].update(x=15,hp=2)
        g.units[0]['inventory']['Medikit']=dict(ammo=2,reserve=0)
        page.reload();page.wait_for_selector('[data-weapon="Medikit"]');ready();page.locator('[data-weapon="Medikit"]').click();ready()
        click_point(15,27,height=.8);assert g.units[1]['hp']==2
        click_point(15,27,height=.8,double=True);ready();assert g.units[1]['hp']==8 and g.units[0]['ammo']==1
        # A slow preview response must not swallow the native double-click.
        import time
        page.route('**/api/preview',lambda route:(time.sleep(.3),route.continue_()))
        page.locator('[data-unit="s2"]').click();click_point(18,25,double=True);ready()
        assert g.position(g.units[2])==(18,25,0)
        page.unroute('**/api/preview')
        # Peeking animates an exposure and retreat; concealed sightings become gray memories.
        from test_fieldcraft import FieldcraftTests
        g,u,e=FieldcraftTests().corner();e.update(x=11,y=10);g.rng.randint=lambda a,b:11;server.game=g
        page.reload();page.wait_for_selector('[data-peek="9,9,0"]');ready();page.locator('[data-peek="9,9,0"]').click();ready()
        assert g.position(u)==(9,10,0) and g.state()['last_seen']
        page.locator('#view-level').select_option('0');ready()
        assert page.evaluate("async()=>{const {battlefield:b}=await import('/app.js');return b.actors.children.some(o=>o.userData.memory)}")
        page.screenshot(path='/tmp/ground-control-v7-peek.png')
        page.locator('[data-weapon="Frag grenade"]').click();ready()
        click_point(11,10,height=.7);assert 'CORNER THROW' in page.locator('#message').text_content()
        click_point(11,10,height=.7,double=True);ready();assert u['ammo']==1
        assert page.locator('#confirmation').count()==0
        assert not errors,errors
        print('PASS WebGL: four unrestricted equipment slots, hover health, sidebar camera focus, visible enemy tracking, expanded zoom bounds, mission configuration, 12 item images, visual loadouts, icons, minimap, double-click / cancel, automatic fire, smoke, corpses, structure clicks, healing, free facing, peeking, memories, corner throws.',flush=True)
        browser.close()
        disabled=p.chromium.launch(headless=True,executable_path=args.browser,args=['--no-sandbox','--disable-webgl','--disable-gpu'])
        blocked=disabled.new_page();blocked.goto(base);blocked.wait_for_function("document.getElementById('phase').textContent==='WEBGL REQUIRED'")
        assert 'WebGL' in blocked.locator('#message').text_content()
        disabled.close()
        print('PASS WebGL unavailable: clear startup message; no software fallback.',flush=True)
finally:httpd.shutdown();httpd.server_close()
