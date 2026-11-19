"""LinkGuard v4.7 unit tests (offline). Run: python -m unittest discover -s tests_linkguard -t ."""
import hashlib, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from linkguard import intake as LI, apk as AP, policy as PO  # noqa: E402
from tools.release_metadata import load_distribution

CORPUS = ROOT / 'tests_data' / 'apk_corpus'


def corpus_meta():
    meta = json.loads((CORPUS / 'CORPUS.json').read_text())
    dist = load_distribution(ROOT)
    own = meta['own_iteraguard_debug.apk']
    own.update(path=dist['apk'], sha256=dist['sha256'])
    own.pop('bytes', None)  # Current artifact hash is fixed by build metadata.
    return meta


def urls(msg, **kw):
    return LI.intake(msg, **kw)['urls']


class Intake(unittest.TestCase):
    def test_no_url(self):
        r = LI.intake('엄마 오늘 저녁 7시에 봐요. 3.14 는 파이야', message_id='m1')
        self.assertEqual(r['url_count'], 0); self.assertFalse(r['network_used'])
        self.assertEqual(PO.assess_message(r)['overall'], 'NOT_SCANNED')

    def test_multiple_urls_order_and_offsets(self):
        m = '공지 https://www.yna.co.kr/view/A 및 bit.ly/x9Y 확인'
        u = urls(m)
        self.assertEqual([x['raw'] for x in u], ['https://www.yna.co.kr/view/A', 'bit.ly/x9Y'])
        for x in u: self.assertEqual(m[x['start']:x['end']], x['raw'])

    def test_korean_suffix_trimmed(self):
        self.assertEqual(urls('bit.ly/abc에서 확인')[0]['raw'], 'bit.ly/abc')

    def test_normal_news(self):
        u = urls('https://www.yna.co.kr/view/AKR2026')[0]
        self.assertEqual(u['registrable_domain'], 'yna.co.kr'); self.assertEqual(u['flags'], [])

    def test_unknown_new_domain_is_not_safe(self):
        r = LI.intake('신규 이벤트 https://promo-gift-2026.xyz/event')
        a = PO.assess_message(r)
        self.assertNotEqual(a['overall'], 'NO_KNOWN_THREAT_FOUND')   # nothing ran beyond intake
        self.assertFalse(a['urls'][0]['is_safe_claim'])

    def test_shortener(self):
        self.assertIn('SHORTENER', urls('han.gl/AbCd')[0]['flags'])

    def test_punycode_homoglyph(self):
        f = urls('https://xn--80ak6aa92e.com/')[0]['flags']
        self.assertIn('PUNYCODE', f); self.assertIn('HOMOGLYPH_BRAND', f)
        f2 = urls('https://nаver.com-secure.top/')[0]['flags']   # Cyrillic а
        self.assertIn('HOMOGLYPH_BRAND', f2); self.assertIn('MIXED_SCRIPT', f2)

    def test_brand_on_unofficial_domain(self):
        u = urls('http://kbstar-login.top/x')[0]
        self.assertIn('BRAND_NOT_OFFICIAL_DOMAIN', u['flags'])
        self.assertEqual(urls('https://obank.kbstar.com/')[0]['flags'], [])

    def test_private_and_obfuscated_ip(self):
        for s in ('http://127.0.0.1/', 'http://0x7f000001/', 'http://2130706433/', 'http://10.1.2.3/', 'http://169.254.169.254/latest',
                  'http://[::1]/', 'http://[fe80::1]/', 'http://[::ffff:127.0.0.1]/', 'http://192.168.0.1:8080/'):
            u = LI.analyze(s)
            self.assertIn('NON_PUBLIC_IP', u['flags'], s); self.assertFalse(u['fetchable'], s)
        self.assertIn('OBFUSCATED_IP', LI.analyze('http://0177.0.0.1/')['flags'])

    def test_token_redaction(self):
        u = LI.analyze('https://example.com/reset/aZ09aZ09aZ09aZ09aZ09aZ09aZ?token=s3cr3t&lang=ko#frag')
        self.assertNotIn('s3cr3t', json.dumps(u, ensure_ascii=False).replace(u['raw'], ''))
        self.assertNotIn('aZ09aZ09aZ09', u['display_url'])
        self.assertEqual(u['external_url'], 'https://example.com/reset/{REDACTED}')
        self.assertIn('SENSITIVE_QUERY', u['flags'])

    def test_userinfo_removed(self):
        u = LI.analyze('https://www.naver.com@evil.top/login')
        self.assertEqual(u['host_ascii'], 'evil.top'); self.assertIn('USERINFO_AT', u['flags'])
        self.assertNotIn('naver.com@', u['display_url'])

    def test_non_http_never_fetchable(self):
        for s in ('intent://scan/#Intent;scheme=zxing;end', 'javascript:alert(1)', 'tel:01012345678', 'data:text/html,hi', 'file:///etc/passwd'):
            u = LI.analyze(s)
            self.assertFalse(u['fetchable'], s); self.assertIsNone(u['external_url'], s); self.assertIn('NON_HTTP_SCHEME', u['flags'])
        self.assertIn('DANGEROUS_SCHEME', LI.analyze('javascript:alert(1)')['flags'])

    def test_messenger_and_apk(self):
        self.assertIn('MESSENGER_LINK', urls('open.kakao.com/o/abc')[0]['flags'])
        self.assertIn('APK_DOWNLOAD', urls('https://dl.example.top/app/update.apk')[0]['flags'])

    def test_defanged(self):
        u = urls('naver[.]com/x')[0]
        self.assertIn('DEFANGED', u['flags']); self.assertEqual(u['host_ascii'], 'naver.com')

    def test_punycode_roundtrip(self):
        for w in ('münchen', '한국', 'bücher', 'пример'):
            self.assertEqual(LI.punycode_decode(LI.punycode_encode(w)), w)
        self.assertEqual(LI.punycode_encode('münchen'), 'mnchen-3ya')

    def test_bad_input(self):
        with self.assertRaises(ValueError): LI.intake('x' * (LI.MAX_TEXT + 1))
        with self.assertRaises(ValueError): LI.intake(None)

    def test_url_cap(self):
        self.assertEqual(LI.intake(' '.join('a%d.com' % i for i in range(50)))['url_count'], LI.MAX_URLS)


class Policy(unittest.TestCase):
    def test_states_and_scope(self):
        r = LI.intake('http://127.0.0.1/admin')
        a = PO.assess_message(r)
        self.assertEqual(a['overall'], 'SUSPICIOUS')
        self.assertIn('web_analysis', a['urls'][0]['not_checked'])

    def test_known_malicious_local_list(self):
        r = LI.intake('https://bad-parcel.test/track')
        a = PO.assess_message(r, blocklist={'domains': ['bad-parcel.test'], 'source': 'fixture', 'as_of': '2026-11-02'})
        self.assertEqual(a['overall'], 'KNOWN_MALICIOUS')
        self.assertEqual(PO.fuse({'policy_action': 'NO_STRONG_SIGNAL'}, a)['policy_action'], 'PAUSE_AND_VERIFY')

    def test_external_reputation_not_run_without_consent_or_key(self):
        a = PO.assess_message(LI.intake('https://example.com/'))
        self.assertEqual(a['urls'][0]['stages']['safe_browsing'], 'NOT_RUN')
        a2 = PO.assess_message(LI.intake('https://example.com/', consent={'external_reputation': True}))
        self.assertEqual(a2['urls'][0]['reputation'][1]['reason'], 'NO_API_KEY_ON_SERVER')

    def test_web_analysis_blocked_even_with_consent(self):
        a = PO.assess_message(LI.intake('https://example.com/', consent={'web_analysis': True}))
        self.assertEqual(a['urls'][0]['stages']['web_analysis'], 'BLOCKED')

    def test_never_downgrade(self):
        for base in ('PAUSE_AND_VERIFY', 'ASK_HUMAN', 'CAUTION'):
            f = PO.fuse({'policy_action': base}, {'overall': 'NO_KNOWN_THREAT_FOUND'})
            self.assertEqual(f['policy_action'], base); self.assertFalse(f['downgraded'])
        self.assertEqual(PO.fuse({'policy_action': 'ASK_HUMAN'}, {'overall': 'SUSPICIOUS'})['policy_action'], 'ASK_HUMAN')
        self.assertEqual(PO.fuse({'policy_action': 'NO_STRONG_SIGNAL'}, None, 'SUSPICIOUS')['policy_action'], 'CAUTION')

    def test_no_safe_wording(self):
        a = PO.assess_message(LI.intake('https://www.yna.co.kr/'), blocklist={'domains': [], 'source': 'fixture', 'as_of': 'x'})
        self.assertEqual(a['overall'], 'NO_KNOWN_THREAT_FOUND'); self.assertEqual(a['urls'][0]['note'], 'NO_DETECTION_IS_NOT_SAFETY')
        self.assertNotIn('SAFE', a['overall'].replace('NO_KNOWN_THREAT_FOUND', ''))


class Apk(unittest.TestCase):
    def test_corpus_expectations(self):
        meta = corpus_meta()
        for name, m in meta.items():
            with self.subTest(name=name):
                f = ROOT / m['path'] if 'path' in m else CORPUS / name
                self.assertTrue(f.is_file(), f'Missing required corpus artifact: {f}')
                self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), m['sha256'])
                r = AP.inspect(f.read_bytes(), name)
                self.assertEqual(r['state'], m['expect']['state'])
                if 'finding' in m['expect']: self.assertIn(m['expect']['finding'], r['findings'])
                if m['expect'].get('obfuscation_likely'): self.assertTrue(r['obfuscation']['likely'])
                self.assertEqual(r['verdict_basis'], 'NOT_A_MALWARE_VERDICT')

    def test_overperm_details(self):
        r = AP.inspect((CORPUS / 'overperm_tracker.apk').read_bytes(), 'overperm_tracker.apk')
        self.assertIn('SMS', r['permission_groups']); self.assertIn('ACCESSIBILITY', r['special_access'])
        self.assertIn('SMS_PLUS_ACCESSIBILITY', r['risk_combinations']); self.assertIn('DYNAMIC_CODE_LOADING', r['capabilities'])
        self.assertIn('203.0.113.77', r['network_indicators']['ipv4'])
        self.assertIn('assets/payload.dex', r['nested_packages'])

    def test_permission_alone_not_suspicious(self):
        # INTERNET + obfuscation only -> not SUSPICIOUS
        r = AP.inspect((CORPUS / 'obfuscated_game.apk').read_bytes(), 'obfuscated_game.apk')
        self.assertEqual(r['state'], 'NO_KNOWN_THREAT_FOUND'); self.assertIn('OBFUSCATION_LIKELY', r['findings'])
        self.assertIn('arm64-v8a:libgame.so', r['native_libs'])

    def test_oversized(self):
        r = AP.inspect(b'PK\x03\x04' + b'\0' * 2048, 'big.apk', max_bytes=1024)
        self.assertEqual(r['state'], 'NOT_SCANNED'); self.assertIn('FILE_TOO_LARGE', r['findings'])

    def test_truncated_zip(self):
        b = (CORPUS / 'normal_utility.apk').read_bytes()
        self.assertEqual(AP.inspect(b[: len(b) // 2], 'cut.apk')['state'], 'SCAN_FAILED')

    def test_own_apk_cert(self):
        meta = corpus_meta()
        p = ROOT / meta.get('own_iteraguard_debug.apk', {}).get('path', 'missing')
        self.assertTrue(p.is_file(), 'Current release APK is required')
        r = AP.inspect(p.read_bytes(), p.name)
        self.assertEqual(r['manifest']['package'], 'kr.iteraguard.doubtmeter')
        self.assertEqual(r['signing'][0]['scheme'], 'v2'); self.assertEqual(r['signing'][0]['subject_cn'], 'IteraGuard Debug')


class Regression(unittest.TestCase):
    def test_dmsg_path_set_unchanged(self):
        baseline = (ROOT / 'internal/evidence/v47/BASELINE_V46.json').read_bytes()
        base = json.loads(baseline)
        additions = json.loads((ROOT / 'tests_data/release/skill_path_additions.json').read_text())
        self.assertEqual(hashlib.sha256(baseline).hexdigest(), additions['baseline_sha256'])
        files = sorted(p.relative_to(ROOT / 'dmsg').as_posix() for p in (ROOT / 'dmsg').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        expected = set(base['dmsg_frozen']['skill_files']) | set(additions['additions'])
        self.assertEqual(files, sorted(expected))


if __name__ == '__main__':
    unittest.main()
