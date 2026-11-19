"""v4.7 validation: LinkGuard PHASE 9 scenario matrix + regression suites. Writes internal/evidence/v47/.

Each scenario records expected, observed, evidence and the failure condition. Scenarios that need something this
environment does not have (internet, a phone, a reputation API key, an isolated fetcher) are recorded as NOT_RUN or
BLOCKED, never as PASS.
usage: python tools/run_v47_validation.py
"""
from __future__ import annotations
import datetime, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'dmsg'))
from linkguard import intake as LI, policy as PO, apk as AP  # noqa: E402

EVD = ROOT / 'internal/evidence/v47'
CORPUS = ROOT / 'tests_data/apk_corpus'
rows = []


def scen(sid, name, expected, fail_if, fn):
    try:
        observed, ok, evidence = fn()
        status = 'PASS' if ok else 'FAIL'
    except NotImplementedError as e:
        observed, status, evidence = str(e), 'NOT_RUN', '-'
    except PermissionError as e:
        observed, status, evidence = str(e), 'BLOCKED', '-'
    rows.append({'id': sid, 'scenario': name, 'expected': expected, 'observed': observed, 'evidence': evidence, 'failure_condition': fail_if, 'status': status})


def msg_state(t, **kw):
    r = LI.intake(t, consent=kw.pop('consent', {})); return PO.assess_message(r, **kw), r


def run_lg():
    scen('L01', 'URL 없는 메시지', 'url_count=0, overall=NOT_SCANNED, network_used=False', 'URL이 추출되거나 네트워크 사용',
         lambda: (lambda a: (f"url_count={a[1]['url_count']} overall={a[0]['overall']}", a[1]['url_count'] == 0 and a[0]['overall'] == 'NOT_SCANNED' and not a[1]['network_used'], 'linkguard.intake'))(msg_state('엄마 저녁 7시에 봐요')))
    scen('L02', '여러 URL', '두 URL을 원문 순서·코드포인트 오프셋으로 추출', '개수·순서·오프셋 불일치',
         lambda: (lambda r, m: ([u['raw'] for u in r['urls']], [u['raw'] for u in r['urls']] == ['https://www.yna.co.kr/view/A', 'bit.ly/x9Y'] and all(m[u['start']:u['end']] == u['raw'] for u in r['urls']), 'offsets'))(LI.intake('공지 https://www.yna.co.kr/view/A 및 bit.ly/x9Y 확인'), '공지 https://www.yna.co.kr/view/A 및 bit.ly/x9Y 확인'))
    scen('L03', '정상 뉴스 링크', '플래그 없음; 평판 미실행이면 NOT_SCANNED(안전 표시 아님)', '"안전" 상태 또는 위험 플래그',
         lambda: (lambda a: (f"{a[0]['overall']} flags={a[1]['urls'][0]['flags']}", a[0]['overall'] == 'NOT_SCANNED' and not a[1]['urls'][0]['flags'] and not a[0]['urls'][0]['is_safe_claim'], 'policy'))(msg_state('https://www.yna.co.kr/view/AKR2026')))
    scen('L04', '신규 미확인 도메인', 'NO_KNOWN_THREAT_FOUND로 끝나지 않음(검사 안 한 단계 표시)', '평판 없이 위협 없음 표시',
         lambda: (lambda a: (a[0]['overall'] + ' not_checked=' + ','.join(a[0]['urls'][0]['not_checked']), a[0]['overall'] != 'NO_KNOWN_THREAT_FOUND', 'policy'))(msg_state('https://promo-gift-2026.xyz/event')))
    scen('L05', '정상 단축 URL', 'SHORTENER 주의 플래그, 목적지 미확인(열지 않음)', '단축 URL을 열거나 플래그 누락',
         lambda: (lambda u: (u['flags'], 'SHORTENER' in u['flags'], 'intake'))(LI.analyze('https://han.gl/AbCd')))
    scen('L06', 'Punycode·동형문자 도메인', 'PUNYCODE+HOMOGLYPH_BRAND → SUSPICIOUS', '동형문자 미탐',
         lambda: (lambda a: (a[0]['overall'] + ' ' + str(a[1]['urls'][0]['flags']), a[0]['overall'] == 'SUSPICIOUS' and 'HOMOGLYPH_BRAND' in a[1]['urls'][0]['flags'], 'intake+policy'))(msg_state('https://xn--80ak6aa92e.com/login')))
    scen('L07', '내부 IP로의 리다이렉트', '격리 페치 단계 BLOCKED(이 릴리스에 없음); 내부 IP 직접 링크는 SUSPICIOUS·fetchable=False', '내부 IP를 가져오거나 PASS로 기록',
         lambda: (lambda a: (a[0]['overall'] + ' web=' + a[0]['urls'][0]['stages']['web_analysis'], a[0]['overall'] == 'SUSPICIOUS' and a[0]['urls'][0]['stages']['web_analysis'] == 'BLOCKED' and not a[1]['urls'][0]['fetchable'], 'policy (redirect following not shipped)'))(msg_state('http://169.254.169.254/latest', consent={'web_analysis': True})))
    def blocked(): raise PermissionError('BLOCKED: isolated fetcher not included in v4.7')
    scen('L08', '무한 리다이렉트', '홉 제한에서 중단', '무한 루프', blocked)
    scen('L09', '분석 중 DNS 변경', 'DNS_CHANGED_DURING_ANALYSIS 보고', '재바인딩된 내부 주소 접속', blocked)
    scen('L10', '로그인 토큰 포함 개인 URL', '토큰은 표시·외부 URL에서 제거, 쿼리 미전송', '토큰이 display/external에 남음',
         lambda: (lambda u: (u['display_url'] + ' | ' + u['external_url'], 's3cr3t' not in u['display_url'] + u['external_url'] and '?' not in u['external_url'], 'redaction'))(LI.analyze('https://example.com/reset?token=s3cr3t&lang=ko')))
    meta = json.loads((CORPUS / 'CORPUS.json').read_text()) if (CORPUS / 'CORPUS.json').is_file() else {}
    def apk_case(name, want_state, want_find=None):
        def f():
            if name not in meta: raise NotImplementedError('NOT_RUN: corpus missing')
            f = ROOT / meta[name]['path'] if 'path' in meta[name] else CORPUS / name
            r = AP.inspect(f.read_bytes(), name)
            return (f"{r['state']} findings={r['findings']} combos={r.get('risk_combinations')}", r['state'] == want_state and (want_find is None or want_find in r['findings']), f'{f.relative_to(ROOT).as_posix()} sha256={meta[name]["sha256"][:16]}')
        return f
    scen('A01', '정상 APK(자체 빌드)', 'NO_KNOWN_THREAT_FOUND + DEBUGGABLE 표시', '위험 조합 오탐', apk_case('own_iteraguard_debug.apk', 'NO_KNOWN_THREAT_FOUND', 'DEBUGGABLE'))
    scen('A02', '과도 권한 APK(합성)', 'SUSPICIOUS (SMS+접근성 등 조합)', '조합 미탐', apk_case('overperm_tracker.apk', 'SUSPICIOUS'))
    scen('A03', '난독화 APK(합성)', 'OBFUSCATION_LIKELY 표시, 그 자체로 SUSPICIOUS 아님', '난독화만으로 악성 판정', apk_case('obfuscated_game.apk', 'NO_KNOWN_THREAT_FOUND', 'OBFUSCATION_LIKELY'))
    scen('A04', '확장자 불일치(PDF→.apk)', 'SCAN_FAILED + EXTENSION_MISMATCH', 'APK로 처리', apk_case('mismatch_pdf.apk', 'SCAN_FAILED', 'NOT_AN_APK_CONTAINER_EXTENSION_MISMATCH'))
    scen('A05', '대용량 파일', 'NOT_SCANNED + FILE_TOO_LARGE (읽기 전 거부)', '대용량 파싱',
         lambda: (lambda r: (r['state'] + ' ' + str(r['findings']), r['state'] == 'NOT_SCANNED' and 'FILE_TOO_LARGE' in r['findings'], 'max_bytes=1024 synthetic'))(AP.inspect(b'PK\x03\x04' + b'\0' * 4096, 'big.apk', max_bytes=1024)))
    scen('A06', 'zip-slip 경로', 'SUSPICIOUS + PATH_TRAVERSAL, 추출 없음', '경로 탈출 허용', apk_case('zipslip.apk', 'SUSPICIOUS', 'PATH_TRAVERSAL'))
    def no_net(): raise NotImplementedError('NOT_RUN: this environment has no general internet; offline path is the default')
    scen('F01', '네트워크 장애', '형식 검사만으로 결과, 외부 단계 NOT_RUN', '장애를 위협 없음으로 표시',
         lambda: (lambda a: (str(a[0]['urls'][0]['stages']), a[0]['urls'][0]['stages']['safe_browsing'] == 'NOT_RUN' and a[0]['overall'] != 'NO_KNOWN_THREAT_FOUND', 'policy'))(msg_state('https://example.org/', consent={'external_reputation': True})))
    scen('F02', '위협 인텔리전스 서비스 장애', 'NOT_RUN 사유 기록(키 없음/미실행)', '장애를 안전으로 해석',
         lambda: (lambda a: (a[0]['urls'][0]['reputation'][1]['reason'], a[0]['urls'][0]['reputation'][1]['status'] == 'NOT_RUN', 'policy'))(msg_state('https://example.org/', consent={'external_reputation': True})))
    scen('F03', '사용자 취소', '중간 결과 폐기·기록 없음', '취소 후 외부 전송', lambda: (_ for _ in ()).throw(NotImplementedError('NOT_RUN: no cancellable remote stage exists in v4.7 (all stages local and synchronous)')))
    scen('F04', '검사 후 URL 콘텐츠 변경', '콘텐츠 해시 비교로 변경 감지', '변경 미감지', blocked)
    return rows


def run_cmd(name, cmd, cwd=ROOT, timeout=1800):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    tail = (p.stdout + p.stderr)[-1500:]
    return {'name': name, 'cmd': ' '.join(cmd), 'returncode': p.returncode, 'tail': tail}


def main():
    EVD.mkdir(parents=True, exist_ok=True)
    run_lg()
    suites = [run_cmd('dmsg unittest', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT / 'dmsg'),
              run_cmd('linkguard+arbiter unittest', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests_linkguard', '-t', '.', '-q']),
              run_cmd('engine conformance (Python↔JS)', ['node', 'apps/conformance/run_conformance.js']),
              run_cmd('linkguard conformance (Python↔JS)', ['node', 'apps/conformance/run_linkguard.js']),
              run_cmd('apk parity (Python↔JS, mutations, androguard oracle)', [sys.executable, 'tools/linkguard/apk_parity.py'])]
    counts = {s: sum(1 for r in rows if r['status'] == s) for s in ('PASS', 'FAIL', 'NOT_RUN', 'BLOCKED')}
    rep = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scenario_counts': counts, 'scenarios': rows, 'suites': suites,
           'regression_messages': 'see internal/evidence/v47/v47_arbiter_eval.json (의심계 4 sets) and dmsg unittest (PAYLOCK included)'}
    (EVD / 'v47_validation.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    md = ['| ID | 시나리오 | 기대 | 관찰 | 근거 | 실패 조건 | 상태 |', '|---|---|---|---|---|---|---|']
    for r in rows:
        md.append('| {id} | {scenario} | {expected} | {obs} | {evidence} | {failure_condition} | {status} |'.format(obs=str(r['observed']).replace('|', '/')[:140], **{k: str(v).replace('|', '/') for k, v in r.items() if k != 'observed'}))
    (EVD / 'v47_validation_matrix.md').write_text('\n'.join(md) + '\n')
    print(json.dumps({'scenarios': counts, 'suites': [(s['name'], s['returncode']) for s in suites]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
