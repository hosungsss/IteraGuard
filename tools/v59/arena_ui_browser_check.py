"""Real-browser check of the Arena UI (Playwright/Chromium) against a running server. usage: python tools/v59/arena_ui_browser_check.py http://127.0.0.1:8791/ OUT_DIR"""
import sys, json
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
R = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, vp in (('desktop', {'width': 1360, 'height': 900}), ('mobile', {'width': 390, 'height': 844})):
        pg = b.new_page(viewport=vp, device_scale_factor=2 if name == 'mobile' else 1)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.goto(url); pg.wait_for_function('() => document.getElementById("lifecycle").textContent !== "불러오는 중"', timeout=15000)
        pg.screenshot(path=f'{out}/{name}-0-initial.png', full_page=True)
        r = {}
        pg.fill('#text', '계정 정지를 피하려면 메시지에 첨부한 링크에서 로그인 비밀번호와 인증번호를 입력하세요.')
        pg.click('#run')
        pg.wait_for_function('() => document.body.dataset.phase === "idle" && document.querySelector(\'[data-stage="task"]\').dataset.state', timeout=15000)
        r['risky'] = {'action': pg.text_content('#action'), 'title': pg.text_content('#verdictTitle'), 'verdict': pg.evaluate('document.body.dataset.verdict'),
                      'stages': pg.evaluate('[...document.querySelectorAll(".stage")].map(s=>[s.dataset.stage,s.dataset.state,s.querySelector("small").textContent])'),
                      'task_panel_visible': pg.is_visible('#taskPanel'), 'meta': pg.text_content('#pipeMeta'), 'mode': pg.text_content('#modePill')}
        pg.screenshot(path=f'{out}/{name}-1-risky.png', full_page=True)
        pg.fill('#text', '신청하신 화분이 준비됐어요. 편한 시간에 공방으로 찾아와 주세요.'); pg.click('#run')
        pg.wait_for_function('() => document.body.dataset.phase === "idle" && document.getElementById("currentTurn").textContent', timeout=15000)
        pg.wait_for_timeout(900)
        r['ordinary_after_risk'] = {'action': pg.text_content('#action'), 'currentTurn': pg.text_content('#currentTurn'), 'session': pg.text_content('#sessionNotice'),
                                    'policy_stage': pg.text_content('[data-stage="policy"] small')}
        pg.screenshot(path=f'{out}/{name}-2-retained.png', full_page=True)
        pg.fill('#text', 'FAIL 연결 실패 재현'); pg.click('#run')
        pg.wait_for_function('() => document.body.dataset.phase === "idle" && document.querySelector(\'[data-stage="model"]\').dataset.state === "fail"', timeout=15000)
        pg.wait_for_timeout(900)
        r['failure'] = {'action': pg.text_content('#action'), 'model_stage': pg.text_content('[data-stage="model"] small'), 'notice': pg.text_content('#modelNotice'), 'mode': pg.text_content('#modePill')}
        pg.screenshot(path=f'{out}/{name}-3-failure.png', full_page=True)
        pg.click('#openSheet'); pg.wait_for_timeout(600)
        r['sheet_open'] = pg.evaluate('document.getElementById("sheet").classList.contains("open")')
        pg.screenshot(path=f'{out}/{name}-4-sheet.png')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
        r['sheet_closed_by_escape'] = not pg.evaluate('document.getElementById("sheet").classList.contains("open")')
        r['overflow_x'] = pg.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
        r['errors'] = errs
        R[name] = r; pg.close()
    b.close()
json.dump(R, open(f'{out}/ui_check.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1)[:4000])
