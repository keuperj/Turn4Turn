"""Real browser audio checks: decoding, variants, ambience lifecycle and fallback."""
import sys
import threading
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from game import Game
from audio_assets import CATALOG
from playwright.sync_api import sync_playwright

class QuietHandler(server.Handler):
    """Group automated checks for quiethandler behavior."""
    def log_message(self,*args):
        """Suppress HTTP access logging during tests."""
        pass

httpd=HTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
server.game=Game(41,'woods')
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/snap/bin/chromium',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(60000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        base=f'http://127.0.0.1:{httpd.server_port}'
        page.goto(base+'/?mode=single');page.wait_for_selector('#welcome[open]');page.locator('#welcome-name').fill('Audio Tester');page.locator('#cookie-consent').check();page.locator('#welcome-form button').click();page.wait_for_selector('#move-mode');page.wait_for_function("!document.body.classList.contains('busy')")
        page.keyboard.press('Shift')
        result=page.evaluate('''async()=>{
          const {actionAudio:a,soundAction}=await import('/audio.js');await a.unlock();await a.preload();
          const {battlefield:b}=await import('/app.js');await b.animate([{type:'rocket_launch',point:[14,20,0],target:[14,16,0]}]);
          const failures=[];for(const [name,samples] of Object.entries(a.manifest))for(const sample of samples)if(!await a.buffer(sample.url))failures.push(name);
          const mapping=[soundAction({type:'shot',weapon:'M9'}),soundAction({type:'blast',kind:'charge'}),soundAction({type:'portal',kind:'window',open:false}),soundAction({type:'hide'})];
          const original=a.manifest.move;a.manifest.move=[a.manifest.shot_m4a1[0],a.manifest.shot_m9[0]];
          const choices=Array.from({length:20},()=>a.choose('move').url);a.manifest.move=original;
          await a.play({type:'shot',weapon:'M4A1',origin:[14,20,0]});
          const playing=a.voices.size;
          a.setVolume(.2);const volume=a.volume;
          const version=a.ambientVersion;a.stopAmbience();a.theme='factory';a.startAmbience();
          await new Promise(r=>setTimeout(r,100));
          const ambience=a.ambientVoices.size;
          a.setEnabled(false);await new Promise(r=>setTimeout(r,25));
          const muted=a.voices.size===0&&a.ambientVoices.size===0;
          a.manifest.impact=[{url:'/sounds/missing_999.wav',placeholder:false}];const fallback=await a.sample('impact');
          a.setEnabled(true);await a.unlock();await a.prepare({seed:99,theme:'urban',status:'loadout'});
          return {groups:Object.keys(a.manifest).length,failures,mapping,choices,playing,volume,ambience,muted,fallback:fallback.sample.placeholder,loadoutQuiet:!a.ambientRunning&&a.ambientVoices.size===0};
        }''')
        assert result['groups']==len(CATALOG),result
        assert not result['failures'],result
        assert result['mapping']==['shot_m9','blast_charge','window_close',None],result
        assert all(a!=b for a,b in zip(result['choices'],result['choices'][1:])),result
        assert result['playing']>0 and result['ambience']>0,result
        assert result['muted'] and result['fallback'] and result['loadoutQuiet'],result
        # No server endpoint may expose the generation credentials or metadata.
        for path in ['/.env','/sounds/_sources.json','/sounds/../.env']:
            assert page.request.get(base+path).status==404,path
        assert not errors,errors
        print(f'PASS browser audio: {result["groups"]} groups decoded; variants, event mapping, ambience, mute, missing-file fallback, private files.',flush=True)
        browser.close()
finally:httpd.shutdown()
