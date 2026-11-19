"""Runtime smoke test for the v4.6 apps on this host (Linux x64 + Chromium).

  * starts the compiled Linux desktop binary and kev-shaped stub servers (documented
    public fields only: answers/type/noul/probabilities; no 'model' echo unless asked);
  * checks the HTTP security boundary and every model-relay failure path;
  * drives the real UI in Chromium over HTTP (desktop host) and file:// (standalone),
    light/dark, desktop/mobile viewports; checks results, console errors and layout overflow;
  * saves screenshots and internal/evidence/v47_app_smoke.json.
Windows/macOS binaries and the mobile projects are NOT executed here.
Usage: python tools/app_smoke.py
"""
from __future__ import annotations
import json, socket, subprocess, sys, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / 'apps/dist/desktop/linux-x64/dmsg-desktop'
WEB = ROOT / 'apps/dist/web'
EVD = ROOT / 'internal/evidence'
SHOTS = EVD / 'v47_ui'


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def stub(mode):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if mode == 'slow': time.sleep(2.5)
            text = req['state']
            act = 'transfer' if '송금' in text or '이체' in text else 'none'
            speech = 'negated_or_warning' if '하지 마' in text else 'direct_request'
            ans = {}
            for k, q in req['questions'].items():
                if q['type'] == 'noul': ans[k] = {'type': 'noul', 'noul': 0.2}
                else:
                    opts = list(q['criteria']); win = act if k == 'q_action' else speech if k == 'q_speech' else opts[1]
                    p = {o: 0.08 / (len(opts) - 1) for o in opts}; p[win] = 0.92; ans[k] = {'type': q['type'], 'probabilities': p}
            body = {'answers': ans}
            if mode == 'echo_bad': body['model'] = 'other-model'
            raw = b'{"answers":{},"answers":{}}' if mode == 'dup' else json.dumps(body).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(raw)))
            try:
                self.end_headers(); self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass  # client timed out first (the timeout case)
    srv = ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def call(base, path, body=None, headers=None):
    h = {'Content-Type': 'application/json'}; h.update(headers or {})
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(), headers=h, method='GET' if body is None else 'POST')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=10) as r: return r.status, json.loads(r.read() or b'{}'), dict(r.headers)
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}'), dict(e.headers)


def http_checks(base, stubs):
    c = {}
    s, j, hd = call(base, '/api/health'); c['health'] = j.get('app') == 'dmsg-desktop'
    c['csp_header'] = "default-src 'self'" in call(base, '/api/health')[2].get('Content-Security-Policy', '')
    c['wrong_host_403'] = call(base, '/api/health', headers={'Host': 'evil.example'})[0] == 403
    c['foreign_origin_403'] = call(base, '/api/model', {'text': 'x'}, {'Origin': 'http://evil.example'})[0] == 403
    c['duplicate_key_400'] = True
    try:
        rq = urllib.request.Request(base + '/api/model', data=b'{"text":"a","text":"b"}', headers={'Content-Type': 'application/json'}, method='POST')
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(rq, timeout=5); c['duplicate_key_400'] = False
    except urllib.error.HTTPError as e: c['duplicate_key_400'] = e.code == 400
    c['unconfigured'] = call(base, '/api/model', {'text': '지금 송금하세요'})[1].get('code') == 'ModelUnavailable:MODEL_NOT_CONFIGURED'
    c['ui_remote_blocked'] = call(base, '/api/config', {'endpoint': 'https://example.com/v1/systemone', 'model_id': 'm', 'timeout_s': 5})[1].get('code') == 'REMOTE_ENDPOINT_REQUIRES_OPERATOR_ENV'
    def relay(mode, timeout=3, text='지금 바로 이 계좌로 송금하세요.'):
        port = stubs[mode].server_port if mode in stubs else free_port()
        call(base, '/api/config', {'endpoint': f'http://127.0.0.1:{port}/v1/systemone', 'model_id': 'trillionlabs/Zoro-1', 'timeout_s': timeout})
        return call(base, '/api/model', {'text': text})[1]
    r = relay('ok'); c['relay_ok'] = r.get('ok') is True and r.get('model_id_echo') == 'ABSENT'
    c['echo_mismatch'] = relay('echo_bad').get('code') == 'ModelUnavailable:MODEL_ID_MISMATCH'
    c['dup_response'] = relay('dup').get('code') == 'ModelUnavailable:INVALID_RESPONSE_JSON'
    c['timeout'] = relay('slow', timeout=1).get('code') == 'ModelUnavailable:MODEL_TRANSPORT_ERROR_TimeoutError'
    c['refused'] = relay('closed').get('code') == 'ModelUnavailable:MODEL_TRANSPORT_ERROR_ConnectionRefusedError'
    relay('ok')  # leave a working config for the UI run
    return c


def ui_checks(base):
    from playwright.sync_api import sync_playwright
    SHOTS.mkdir(parents=True, exist_ok=True)
    OV = "(()=>{const w=innerWidth;return [...document.querySelectorAll('main *, header, nav')].filter(e=>e.offsetParent!==null&&!e.parentElement.closest('.chips')).filter(e=>e.getBoundingClientRect().right>w+1).length})()"
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        runs = [('http', base, c, d, 'no-preference') for c in ('light', 'dark') for d in ('desktop', 'mobile')] + \
               [('file', (WEB / 'index.html').as_uri(), 'light', 'mobile', 'no-preference'), ('file', (WEB / 'index.html').as_uri(), 'dark', 'mobile', 'reduce')]
        for scheme, url, cs, dev, motion in runs:
            vp = {'width': 1280, 'height': 900} if dev == 'desktop' else {'width': 390, 'height': 844}
            ctx = b.new_context(viewport=vp, color_scheme=cs, device_scale_factor=2 if dev == 'mobile' else 1, reduced_motion=motion)
            pg = ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
            t0 = time.perf_counter(); pg.goto(url)
            pg.wait_for_function('() => !document.getElementById("splash")', timeout=3000)
            k = f'{scheme}-{cs}-{dev}' + ('-reduced' if motion == 'reduce' else ''); r = {'overflow': {}}
            r['splash_gone_ms'] = round((time.perf_counter() - t0) * 1000)
            r['default_source_text'] = pg.is_visible('#freeText') and pg.inner_text('#runLabel') == '분석하기'
            # v4.5 on-device NLP: real inference in the page (no network); fallback when switched off
            pg.wait_for_function('() => /준비됨/.test(document.getElementById("nlpHint").textContent)', timeout=60000)
            pg.fill('#freeText', '고객님 계좌 보호를 위해 자금을 안전한 곳으로 옮기셔야 합니다. 지금 바로 진행해 주세요.')
            prev = pg.evaluate('document.getElementById("stateCode").textContent'); pg.click('#runBtn')
            pg.wait_for_function('p => document.getElementById("stateCode").textContent !== p && document.getElementById("runBtn").getAttribute("aria-busy") !== "true"', arg=prev, timeout=30000)
            r['nlp_indirect'] = pg.text_content('#stateCode'); r['nlp_badge'] = pg.locator('#facts .badge', has_text='온디바이스 NLP 실행됨').count() == 1
            r['nlp_latency_fact'] = pg.locator('#facts dd', has_text=' ms').count() >= 1
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-nlp.jpg'), full_page=True)
            pg.fill('#freeText', '엄마 이번 주말에 김장하러 갈게. 배추는 내가 사 갈게.')
            prev = pg.text_content('#stateCode'); pg.click('#runBtn')
            pg.wait_for_function('p => document.getElementById("stateCode").textContent !== p', arg=prev, timeout=30000)
            r['nlp_everyday'] = pg.text_content('#stateCode')
            r['no_safety_claim'] = '안전 보증 아님' in pg.inner_text('#stateLabel') if r['nlp_everyday'].startswith('NO_STRONG') else True
            # v4.6: CASE A shape (reconstructed) -> not cleared; risk-signal + structural sections; no check-mark icon on clearance
            pg.fill('#freeText', '[국제발신] 안녕하세요 갑자기 연락드려 죄송해요. 프로필 보고 대화해보고 싶어서요. 라인 아이디 sora_0921 로 연락 주실래요?')
            prev = pg.text_content('#stateCode'); pg.click('#runBtn')
            pg.wait_for_function('p => document.getElementById("stateCode").textContent !== p', arg=prev, timeout=30000)
            r['case_a_state'] = pg.get_attribute('#resultCard', 'data-state')
            r['risk_section'] = pg.locator('#facts dt.sec', has_text='위험 신호').count() == 1 and pg.locator('#facts dt', has_text='원문에서 찾은 단서').count() == 1
            r['identity_unverified'] = pg.locator('#facts dd', has_text='확인되지 않음').count() >= 1
            r['reason_code_collapsed'] = not pg.is_visible('#stateCode')
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-caseA.jpg'), full_page=True)
            pg.fill('#freeText', '엄마 이번 주말에 김장하러 갈게. 배추는 내가 사 갈게.'); prev = pg.text_content('#stateCode'); pg.click('#runBtn')
            pg.wait_for_function('p => document.getElementById("stateCode").textContent !== p', arg=prev, timeout=30000)
            r['clear_icon_not_check'] = 'M5 12.5 10 17l9-10' not in pg.inner_html('#stateIcon') if pg.get_attribute('#resultCard', 'data-state') == 'NO_STRONG_SIGNAL' else True
            # result must not be hidden under the fixed tab bar after scrolling it into view
            box = pg.locator('#resultCard').bounding_box(); nav = pg.locator('.tabbar').bounding_box()
            r['result_top_visible'] = box is not None and nav is not None and box['y'] < nav['y']
            pg.click('label.switch-row:has(#useNLP)'); assert not pg.is_checked('#useNLP')
            pg.fill('#freeText', '고객님 계좌 보호를 위해 자금을 안전한 곳으로 옮기셔야 합니다.'); pg.click('#runBtn'); pg.wait_for_timeout(300)
            r['nlp_off_fallback'] = pg.text_content('#stateCode'); r['fallback_badge'] = pg.locator('#facts .badge', has_text='의미 분석 불가').count() == 1
            pg.click('label.switch-row:has(#useNLP)')
            pg.click('.seg-btn[data-src=fixture]'); pg.click('text=송금 압박'); pg.click('#runBtn'); pg.wait_for_selector('#resultCard:not([hidden])'); pg.wait_for_timeout(450)
            r['fixture_transfer'] = pg.get_attribute('#resultCard', 'data-state'); r['overflow']['analyze'] = pg.evaluate(OV)
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-analyze.jpg'))
            pg.click('.seg-btn[data-src=text]'); pg.click('label.switch-row:has(#useNLP)')
            pg.fill('#freeText', '[경고] 계좌가 동결됩니다. 지금 바로 안전계좌로 이체하세요. 가족에게 말하지 마세요.')
            pg.click('#runBtn'); pg.wait_for_timeout(300)
            r['free_text_no_model'] = pg.get_attribute('#resultCard', 'data-state'); r['lexical_preview_shown'] = pg.locator('.preview').count() == 1
            if not pg.is_disabled('#useModel'):
                prev = pg.text_content('#stateCode'); pg.click('label.switch-row:has(#useModel)'); assert pg.is_checked('#useModel'); pg.click('#runBtn')
                pg.wait_for_function('p => document.querySelector("#stateCode").textContent !== p', arg=prev, timeout=8000)
                r['free_text_model'] = pg.text_content('#stateCode')
            pg.click('#tab-pay'); pg.click('text=거래처 계좌 변경 통지'); pg.click('#payBtn'); pg.wait_for_timeout(250)
            r['paylock_change'] = pg.inner_text('#payCode'); r['overflow']['pay'] = pg.evaluate(OV)
            pg.click('text=정상 참조자료와 일치'); pg.click('#payBtn'); pg.wait_for_timeout(250); r['paylock_match'] = pg.inner_text('#payCode')
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-pay.jpg'))
            pg.click('#tab-model'); pg.click('#simBtn'); pg.wait_for_timeout(250); r['simulated'] = pg.inner_text('#simOut code'); r['overflow']['model'] = pg.evaluate(OV)
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-model.jpg'))
            # v4.7 LinkGuard: link section in a message result, URL check, on-device APK check, consent defaults off
            pg.click('#tab-analyze')
            if not pg.is_checked('#useNLP'): pg.click('label.switch-row:has(#useNLP)')
            if pg.is_checked('#useModel'): pg.click('label.switch-row:has(#useModel)')
            pg.fill('#freeText', '[CJ택배] 주소 확인 후 앱을 설치하세요 https://nаver.com-secure.top/update.apk')
            pg.click('#runBtn')
            pg.wait_for_function('() => [...document.querySelectorAll("#facts dt.sec")].some(e => e.textContent.includes("링크 검사")) && document.getElementById("runBtn").getAttribute("aria-busy") !== "true"', timeout=30000)
            r['lg_link_section'] = pg.locator('#facts dt.sec', has_text='링크 검사').count() == 1
            r['lg_state'] = pg.get_attribute('#resultCard', 'data-state')
            r['lg_timeline_not_run_shown'] = pg.locator('#facts .timeline li', has_text='미실행').count() >= 1
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-linkguard-result.jpg'), full_page=True)
            pg.click('#tab-guard'); r['lg_consent_default_off'] = not pg.is_checked('#consentRep') and not pg.is_checked('#consentWeb')
            pg.fill('#urlText', 'http://0x7f000001/admin 그리고 https://www.yna.co.kr/view/A'); pg.click('#urlBtn'); pg.wait_for_timeout(150)
            r['lg_url_overall'] = pg.inner_text('#urlOut .state-mini')
            pg.set_input_files('#apkFile', str(ROOT / 'tests_data/apk_corpus/overperm_tracker.apk'))
            pg.wait_for_function('() => document.querySelector("#apkOut .state-mini")', timeout=20000)
            r['lg_apk_state'] = pg.inner_text('#apkOut .state-mini'); r['overflow']['guard'] = pg.evaluate(OV)
            pg.screenshot(type='jpeg', quality=80, path=str(SHOTS / f'{k}-guard.jpg'), full_page=True)
            pg.click('#tab-info'); pg.wait_for_timeout(250); r['overflow']['info'] = pg.evaluate(OV)
            r['host_pill'] = pg.inner_text('#hostPill')
            # back button returns to the previous tab instead of leaving the app
            pg.click('#tab-pay'); pg.go_back(); pg.wait_for_timeout(200); r['back_to_previous_tab'] = pg.is_visible('#view-info') and not pg.is_visible('#view-pay')
            # rotation proxy (viewport swap) keeps state; 300px width as a large-font proxy must not overflow
            pg.click('#tab-analyze'); txt = pg.input_value('#freeText')
            pg.set_viewport_size({'width': vp['height'], 'height': vp['width']}); pg.wait_for_timeout(150); r['rotation_keeps_input'] = pg.input_value('#freeText') == txt
            pg.set_viewport_size({'width': 300, 'height': 700}); pg.wait_for_timeout(200); r['overflow']['narrow300'] = pg.evaluate(OV)
            import base64 as _b64
            sh = _b64.urlsafe_b64encode('지금 바로 이 계좌로 송금하세요 bit.ly/x9Y'.encode()).decode()
            pg2 = ctx.new_page(); pg2.goto(url.split('#')[0] + '#share=' + sh)
            pg2.wait_for_function('() => !document.getElementById("splash")', timeout=3000)
            pg2.wait_for_function('() => !document.getElementById("resultCard").hidden', timeout=60000)
            r['share_prefilled'] = pg2.input_value('#freeText').startswith('지금 바로 이 계좌로')
            r['share_hash_cleared'] = pg2.evaluate('location.hash') == ''
            pg2.close()
            r['console_errors'] = errs
            out[k] = r; ctx.close()
        b.close()
    return out


def main():
    stubs = {m: stub(m) for m in ('ok', 'slow', 'echo_bad', 'dup')}
    port = free_port(); base = f'http://127.0.0.1:{port}'
    proc = subprocess.Popen([str(BIN), '--no-browser', f'--port={port}'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try: call(base, '/api/health'); break
            except Exception: time.sleep(0.1)
        http = http_checks(base, stubs)
        ui = ui_checks(base + '/')
    finally:
        proc.terminate(); proc.wait(5)
    expect_ui = all(v['fixture_transfer'] == 'PAUSE_AND_VERIFY' and v['free_text_no_model'] == 'ASK_HUMAN' and v['lexical_preview_shown']
                    and v['splash_gone_ms'] < 2000 and v['default_source_text'] and v['nlp_badge'] and v['nlp_latency_fact'] and v['no_safety_claim']
                    and v['nlp_off_fallback'].startswith('ASK_HUMAN') and v['fallback_badge']
                    and v['case_a_state'] != 'NO_STRONG_SIGNAL' and v['risk_section'] and v['identity_unverified'] and v['reason_code_collapsed']
                    and v['clear_icon_not_check'] and v['result_top_visible'] and v['back_to_previous_tab'] and v['rotation_keeps_input']
                    and v['paylock_change'] == 'HOLD_FOR_INDEPENDENT_VERIFICATION' and v['paylock_match'] == 'READY_FOR_INTERNAL_REVIEW_NOT_PAYMENT'
                    and v['simulated'] == 'MODEL_DIRECT_ACTION_ADVISORY' and not any(v['overflow'].values())
                    and v['lg_link_section'] and v['lg_state'] in ('CAUTION', 'PAUSE_AND_VERIFY') and v['lg_timeline_not_run_shown'] and v['lg_consent_default_off']
                    and '의심 구조' in v['lg_url_overall'] and '위험한 권한 조합' in v['lg_apk_state'] and v['share_prefilled'] and v['share_hash_cleared']
                    and not [e for e in v['console_errors'] if 'api/health' not in e and '404' not in e] for v in ui.values())
    model_ui = all(any(x in v.get('free_text_model', 'MODEL_DIRECT_ACTION_ADVISORY') for x in ('MODEL_DIRECT_ACTION_ADVISORY', 'WARNING_LABEL', 'DRA_MIN_EXPECTED_COST_PAUSE', 'DRA_DECISION_RELEVANT_UNCERTAINTY')) for v in ui.values())
    report = {'status': 'PASS' if all(http.values()) and expect_ui and model_ui else 'FAIL', 'http': http, 'ui': ui,
              'executed_on': 'linux-x64 binary + Chromium headless', 'not_executed': ['windows-x64', 'macos-arm64', 'macos-x64', 'android', 'ios'],
              'model': 'kev-shaped local stub, not Zoro-1', 'nlp': 'shipped on-device KoELECTRA-small int8 + heads, run inside Chromium (no network)'}
    (EVD / 'v47_app_smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps({'status': report['status'], 'http': http, 'ui': {k: {kk: vv for kk, vv in v.items() if kk in ('fixture_transfer', 'free_text_model', 'overflow', 'console_errors', 'splash_gone_ms', 'nlp_indirect', 'nlp_everyday', 'nlp_off_fallback', 'nlp_badge', 'case_a_state', 'risk_section', 'result_top_visible', 'back_to_previous_tab', 'rotation_keeps_input', 'lg_link_section', 'lg_state', 'lg_url_overall', 'lg_apk_state', 'share_prefilled', 'share_hash_cleared', 'lg_consent_default_off')} for k, v in ui.items()}}, ensure_ascii=False, indent=1))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
