"""Integration checks for the isolated three-engine visual study.
Requires a running server: python3 server.py --port 8002.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--engine',choices=['babylon','playcanvas','three'])
args=parser.parse_args()

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/snap/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':900},accept_downloads=True)
    errors=[];remote=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:print('CONSOLE',m.type,m.text[:400]) if m.type=='error' else None)
    page.on('request',lambda r:remote.append(r.url) if not r.url.startswith(('http://localhost:8002/','data:','blob:')) else None)
    page.goto('http://localhost:8002/comparison/')
    for engine in ([args.engine] if args.engine else ['babylon','playcanvas','three']):
        if engine!='babylon':page.locator(f'[data-engine="{engine}"]').click()
        page.locator('#status').wait_for(state='hidden',timeout=120000)
        frame=page.frame_locator('#view')
        child=page.frames[1]
        child.wait_for_function('window.comparison && window.comparison.time > .2',timeout=60000)
        print(engine,child.evaluate('({version:comparison.api.version,clips:comparison.api.clips,stats:comparison.api.stats()})'),flush=True)
        assert child.evaluate('comparison.api.clips.length')>0
        assert child.evaluate('document.querySelector("canvas").width === innerWidth && document.querySelector("canvas").height === innerHeight'), 'Mismatched render resolution'
        page.screenshot(path=f'/tmp/comparison-{engine}.png')
        page.locator('#preset').select_option('interior')
        page.locator('#cutaway').select_option('ground')
        child.wait_for_function('comparison.state.cutaway === "ground"')
        page.locator('#explosion').click()
        child.wait_for_function('comparison.effect?.kind === "explosion"')
        page.locator('#pause').click()
        child.wait_for_function('comparison.state.paused')
        t=child.evaluate('comparison.time');page.wait_for_timeout(400)
        assert child.evaluate('comparison.time')==t
        page.screenshot(path=f'/tmp/comparison-{engine}-interior.png')
        page.locator('#pause').click()
        page.locator('#motion').select_option('run')
        child.wait_for_function('comparison.state.motion === "run"')
        page.locator('#preset').select_option('soldier')
        page.locator('#cutaway').select_option('exterior')
        page.locator('#reset').click()
        page.wait_for_timeout(800)
        pose=child.evaluate('comparison.api.capture()')
        page.wait_for_timeout(600)
        assert child.evaluate('comparison.api.capture()')!=pose, 'Stationary character must animate'
        page.screenshot(path=f'/tmp/comparison-{engine}-soldier.png')
        with page.expect_download() as download:page.locator('#capture').click()
        assert download.value.suggested_filename==f'{engine}-soldier.png'
        page.locator('#preset').select_option('hero')
        page.locator('#motion').select_option('walk')
    assert not errors,errors
    assert not remote,remote
    print('PASS: selected engines load local assets, animate, cut away, pause, trigger effects and capture.')
    browser.close()
