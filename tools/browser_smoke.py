"""Run genuine Chromium DOM/JS + genuine loopback HTTP API through a host bridge.

The execution environment blocks Chromium's own localhost navigation. The
bridge forwards browser fetch() to the real running stdlib server via Python;
no API response is synthesized. This is NOT native browser TCP, real hardware
or an accessibility certification. Synthetic examples only.

Run from project root: python tools/browser_smoke.py
"""
from __future__ import annotations
from pathlib import Path
import json, os, socket, subprocess, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'dmsg'/'web'
def _chromium_path(pw):
    # Portable: explicit override, then a system Chromium, then Playwright's own build.
    import os
    for cand in (os.environ.get('DMSG_CHROMIUM'),'/usr/bin/chromium'):
        if cand and Path(cand).is_file():
            return cand
    return pw.chromium.executable_path

server=subprocess.Popen([sys.executable,'-m','prototype.server'],cwd=ROOT/'dmsg',
                        env={**os.environ,'PYTHONPATH':str(ROOT/'dmsg'),'DMSG_MODEL_ENABLED':'0'},
                        stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)

def proxy_fetch(path,method='GET',body=None):
    if not isinstance(path,str) or not path.startswith('/api/') or method not in ('GET','POST'):
        return {'status':403,'body':json.dumps({'error':'BRIDGE_ROUTE_FORBIDDEN'})}
    data=body.encode('utf8') if method=='POST' and isinstance(body,str) else None
    req=urllib.request.Request('http://127.0.0.1:8765'+path,data=data,method=method,
                               headers={'Content-Type':'application/json'} if data is not None else {})
    try:
        with urllib.request.urlopen(req,timeout=5) as response:
            return {'status':response.status,'body':response.read(200001).decode('utf8')}
    except urllib.error.HTTPError as e:
        return {'status':e.code,'body':e.read(200001).decode('utf8')}

try:
    for _ in range(80):
        try:
            with socket.create_connection(('127.0.0.1',8765),timeout=.2):break
        except OSError:time.sleep(.1)
    else:raise RuntimeError('SERVER_DID_NOT_START')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=_chromium_path(p),headless=True,
                                  args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=*'])
        checks=[];errors=[]
        page=browser.new_page(viewport={'width':1280,'height':900},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.expose_function('__bridgeFetch',proxy_fetch)
        page.set_content((WEB/'paylock.html').read_text('utf8'))
        page.add_style_tag(content=(WEB/'style.css').read_text('utf8'))
        page.add_init_script('') # no network / cached harness dependencies
        page.evaluate('''() => { window.fetch=async (input,opts={})=>{
            const result=await window.__bridgeFetch(String(input),opts.method||'GET',opts.body||null);
            return new Response(result.body,{status:result.status,headers:{'Content-Type':'application/json'}});
        }; }''')
        page.add_script_tag(content=(WEB/'paylock.js').read_text('utf8'))
        page.wait_for_function("document.querySelectorAll('#pl-example option').length===6",timeout=10000)
        page.locator('#pl-example').select_option('ACCOUNT_CHANGE')
        page.locator('#pl-evaluate').click()
        page.wait_for_function("document.getElementById('pl-action').textContent.includes('보류')",timeout=10000)
        assert '계좌' in page.locator('#pl-reasons').inner_text()
        checks.append('paylock_account_change_hold')
        page.locator('#pl-verify').click()
        page.wait_for_function("document.getElementById('pl-action').textContent.includes('담당자 확인 보고')",timeout=10000)
        assert '실제 지급: 없음' in page.locator('#pl-case').inner_text()
        checks.append('paylock_simulated_two_person_report_no_payment')
        (ROOT/'internal/evidence').mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(ROOT/'internal/evidence/v46_browser_desktop.png'),full_page=True)
        page.locator('#pl-example').select_option('MATCH')
        page.locator('#pl-evaluate').click()
        page.wait_for_function("document.getElementById('pl-action').textContent.includes('내부 지급 검토 대기')",timeout=10000)
        assert page.locator('#pl-verify').is_disabled()
        checks.append('paylock_matching_request_never_payment')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'), 'MOBILE_HORIZONTAL_OVERFLOW'
        page.screenshot(path=str(ROOT/'internal/evidence/v46_browser_mobile.png'),full_page=True)
        checks.append('mobile_no_horizontal_overflow')
        assert not errors,errors
        browser.close()
        out={'status':'PASS','transport':'CHROMIUM_INPAGE_PYTHON_PROXY_TO_REAL_LOOPBACK_SERVER',
             'browser':'Chromium headless','checks':checks,'page_errors':errors,
             'limitations':['not direct browser localhost TCP','not independent real-device QA',
                            'fixtures only, not actual Zoro-1 inference']}
        (ROOT/'internal/evidence/v46_browser_smoke.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n','utf8')
        print(json.dumps(out,ensure_ascii=False))
finally:
    server.terminate()
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.kill()
