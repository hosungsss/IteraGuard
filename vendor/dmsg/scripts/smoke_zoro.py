"""OPTIONAL operator-run Zoro System One contract capture (NO LIVE TEST IS CLAIMED).

v4.2: probes the SAME six questions the product sends (prototype.model_bridge.questions),
not the legacy two-question set, and records the response *shape* so the adapter can be
checked against a real kev server before the event.

Usage (local kev, e.g. `python -m kev.serve --run <dir> --port 8008`):
  python scripts/smoke_zoro.py --url http://127.0.0.1:8008/v1/systemone \
      --model-id trillionlabs/Zoro-1 --revision <hf-commit> --out /secure/smoke.json
Optional bearer token via ZORO_API_KEY. Synthetic text only. Output stays NOT_ATTESTED.
Exit 0 only when every synthetic probe parses AND reaches its expected policy action.
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prototype.model_bridge import questions, advisory, SPEC, OPTIONAL_QUESTIONS
from prototype.typed_contract import normalize_response, ContractError

# Expected actions are for the ADAPTER/POLICY path given a sensible model answer.
# A mismatch is a finding to inspect, not proof the model is wrong.
PROBES = (
    ('P_DIRECT', '합성 사례: 지금 바로 이 계좌로 300만원 송금하세요.', {'PAUSE_AND_VERIFY'}),
    ('P_WARNING', '합성 사례: 누가 요구해도 송금하지 마세요.', {'NO_STRONG_SIGNAL', 'ASK_HUMAN'}),
    ('P_QUOTE', '합성 사례: 상대가 송금하라고 했다고 신고했습니다.', {'CAUTION', 'ASK_HUMAN'}),
    ('P_DECORATED', '합성 사례: [경고] 계좌가 동결됩니다. 지금 바로 안전계좌로 이체하세요. 가족에게 말하지 마세요.', {'PAUSE_AND_VERIFY', 'ASK_HUMAN'}),
)


def shape(value, depth=0):
    """Field names and JSON types only; never values (values may echo text)."""
    if depth > 4:
        return '...'
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    return type(value).__name__


def post(url, body, timeout):
    data = json.dumps(body, ensure_ascii=False).encode()
    headers = {'Content-Type': 'application/json'}
    key = os.environ.get('ZORO_API_KEY')
    if key:
        headers['Authorization'] = 'Bearer ' + key

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    t = time.monotonic()
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read(200000)
        return resp.status, resp.headers.get('Content-Type', ''), raw, round(1000 * (time.monotonic() - t), 2), hashlib.sha256(data).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--url', required=True)
    p.add_argument('--model-id', required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--timeout', type=float, default=30.0)
    p.add_argument('--send-model-field', action='store_true')
    a = p.parse_args(argv)
    u = urllib.parse.urlparse(a.url)
    if u.scheme != 'https' and not (u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost')):
        p.error('HTTPS required unless localhost')
    if u.path.rstrip('/') != '/v1/systemone':
        p.error('must use exact /v1/systemone path')
    if not 0.5 <= a.timeout <= 120:
        p.error('timeout out of range')
    record = {'status': 'NOT_ATTESTED', 'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_id_declared': a.model_id, 'checkpoint_revision_declared': a.revision,
              'endpoint_host': u.hostname, 'synthetic_only': True, 'question_set': sorted(SPEC),
              'optional_questions': sorted(OPTIONAL_QUESTIONS), 'model_field_sent': a.send_model_field,
              'probes': []}
    ok = True
    for pid, text, expected in PROBES:
        body = questions(text)
        if a.send_model_field:
            body['model'] = a.model_id
        item = {'probe': pid, 'expected_policy_actions': sorted(expected)}
        try:
            status, ctype, raw, ms, req_hash = post(a.url, body, a.timeout)
            item.update(http_status=status, content_type=ctype.split(';')[0].strip(), latency_ms=ms,
                        request_sha256=req_hash, response_sha256=hashlib.sha256(raw).hexdigest())
            parsed = json.loads(raw)
            item['response_shape'] = shape(parsed)
            item['model_field_in_response'] = isinstance(parsed, dict) and 'model' in parsed
            try:
                norm = normalize_response(parsed, SPEC, optional=OPTIONAL_QUESTIONS)
                item['schema_check'] = 'PASS_NOT_ATTESTATION'
                item['dropped_optional'] = list(norm.get('_dropped_optional', ()))
                item['score_key_format'] = norm.get('q_risk', {}).get('key_format')
                adv = advisory(text, parsed)
                item['policy_action'] = adv['action']
                item['policy_reason'] = adv['reason']
                item['top_choices'] = {'q_action': adv['selected_action'], 'q_speech': adv['selected_speech']}
                if adv['action'] not in expected:
                    ok = False
                    item['finding'] = 'POLICY_ACTION_OUTSIDE_EXPECTATION'
            except ContractError as exc:
                ok = False
                item['schema_check'] = 'FAILED_' + str(exc)
        except Exception as exc:  # operator diagnostic tool: record and continue
            ok = False
            item['error_type'] = type(exc).__name__
        record['probes'].append(item)
    lat = sorted(x['latency_ms'] for x in record['probes'] if 'latency_ms' in x)
    record['latency_ms_observed'] = lat
    record['latency_note'] = 'n=%d sequential synthetic probes on this host only; not p95.' % len(lat)
    record['overall'] = 'CONTRACT_AND_POLICY_PROBES_PASS_NOT_ATTESTED' if ok else 'FINDINGS_PRESENT'
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf8')
    try:
        out.chmod(0o600)
    except OSError:
        pass
    print(json.dumps({'output': str(out), 'overall': record['overall'],
                      'probes': [(x['probe'], x.get('schema_check', x.get('error_type')), x.get('policy_action')) for x in record['probes']]},
                     ensure_ascii=False))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
