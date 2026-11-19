/*
 * dmsg engine (JavaScript port of the Python reference in dmsg/prototype).
 *
 * Data (patterns, fixtures, messages, records) is generated from Python by
 * tools/export_engine_data.py; only the algorithms live here. Offsets and
 * lengths are reported in Unicode code points, as in Python. Behavioural
 * equality with Python is checked by apps/conformance (vectors produced by
 * tools/make_conformance_vectors.py). This engine performs no network calls
 * and no external actions; it returns advisory states only.
 */
(function (root, factory) {
  var api = factory(root.DMSG_DATA || (typeof require === 'function' ? (require('./engine-data.js'), root.DMSG_DATA) : null));
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.DMSG = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (D) {
  'use strict';
  if (!D) throw new Error('DMSG_DATA_MISSING');

  // ---------- helpers ----------
  function rx(p, extra) { return new RegExp(p.source, p.flags + (extra || '')); }
  function cpLen(s) { var n = 0; for (var _ of s) n++; return n; }
  function cpIndex(s, i) { return cpLen(s.slice(0, i)); }
  function isPlainObject(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
  function sameSet(a, b) {
    if (a.length !== b.length) return false;
    var s = new Set(a); for (var x of b) if (!s.has(x)) return false; return true;
  }
  function subset(a, b) { var s = new Set(b); for (var x of a) if (!s.has(x)) return false; return true; }
  function escapeRx(s) { return s.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&'); }
  function pyStrip(s) { return s.replace(/^[\s\x1c-\x1f\x85]+|[\s\x1c-\x1f\x85]+$/gu, ''); }
  function ContractError(code) { var e = new Error(code); e.name = 'ContractError'; e.code = code; return e; }
  function PaylockError(code) { var e = new Error(code); e.name = 'PaylockError'; e.code = code; return e; }

  var G = D.guard, M = D.model, C = D.core;
  var WARNING = G.warning.map(function (p) { return rx(p); });
  var REPORT = G.report.map(function (p) { return rx(p); });
  var PRESSURE = G.pressure.map(function (p) { return rx(p); });
  var REQUEST = G.request.map(function (p) { return rx(p); });
  var SECRECY_G = G.secrecy.map(function (p) { return rx(p, 'g'); });
  var CREDENTIAL = rx(G.credential_topic);
  var CLAUSE_SPLIT_G = rx(G.clause_split, 'g');
  var EXTERNAL = G.external_directive.map(function (p) { return rx(p); });
  var TOKENS = G.action_tokens.map(function (t) { return t.toLowerCase(); });

  // ---------- strict JSON (rejects duplicate keys and NaN/Infinity, like the Python bridge) ----------
  function strictJSON(text) {
    var i = 0, s = String(text);
    function ws() { while (i < s.length && ' \t\n\r'.indexOf(s[i]) >= 0) i++; }
    function fail() { throw new SyntaxError('INVALID_RESPONSE_JSON'); }
    function str() {
      if (s[i] !== '"') fail();
      var j = i + 1, esc = false;
      for (; j < s.length; j++) {
        var c = s[j];
        if (esc) { esc = false; continue; }
        if (c === '\\') { esc = true; continue; }
        if (c === '"') break;
        if (c < ' ') fail();
      }
      if (j >= s.length) fail();
      var out = JSON.parse(s.slice(i, j + 1)); i = j + 1; return out;
    }
    function val() {
      ws(); var c = s[i];
      if (c === '{') {
        i++; var o = Object.create(null), keys = new Set(); ws();
        if (s[i] === '}') { i++; return toObj(o); }
        for (;;) {
          ws(); var k = str(); ws(); if (s[i] !== ':') fail(); i++;
          if (keys.has(k)) throw new SyntaxError('DUPLICATE_MODEL_RESPONSE_KEY');
          keys.add(k); o[k] = val(); ws();
          if (s[i] === ',') { i++; continue; }
          if (s[i] === '}') { i++; return toObj(o); }
          fail();
        }
      }
      if (c === '[') {
        i++; var a = []; ws(); if (s[i] === ']') { i++; return a; }
        for (;;) { a.push(val()); ws(); if (s[i] === ',') { i++; continue; } if (s[i] === ']') { i++; return a; } fail(); }
      }
      if (c === '"') return str();
      var m = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(s.slice(i));
      if (m) { i += m[0].length; return Number(m[0]); }
      if (s.startsWith('true', i)) { i += 4; return true; }
      if (s.startsWith('false', i)) { i += 5; return false; }
      if (s.startsWith('null', i)) { i += 4; return null; }
      fail();
    }
    function toObj(o) { var r = {}; for (var k of Object.keys(o)) Object.defineProperty(r, k, { value: o[k], enumerable: true, writable: true, configurable: true }); return r; }
    var v = val(); ws(); if (i !== s.length) fail(); return v;
  }

  // ---------- context guard ----------
  function warningCue(text) {
    var masked = text;
    if (!CREDENTIAL.test(text)) SECRECY_G.forEach(function (r) { r.lastIndex = 0; masked = masked.replace(r, ' '); });
    return WARNING.some(function (r) { return r.test(masked); });
  }
  function contextFlags(text) {
    if (typeof text !== 'string') throw new TypeError('TEXT_REQUIRED');
    var folded = text.toLowerCase();
    return {
      action_mentioned: TOKENS.some(function (t) { return folded.indexOf(t) >= 0; }),
      warning_cue: warningCue(text),
      report_cue: REPORT.some(function (r) { return r.test(text); }),
      request_cue: REQUEST.some(function (r) { return r.test(text); }),
      pressure_cue: PRESSURE.some(function (r) { return r.test(text); })
    };
  }
  // Clauses carry UTF-16 positions internally (u16start/u16end) and code points for output.
  function clauseProfile(text) {
    if (typeof text !== 'string') throw new TypeError('TEXT_REQUIRED');
    var out = [], pos = 0, ms = Array.from(text.matchAll(CLAUSE_SPLIT_G));
    ms.push(null);
    for (var m of ms) {
      var end = m ? m.index : text.length, piece = text.slice(pos, end);
      if (pyStrip(piece)) {
        var f = contextFlags(piece);
        var clean = f.action_mentioned && !f.warning_cue && !f.report_cue;
        out.push({ u16start: pos, u16end: end, start: cpIndex(text, pos), end: cpIndex(text, end),
          flags: f, clean_action: clean, clean_imperative: clean && f.request_cue });
      }
      if (m) pos = m.index + m[0].length;
    }
    return out;
  }
  function contextConflict(action, speech, flags, profile) {
    if (action === 'none' && flags.action_mentioned && speech !== 'informational') return 'MODEL_NONE_BUT_ACTION_TERMS_PRESENT';
    if (action === 'none' && speech === 'direct_request') return 'NONE_DIRECT_REQUEST_CONFLICT';
    if (profile) {
      var acts = profile.filter(function (c) { return c.flags.action_mentioned; });
      var clean = acts.filter(function (c) { return c.clean_action; });
      var imp = acts.filter(function (c) { return c.clean_imperative; });
      if (speech === 'direct_request' && acts.length && !clean.length) return 'DIRECT_REQUEST_CONTRADICTS_CONTEXT';
      if (speech === 'negated_or_warning') {
        if (imp.length) return 'WARNING_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE';
        if (acts.length && !acts.some(function (c) { return c.flags.warning_cue; })) return 'UNSUPPORTED_WARNING_LABEL';
      }
      if (speech === 'informational' && imp.length) return 'INFORMATIONAL_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE';
      if (speech === 'reported_or_quoted') {
        if (imp.length) return 'REPORT_LABEL_CONTRADICTED_BY_IMPERATIVE_CLAUSE';
        if (acts.length && !acts.some(function (c) { return c.flags.report_cue; })) return 'UNSUPPORTED_QUOTATION_LABEL';
      }
      return null;
    }
    if (speech === 'direct_request' && (flags.warning_cue || flags.report_cue)) return 'DIRECT_REQUEST_CONTRADICTS_CONTEXT';
    if (speech === 'negated_or_warning' && flags.action_mentioned && !flags.warning_cue) return 'UNSUPPORTED_WARNING_LABEL';
    if (speech === 'reported_or_quoted' && flags.action_mentioned && !flags.report_cue) return 'UNSUPPORTED_QUOTATION_LABEL';
    return null;
  }
  function externalDirectiveFlags(text) {
    if (typeof text !== 'string' || cpLen(text) > G.external_max) throw new Error('UNSUPPORTED_EXTERNAL_TEXT');
    return EXTERNAL.some(function (r) { return r.test(text); }) ? ['UNTRUSTED_TEXT_INSTRUCTION_CUE'] : [];
  }

  // ---------- core policy (fixture / annotated evidence) ----------
  function result(action, reason, spans) {
    return { action: action, reason: reason, evidence: spans || [], message: C.messages[action], mode: C.default_mode };
  }
  function contradictions(spans) {
    for (var i = 0; i < spans.length; i++) for (var j = i + 1; j < spans.length; j++) {
      var a = spans[i], b = spans[j];
      if (a.start < b.end && b.start < a.end && (a.directness !== b.directness || a.kind !== b.kind)) return true;
    }
    return false;
  }
  function decide(text, spans, opts) {
    opts = opts || {};
    var status = opts.status === undefined ? 'OK' : opts.status;
    var review = opts.user_asks_review === undefined ? false : opts.user_asks_review;
    if (typeof text !== 'string' || !pyStrip(text) || cpLen(text) > C.max_text) return result('ASK_HUMAN', 'EMPTY_OR_INVALID_INPUT');
    if (C.statuses.indexOf(status) < 0 || typeof review !== 'boolean') return result('ASK_HUMAN', 'INVALID_CONTROL_SCHEMA');
    if (!Array.isArray(spans) || spans.length > C.max_spans) return result('ASK_HUMAN', 'INVALID_EVIDENCE_COLLECTION');
    var cps = Array.from(text);
    for (var s of spans) {
      if (!isPlainObject(s) || C.kinds.indexOf(s.kind) < 0 || C.directness.indexOf(s.directness) < 0 || C.origins.indexOf(s.origin) < 0)
        return result('ASK_HUMAN', 'INVALID_EVIDENCE_SCHEMA');
      if (!Number.isInteger(s.start) || !Number.isInteger(s.end) || typeof s.quote !== 'string') return result('ASK_HUMAN', 'INVALID_EVIDENCE_OFFSET');
      if (!(0 <= s.start && s.start < s.end && s.end <= cps.length) || cps.slice(s.start, s.end).join('') !== s.quote)
        return result('ASK_HUMAN', 'EVIDENCE_OFFSET_MISMATCH');
    }
    if (contradictions(spans)) return result('ASK_HUMAN', 'CONFLICTING_EVIDENCE_ANNOTATIONS');
    if (spans.some(function (s) { return s.origin === 'MODEL_PROPOSED'; })) return result('ASK_HUMAN', 'UNVERIFIED_MODEL_EVIDENCE');
    var direct = spans.filter(function (s) { return s.directness === 'DIRECT_REQUEST'; });
    var risk = direct.filter(function (s) { return C.dangerous.indexOf(s.kind) >= 0; });
    if (risk.length) return result('PAUSE_AND_VERIFY', 'CONFIRMED_DIRECT_RISK_REQUEST', risk);
    if (status !== 'OK') return result('ASK_HUMAN', 'MODEL_NOT_AVAILABLE');
    if (review || spans.some(function (s) { return s.directness === 'UNCLEAR'; })) return result('ASK_HUMAN', 'AMBIGUOUS_DIRECTNESS');
    var caution = direct.filter(function (s) { return C.cautionary.indexOf(s.kind) >= 0; });
    if (caution.length) return result('CAUTION', 'CONFIRMED_CAUTIONARY_REQUEST', caution);
    if (spans.length && spans.some(function (s) { return s.directness === 'REPORTED_OR_QUOTED'; })) return result('CAUTION', 'REPORTED_ACTION_NOT_DIRECT_REQUEST');
    return result('NO_STRONG_SIGNAL', 'NO_VALIDATED_DIRECT_REQUEST');
  }
  var FIXTURES = {}; D.fixtures.forEach(function (f) { FIXTURES[f.id] = f; });
  // Mirrors Store.process(): fixtures are annotated (status OK); free text has no model (NOT_CONNECTED).
  function evaluateTurn(input) {
    if (input.fixture_id !== undefined) {
      var f = FIXTURES[input.fixture_id]; if (!f) throw new Error('UNKNOWN_FIXTURE');
      return decide(f.transcript, f.evidence, { status: input.simulate_failure ? 'UNAVAILABLE' : 'OK',
        user_asks_review: input.fixture_id === 'AMBIGUOUS' ? true : !!input.user_asks_review });
    }
    if (typeof input.text !== 'string' || cpLen(input.text) > 2000) throw new Error('INVALID_TEXT');
    return decide(input.text, [], { status: input.simulate_failure ? 'UNAVAILABLE' : 'NOT_CONNECTED', user_asks_review: !!input.user_asks_review });
  }

  // ---------- typed contract ----------
  function prob(p) {
    if (typeof p !== 'number' || !isFinite(p) || p < 0 || p > 1) throw ContractError('INVALID_PROBABILITY');
    return p;
  }
  function scoreProbabilities(probs, options) {
    if (!isPlainObject(probs)) throw ContractError('INVALID_OPTIONS');
    var keys = Object.keys(probs);
    if (sameSet(keys, options)) return [probs, 'LABEL_KEYS'];
    var idx = options.map(function (_, i) { return String(i); });
    if (sameSet(keys, idx)) { var m = {}; options.forEach(function (o, i) { m[o] = probs[String(i)]; }); return [m, 'INDEX_KEYS']; }
    throw ContractError('INVALID_OPTIONS');
  }
  function argmax(parsed, options) {
    var top = Math.max.apply(null, options.map(function (o) { return parsed[o]; }));
    var w = options.filter(function (o) { return Math.abs(parsed[o] - top) <= 1e-8; });
    if (w.length !== 1) throw ContractError('TIED_ARGMAX');
    return w[0];
  }
  function normalizeStrict(answers, spec, order) {
    var out = {};
    for (var name of order) {
      var a = answers[name], req = spec[name];
      if (!isPlainObject(a) || !isPlainObject(req)) throw ContractError('INVALID_ANSWER_OBJECT');
      var typ = req.type;
      if (Object.prototype.hasOwnProperty.call(a, 'type') && a.type !== typ) throw ContractError('ANSWER_TYPE_MISMATCH');
      if (typ === 'noul') {
        var p = prob(a.noul); out[name] = { type: 'noul', probabilities: { yes: p, no: 1 - p } };
      } else if (typ === 'choice' || typ === 'score') {
        var options = req.options;
        if (!Array.isArray(options) || options.length < 2 || options.some(function (o) { return typeof o !== 'string'; }) || new Set(options).size !== options.length)
          throw ContractError('INVALID_CHOICE_SPEC');
        var probs = a.probabilities, has = Object.prototype.hasOwnProperty;
        var winner = typ === 'choice' ? (has.call(a, 'choice') ? a.choice : null) : (has.call(a, 'score') ? a.score : null);
        var keyFormat = 'LABEL_KEYS';
        if (typ === 'score') { var sp = scoreProbabilities(probs, options); probs = sp[0]; keyFormat = sp[1]; }
        if (!isPlainObject(probs) || !sameSet(Object.keys(probs), options)) throw ContractError('INVALID_OPTIONS');
        var parsed = {}; options.forEach(function (o) { parsed[o] = prob(probs[o]); });
        var sum = options.reduce(function (t, o) { return t + parsed[o]; }, 0);
        if (Math.abs(sum - 1) > 0.002) throw ContractError('PROBABILITIES_NOT_NORMALIZED');
        var top = Math.max.apply(null, options.map(function (o) { return parsed[o]; }));
        if (typ === 'choice') {
          if (winner === null) winner = argmax(parsed, options);
          if (options.indexOf(winner) < 0 || parsed[winner] + 1e-8 < top) throw ContractError('INCONSISTENT_CHOICE');
          out[name] = { type: typ, choice: winner, probabilities: parsed };
        } else {
          if (winner === null) winner = argmax(parsed, options);
          if (typeof winner === 'boolean') throw ContractError('INVALID_SCORE');
          if (keyFormat === 'INDEX_KEYS' && typeof winner === 'string' && /^[0-9]+$/.test(winner) && parseInt(winner, 10) < options.length)
            winner = options[parseInt(winner, 10)];
          if ((typeof winner !== 'number' && typeof winner !== 'string') || (typeof winner === 'string' && options.indexOf(winner) < 0) ||
              (typeof winner === 'number' && (!isFinite(winner) || winner < 0 || winner > options.length - 1)))
            throw ContractError('INVALID_SCORE');
          if (typeof winner === 'string' && parsed[winner] + 1e-8 < top) throw ContractError('INCONSISTENT_SCORE');
          out[name] = { type: typ, score: winner, probabilities: parsed, key_format: keyFormat };
        }
      } else throw ContractError('UNKNOWN_QUESTION_TYPE');
    }
    return out;
  }
  function normalizeResponse(body, spec, opts) {
    opts = opts || {};
    var order = opts.order || Object.keys(spec || {});
    var optional = opts.optional || [];
    if (!isPlainObject(body) || !isPlainObject(spec) || !Object.keys(spec).length) throw ContractError('INVALID_ENVELOPE');
    if (!subset(optional, Object.keys(spec))) throw ContractError('INVALID_OPTIONAL_SPEC');
    var answers = body.answers;
    var required = order.filter(function (k) { return optional.indexOf(k) < 0; });
    if (!isPlainObject(answers) || !subset(required, Object.keys(answers)) || !subset(Object.keys(answers), Object.keys(spec)))
      throw ContractError('ANSWER_KEYS_MISMATCH');
    if (!optional.length) return normalizeStrict(answers, spec, order);
    var out = {}, dropped = [];
    for (var name of order) {
      if (!Object.prototype.hasOwnProperty.call(answers, name)) { if (optional.indexOf(name) >= 0) dropped.push(name); continue; }
      try { var one = {}; one[name] = spec[name]; Object.assign(out, normalizeStrict(answers, one, [name])); }
      catch (e) { if (e.name !== 'ContractError' || optional.indexOf(name) < 0) throw e; dropped.push(name); }
    }
    out._dropped_optional = dropped.sort();
    return out;
  }

  // ---------- model advisory ----------
  function chooseAnchor(text, action, within) {
    var options = M.anchors[action] || [], lo = within ? within[0] : 0, hi = within ? within[1] : text.length, hits = [];
    for (var a of options) {
      var r = new RegExp(escapeRx(a), 'giu'), m;
      while ((m = r.exec(text)) !== null) {
        if (lo <= m.index && m.index + m[0].length <= hi) { hits.push([m.index, m.index + m[0].length, m[0]]); break; }
        if (m[0].length === 0) r.lastIndex++;
      }
    }
    hits.sort(function (x, y) { return x[0] - y[0] || x[1] - y[1] || (x[2] < y[2] ? -1 : x[2] > y[2] ? 1 : 0); });
    return hits.length ? hits[0] : null;
  }
  function advisory(text, raw, opts) {
    opts = opts || {};
    var source = opts.source || 'MODEL_RESPONSE_UNATTESTED';
    var threshold = opts.threshold === undefined ? M.default_threshold : opts.threshold;
    if (typeof text !== 'string' || !pyStrip(text) || cpLen(text) > 2000) throw ContractError('INVALID_TEXT');
    if (typeof threshold !== 'number' || !(threshold >= 0.5 && threshold <= 0.99)) throw ContractError('INVALID_THRESHOLD');
    var n = normalizeResponse(raw, M.spec, { optional: M.optional, order: M.spec_order });
    var dropped = n._dropped_optional || []; delete n._dropped_optional;
    var flags = contextFlags(text), profile = clauseProfile(text);
    var a = n.q_action.choice, sp = n.q_speech.choice;
    var pa = n.q_action.probabilities[a], ps = n.q_speech.probabilities[sp];
    var probs = {}; M.spec_order.forEach(function (k) { if (n[k]) probs[k] = n[k].probabilities; });
    var out = { source: source, model_attested: false, calibration_status: 'NOT_ESTABLISHED', threshold_type: 'UNVALIDATED_DEMO_HEURISTIC',
      probs: probs, dropped_optional_questions: dropped, calibration_temperature: M.calibration_temperature, guard_scope: 'CLAUSE_LOCAL_LEXICAL_V42',
      selected_action: a, selected_speech: sp, action_probability: pa, speech_probability: ps, threshold: threshold,
      grounding: 'NO_ACTION_ANCHOR', evidence: [] };
    var scam = n.q_scam.probabilities.yes, press = n.q_pressure.probabilities.yes, action, reason;
    var conflict = contextConflict(a, sp, flags, profile);
    if (conflict) { action = 'ASK_HUMAN'; reason = conflict; }
    else if (pa < threshold || ps < threshold || a === 'unclear' || sp === 'unclear') { action = 'ASK_HUMAN'; reason = 'MODEL_LOW_CONFIDENCE_OR_AMBIGUOUS'; }
    else if (a === 'none' && (scam >= threshold || (press >= threshold && flags.pressure_cue))) { action = 'ASK_HUMAN'; reason = 'CONFLICTING_MODEL_QUESTIONS'; }
    else if (sp === 'informational') {
      if (flags.pressure_cue && (scam >= threshold || press >= threshold)) { action = 'ASK_HUMAN'; reason = 'AUX_COERCION_BLOCKS_INFORMATIONAL_CLEARANCE'; }
      else { action = 'NO_STRONG_SIGNAL'; reason = 'MODEL_INFORMATIONAL_NOT_REQUEST'; }
    }
    else if (a === 'none') { action = 'NO_STRONG_SIGNAL'; reason = 'NO_ACTION_CANDIDATE_NOT_SAFETY_CLEARANCE'; }
    else {
      var anchor = null;
      if (sp === 'direct_request') for (var c of profile) { if (!c.clean_action) continue; anchor = chooseAnchor(text, a, [c.u16start, c.u16end]); if (anchor) break; }
      anchor = anchor || chooseAnchor(text, a);
      var origin = 'MODEL_SCHEMA_CHECKED', cpStart = null, cpEnd = null;
      if (anchor) { cpStart = cpIndex(text, anchor[0]); cpEnd = cpIndex(text, anchor[1]); }
      else if (opts.model_anchor) {
        // v4.5: on-device attribution span (code-point offsets), accepted only if it matches the text exactly.
        var ma = opts.model_anchor, cps = Array.from(text);
        if (Array.isArray(ma) && ma.length === 3 && Number.isInteger(ma[0]) && Number.isInteger(ma[1]) && typeof ma[2] === 'string' &&
            ma[0] >= 0 && ma[0] < ma[1] && ma[1] <= cps.length && cps.slice(ma[0], ma[1]).join('') === ma[2] && pyStrip(ma[2])) {
          anchor = ma; cpStart = ma[0]; cpEnd = ma[1]; origin = 'MODEL_ATTRIBUTION_SPAN';
        }
      }
      var aux = flags.pressure_cue && (scam >= threshold || press >= threshold);
      if (!anchor) { action = 'ASK_HUMAN'; reason = 'NO_GROUNDED_ACTION_ANCHOR'; }
      else {
        out.grounding = origin === 'MODEL_SCHEMA_CHECKED' ? 'LEXICAL_ANCHOR_NOT_SEMANTIC_VERIFICATION' : 'MODEL_ATTRIBUTION_SPAN_NOT_SEMANTIC_PROOF';
        out.evidence = [{ start: cpStart, end: cpEnd, quote: anchor[2], kind: M.kind_map[a],
          directness: M.speech_map[sp], origin: origin }];
        if (sp === 'negated_or_warning' && aux) { action = 'ASK_HUMAN'; reason = 'AUX_COERCION_BLOCKS_WARNING_CLEARANCE'; }
        else if (sp === 'negated_or_warning') { action = 'NO_STRONG_SIGNAL'; reason = 'MODEL_WARNING_NOT_REQUEST'; }
        else if (sp === 'reported_or_quoted') { action = 'CAUTION'; reason = 'MODEL_REPORTED_REQUEST'; }
        else if (['transfer', 'otp', 'remote_install', 'personal_data'].indexOf(a) >= 0) { action = 'PAUSE_AND_VERIFY'; reason = 'MODEL_DIRECT_ACTION_ADVISORY'; }
        else { action = 'CAUTION'; reason = 'MODEL_DIRECT_CAUTION_ADVISORY'; }
      }
    }
    if (n.q_evidence && n.q_evidence.probabilities.no >= threshold && (action === 'NO_STRONG_SIGNAL' || action === 'CAUTION')) {
      action = 'ASK_HUMAN'; reason = 'MODEL_EVIDENCE_INSUFFICIENT';   // v4.5 / PRD v3.3 rule 6
    }
    out.action = action; out.reason = reason; out.message = C.messages[action]; out.mode = source + ' / NOT_ATTESTED';
    return out;
  }
  // ---------- v4.7 decision-relevant arbiter (port of model_bridge.decision_relevant_advisory) ----------
  function draTruth(ac, sc) {
    if (ac === 'NONE') return 'NO_STRONG_SIGNAL';
    if (ac === 'UNK' || sc === 'UNK') return 'UNKNOWN';
    if (sc === 'CLEAR') return 'NO_STRONG_SIGNAL';
    if (sc === 'REPORT') return 'CAUTION';
    return ac === 'HIGH' ? 'PAUSE_AND_VERIFY' : 'CAUTION';
  }
  function draNorm(d, keys) { var s = 0, o = {}; keys.forEach(function (k) { s += d[k]; }); keys.forEach(function (k) { o[k] = s > 0 ? d[k] / s : 0; }); return o; }
  function argmaxKeys(d, keys) { var b = keys[0]; keys.forEach(function (k) { if (d[k] > d[b]) b = k; }); return b; }
  function decisionRelevantAdvisory(text, raw, opts) {
    opts = opts || {};
    var R = M.dra, source = opts.source || 'MODEL_RESPONSE_UNATTESTED';
    if (typeof text !== 'string' || !pyStrip(text) || cpLen(text) > 2000) throw ContractError('INVALID_TEXT');
    var Cst = opts.costs === undefined ? R.costs : opts.costs;
    if (!isPlainObject(Cst) || !sameSet(Object.keys(Cst), R.outputs) || R.outputs.some(function (o) {
      var v = Cst[o]; return !Array.isArray(v) || v.length !== 4 || v.some(function (x) { return typeof x !== 'number' || !isFinite(x) || x < 0; }); }))
      throw ContractError('INVALID_COSTS');
    var n = normalizeResponse(raw, M.spec, { optional: M.optional, order: M.spec_order }); delete n._dropped_optional;
    var flags = contextFlags(text), profile = clauseProfile(text), AO = R.action_options, SO = R.speech_options, trace = [];
    var pa = {}, ps = {}; AO.forEach(function (k) { pa[k] = n.q_action.probabilities[k]; }); SO.forEach(function (k) { ps[k] = n.q_speech.probabilities[k]; });
    var spanOk = false, ma = opts.model_anchor, cps = Array.from(text);
    if (ma !== undefined && ma !== null) spanOk = Array.isArray(ma) && ma.length === 3 && Number.isInteger(ma[0]) && Number.isInteger(ma[1]) && typeof ma[2] === 'string' &&
      ma[0] >= 0 && ma[0] < ma[1] && ma[1] <= cps.length && cps.slice(ma[0], ma[1]).join('') === ma[2] && !!pyStrip(ma[2]);
    var topAction = argmaxKeys(pa, AO), anchors = {}, structural = structuralEvidence(text);
    AO.forEach(function (a) {
      if (R.action_class[a] !== 'HIGH' && R.action_class[a] !== 'MID') return;
      var h = chooseAnchor(text, a); anchors[a] = h ? [cpIndex(text, h[0]), cpIndex(text, h[1]), h[2]] : null;
      if (anchors[a] === null) {
        var st = structural.filter(function (e) { return (R.structural_grounds[a] || []).indexOf(e.kind) >= 0; });
        if (st.length) anchors[a] = [st[0].start, st[0].end, st[0].quote];
      }
      if (anchors[a] === null) { pa[a] = pa[a] * R.ungrounded_discount; trace.push('UNGROUNDED_' + a.toUpperCase()); }
    });
    pa = draNorm(pa, AO);
    var acts = profile.filter(function (c) { return c.flags.action_mentioned; });
    var imperative = acts.filter(function (c) { return c.clean_imperative; });
    if (imperative.length) { ps.direct_request = ps.direct_request * R.imperative_boost; trace.push('CLEAN_IMPERATIVE_ACTION_CLAUSE'); }
    else if (acts.length && acts.every(function (c) { return c.flags.warning_cue || c.flags.report_cue; })) {
      ps.negated_or_warning = ps.negated_or_warning * R.warning_boost; ps.reported_or_quoted = ps.reported_or_quoted * R.warning_boost;
      trace.push('ALL_ACTION_CLAUSES_WARNED_OR_REPORTED');
    }
    ps = draNorm(ps, SO);
    var q = { NO_STRONG_SIGNAL: 0, CAUTION: 0, PAUSE_AND_VERIFY: 0, UNKNOWN: 0 };
    AO.forEach(function (a) {
      var ac = R.action_class[a];
      if (ac === 'NONE' || ac === 'UNK') { q[draTruth(ac, 'DIRECT')] += pa[a]; return; }
      SO.forEach(function (s) { q[draTruth(ac, R.speech_class[s])] += pa[a] * ps[s]; });
    });
    var scam = n.q_scam.probabilities.yes, press = n.q_pressure.probabilities.yes, moved;
    if (flags.pressure_cue && Math.max(scam, press) >= 0.7) { moved = q.NO_STRONG_SIGNAL * 0.5; q.NO_STRONG_SIGNAL -= moved; q.UNKNOWN += moved; trace.push('AUX_COERCION_WITH_PRESSURE_CUE'); }
    if (n.q_evidence) {
      var evNo = n.q_evidence.probabilities.no;
      moved = q.NO_STRONG_SIGNAL * evNo * 0.5; q.NO_STRONG_SIGNAL -= moved; q.UNKNOWN += moved;
      if (evNo >= 0.5) trace.push('MODEL_EVIDENCE_DOUBT');
    }
    var order = ['NO_STRONG_SIGNAL', 'CAUTION', 'PAUSE_AND_VERIFY', 'UNKNOWN'], exp = {};
    R.outputs.forEach(function (o) { var acc = 0; order.forEach(function (t, i) { acc += q[t] * Cst[o][i]; }); exp[o] = acc; });
    var protect = { NO_STRONG_SIGNAL: 0, CAUTION: 1, ASK_HUMAN: 2, PAUSE_AND_VERIFY: 3 };
    var ranked = R.outputs.slice().sort(function (x, y) { var d = exp[x] - exp[y]; if (Math.abs(d) > 1e-9) return d < 0 ? -1 : 1; return protect[y] - protect[x]; });
    var choice = ranked[0], evidence = [], grounding = 'NO_ACTION_ANCHOR';
    if (choice === 'PAUSE_AND_VERIFY' || choice === 'CAUTION') {
      var allowed = choice === 'PAUSE_AND_VERIFY' ? ['HIGH'] : ['HIGH', 'MID'];
      var cand = AO.filter(function (a) { return allowed.indexOf(R.action_class[a]) >= 0; });
      cand.sort(function (x, y) { return (pa[y] - pa[x]) || (AO.indexOf(x) - AO.indexOf(y)); });
      for (var i = 0; i < cand.length; i++) {
        var a = cand[i], anc = anchors[a], origin = 'MODEL_SCHEMA_CHECKED';
        if (!anc && spanOk && a === topAction && choice === 'CAUTION') { anc = ma; origin = 'MODEL_ATTRIBUTION_SPAN'; }
        if (anc) {
          evidence = [{ start: anc[0], end: anc[1], quote: anc[2], kind: M.kind_map[a], directness: M.speech_map[argmaxKeys(ps, SO)], origin: origin }];
          grounding = origin === 'MODEL_SCHEMA_CHECKED' ? 'LEXICAL_ANCHOR_NOT_SEMANTIC_VERIFICATION' : 'MODEL_ATTRIBUTION_SPAN_NOT_SEMANTIC_PROOF';
          break;
        }
      }
      if (!evidence.length && choice === 'PAUSE_AND_VERIFY') { choice = ranked.filter(function (o) { return o !== 'PAUSE_AND_VERIFY'; })[0]; trace.push('PAUSE_WITHOUT_ANCHOR_DEMOTED'); }
    }
    var reason = { NO_STRONG_SIGNAL: 'DRA_MIN_EXPECTED_COST_CLEAR', CAUTION: 'DRA_MIN_EXPECTED_COST_CAUTION', ASK_HUMAN: 'DRA_DECISION_RELEVANT_UNCERTAINTY', PAUSE_AND_VERIFY: 'DRA_MIN_EXPECTED_COST_PAUSE' }[choice];
    return { source: source, model_attested: false, arbiter: R.version, cost_table: 'DESIGN_CHOICE_NOT_VALIDATED', action: choice, reason: reason,
      message: C.messages[choice], mode: source + ' / NOT_ATTESTED', guidance_distribution: q, expected_cost: exp, margin: exp[ranked[1]] - exp[ranked[0]],
      trace: trace, evidence: evidence, grounding: grounding, selected_action: topAction, selected_speech: argmaxKeys(ps, SO) };
  }
  // ---------- v4.6 structural evidence + risk-indicator policy (ports of context_guard / model_bridge) ----------
  var STRUCT = (G.structural || []).map(function (p) { return { kind: p.kind, re: new RegExp(p.source, p.flags + 'g') }; });
  function structuralEvidence(text) {
    if (typeof text !== 'string') throw new TypeError('TEXT_REQUIRED');
    var out = [];
    STRUCT.forEach(function (p) {
      p.re.lastIndex = 0; var lastEnd = -1, m;
      while ((m = p.re.exec(text)) !== null) {
        if (m[0].length === 0) { p.re.lastIndex++; continue; }
        if (m.index < lastEnd) continue;
        var q = pyStrip(m[0]); if (!q) continue;
        var lead = m[0].length - m[0].replace(/^[\s\x1c-\x1f\x85]+/u, '').length, s16 = m.index + lead;
        var s = cpIndex(text, s16);
        out.push({ kind: p.kind, start: s, end: s + cpLen(q), quote: q });
        lastEnd = m.index + m[0].length;
      }
    });
    out.sort(function (a, b) { return a.start - b.start || a.end - b.end || (a.kind < b.kind ? -1 : a.kind > b.kind ? 1 : 0); });
    return out.slice(0, 20);
  }
  function validSpan(text, sp) {
    if (!Array.isArray(sp) || sp.length !== 3) return null;
    var s = sp[0], e = sp[1], q = sp[2], cps = Array.from(text);
    if (Number.isInteger(s) && Number.isInteger(e) && typeof q === 'string' && s >= 0 && s < e && e <= cps.length &&
        cps.slice(s, e).join('') === q && pyStrip(q)) return [s, e, q];
    return null;
  }
  function indicatorAdvisory(text, base, probs, opts) {
    opts = opts || {};
    if (typeof text !== 'string' || !pyStrip(text) || cpLen(text) > 2000) throw ContractError('INVALID_TEXT');
    if (!isPlainObject(base) || C.actions.indexOf(base.action) < 0 || typeof base.reason !== 'string') throw ContractError('INVALID_BASE_ADVISORY');
    if (!isPlainObject(probs) || !subset(Object.keys(probs), M.indicators)) throw ContractError('INVALID_INDICATORS');
    Object.keys(probs).forEach(function (k) { var v = probs[k]; if (typeof v !== 'number' || !(v >= 0 && v <= 1)) throw ContractError('INVALID_INDICATORS'); });
    var thr = {}; M.indicators.forEach(function (k) { thr[k] = 0.5; });
    if (opts.thresholds !== undefined && opts.thresholds !== null) {
      if (!isPlainObject(opts.thresholds) || !subset(Object.keys(opts.thresholds), M.indicators)) throw ContractError('INVALID_THRESHOLD');
      Object.keys(opts.thresholds).forEach(function (k) { var v = opts.thresholds[k]; if (typeof v !== 'number' || !(v >= 0.05 && v <= 0.95)) throw ContractError('INVALID_THRESHOLD'); thr[k] = v; });
    }
    var spans = {};
    if (isPlainObject(opts.model_spans)) Object.keys(opts.model_spans).forEach(function (k) { if (M.indicators.indexOf(k) >= 0) { var v = validSpan(text, opts.model_spans[k]); if (v) spans[k] = v; } });
    var structural = structuralEvidence(text);
    var fired = M.indicators.filter(function (k) { return Object.prototype.hasOwnProperty.call(probs, k) && probs[k] >= thr[k]; });
    var report = fired.map(function (k) {
      var grounds = M.structural_grounds[k] || [];
      var ev = structural.filter(function (e) { return grounds.indexOf(e.kind) >= 0; }).map(function (e) { return { kind: e.kind, start: e.start, end: e.end, quote: e.quote, origin: 'STRUCTURAL' }; });
      var by = ev.length ? 'STRUCTURAL' : 'NONE';
      if (spans[k]) { ev.push({ kind: 'MODEL_ATTRIBUTION', start: spans[k][0], end: spans[k][1], quote: spans[k][2], origin: 'MODEL_ATTRIBUTION_SPAN' }); if (by === 'NONE') by = 'MODEL_ONLY'; }
      return { label: k, probability: probs[k], threshold: thr[k], grounded: by === 'STRUCTURAL', grounded_by: by, evidence: ev };
    });
    var structuralOk = report.filter(function (r) { return r.grounded; }).map(function (r) { return r.label; });
    var strongModelOnly = report.filter(function (r) { return !r.grounded && r.probability >= Math.max(r.threshold, M.ungrounded_min_probability); }).map(function (r) { return r.label; });
    var has = function (arr, set) { return arr.some(function (x) { return set.indexOf(x) >= 0; }); };
    var speech = base.selected_speech, both = M.primary_indicators.concat(M.high_severity_indicators);
    var warning = M.warning_clearances.indexOf(base.reason) >= 0 || speech === 'negated_or_warning', action = base.action, reason = base.reason;
    if (action !== 'PAUSE_AND_VERIFY' && !warning) {
      if (has(structuralOk, M.high_severity_indicators) && speech === 'direct_request') { action = 'PAUSE_AND_VERIFY'; reason = 'GROUNDED_HIGH_SEVERITY_INDICATOR'; }
      else if (action === 'NO_STRONG_SIGNAL') {
        if (has(structuralOk, both)) { action = 'CAUTION'; reason = 'RISK_INDICATORS_WITHOUT_EXPLICIT_ACTION'; }
        else if (has(strongModelOnly, both)) { action = 'ASK_HUMAN'; reason = 'UNGROUNDED_RISK_INDICATOR'; }
      }
    }
    var out = Object.assign({}, base, { base_action: base.action, base_reason: base.reason, action: action, reason: reason,
      message: C.messages[action], indicators: report, structural_evidence: structural, sender_identity: 'UNVERIFIED',
      indicator_policy: 'V46_NEVER_DOWNGRADES' });
    return out;
  }
  function questions(state) {
    var q = {}; M.spec_order.forEach(function (k) {
      var question = JSON.parse(JSON.stringify(M.questions[k]));
      if (question.type === 'choice') {
        // JSON export sorts object keys, but the model encodes choices in insertion order.
        // Restore the Python contract's option array at the request boundary.
        var options = M.spec[k].options, criteria = question.criteria;
        if (!Array.isArray(options) || new Set(options).size !== options.length ||
            !isPlainObject(criteria) || !sameSet(Object.keys(criteria), options)) {
          throw ContractError('QUESTION_CRITERIA_MISMATCH_' + k);
        }
        var ordered = {}; options.forEach(function (name) { ordered[name] = criteria[name]; });
        question.criteria = ordered;
      }
      q[k] = question;
    });
    return { state: state, questions: q };
  }
  // A fail-closed outcome identical to Store.process_model()'s failure branch.
  function modelUnavailable(code) {
    return { action: 'ASK_HUMAN', message: M.unavailable_message, reason: code, evidence: [],
      mode: 'MODEL_UNAVAILABLE_OR_INVALID / NOT_ATTESTED', source: 'MODEL_UNAVAILABLE_OR_INVALID', model_attested: false,
      calibration_status: 'NOT_ESTABLISHED', probs: {}, grounding: 'NONE' };
  }

  // ---------- PAYLOCK (structured-record policy; never a payment) ----------
  var P = D.paylock, ID_RX = rx(P.id_pattern), EMAIL_RX = rx(P.email_pattern), ACC_RX = rx(P.account_pattern);
  var VENDORS = {}; P.vendor_list.forEach(function (v) { VENDORS[v.vendor_id] = v; });
  var INVOICES = {}; P.invoice_list.forEach(function (v) { INVOICES[v.invoice_id] = v; });
  var REQUIRED = ['request_id', 'requester_id', 'invoice_id', 'vendor_id', 'sender_email', 'requested_bank', 'requested_account', 'amount_krw', 'message'];
  function normalizeAccount(raw) {
    if (typeof raw !== 'string' || cpLen(raw) > 40) throw PaylockError('INVALID_ACCOUNT');
    for (var ch of raw) if ('0123456789- '.indexOf(ch) < 0) throw PaylockError('INVALID_ACCOUNT');
    var compact = raw.replace(/-/g, '').replace(/ /g, '');
    if (!ACC_RX.test(compact)) throw PaylockError('INVALID_ACCOUNT');
    return compact;
  }
  function validateRequest(p) {
    if (!isPlainObject(p) || !sameSet(Object.keys(p), REQUIRED)) throw PaylockError('PAYLOCK_REQUEST_CONTRACT');
    for (var k of ['request_id', 'requester_id', 'invoice_id', 'vendor_id'])
      if (typeof p[k] !== 'string' || !ID_RX.test(p[k])) throw PaylockError('INVALID_' + k.toUpperCase());
    if (typeof p.sender_email !== 'string' || !EMAIL_RX.test(p.sender_email)) throw PaylockError('INVALID_SENDER_CLAIM');
    if (typeof p.requested_bank !== 'string' || P.banks.indexOf(p.requested_bank) < 0) throw PaylockError('INVALID_BANK_CODE');
    if (typeof p.amount_krw !== 'number' || !Number.isInteger(p.amount_krw) || p.amount_krw < 1 || p.amount_krw > 1e10) throw PaylockError('INVALID_AMOUNT');
    if (typeof p.message !== 'string' || cpLen(p.message) > 1500) throw PaylockError('INVALID_MESSAGE');
    var n = Object.assign({}, p); n.requested_account = normalizeAccount(p.requested_account); return n;
  }
  function assessRequest(payload, modelSignals) {
    var p = validateRequest(payload), sig = modelSignals || [];
    if (!Array.isArray(sig) || sig.some(function (x) { return ['MODEL_URGENCY_CUE', 'MODEL_CHANGE_CUE', 'MODEL_UNAVAILABLE'].indexOf(x) < 0; }))
      throw PaylockError('INVALID_MODEL_SIGNALS');
    var reasons = [], v = VENDORS[p.vendor_id], inv = INVOICES[p.invoice_id];
    if (!v || !inv || inv.vendor_id !== p.vendor_id) reasons.push('UNKNOWN_VENDOR_INVOICE_PAIR');
    else {
      if (p.sender_email !== v.known_email) reasons.push('SENDER_CLAIM_DIFFERS_FROM_DIRECTORY');
      if (p.requested_bank !== v.bank || p.requested_account !== v.account) reasons.push('BANK_ACCOUNT_CHANGED');
      if (p.amount_krw !== inv.amount_krw) reasons.push('INVOICE_AMOUNT_MISMATCH');
    }
    var low = p.message.toLowerCase();
    if (P.urgency_tokens.some(function (t) { return low.indexOf(t) >= 0; })) reasons.push('LEXICAL_URGENCY_ONLY_UNVERIFIED');
    if (externalDirectiveFlags(p.message).length) reasons.push('UNTRUSTED_MESSAGE_INSTRUCTION_CUE');
    reasons = reasons.concat(sig);
    reasons = reasons.filter(function (x, i) { return reasons.indexOf(x) === i; });
    if (reasons.length) return { disposition: 'HOLD_FOR_INDEPENDENT_VERIFICATION', reasons: reasons };
    return { disposition: 'READY_FOR_INTERNAL_REVIEW_NOT_PAYMENT', reasons: ['DIRECTORY_FIELDS_MATCH_UNVERIFIED_SENDER'] };
  }

  // ---------- in-memory session (no raw text kept; version-bound retries) ----------
  function Session() { this.version = 0; this.history = []; this.idem = new Map(); }
  Session.prototype.record = function (turnId, version, digestInput, compute) {
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(turnId) || !Number.isInteger(version)) throw new Error('INVALID_TURN_OR_VERSION');
    var key = turnId, ident = JSON.stringify([version, digestInput]);
    if (this.idem.has(key)) { var prior = this.idem.get(key); if (prior[0] !== ident) throw new Error('CONFLICTING_RETRY'); return prior[1]; }
    if (version !== this.version) throw new Error('STALE_VERSION');
    var r = compute(); this.version += 1;
    this.history.push({ turn_id: turnId, version: this.version, action: r.action, reason: r.reason, mode: r.mode });
    var res = Object.assign({ version: this.version }, r); this.idem.set(key, [ident, res]); return res;
  };

  return {
    version: '4.7', data: D, fixtures: D.fixtures, examples: P.examples, vendors: P.vendor_list, invoices: P.invoice_list,
    messages: C.messages, questions: questions, decide: decide, evaluateTurn: evaluateTurn, advisory: advisory,
    structuralEvidence: structuralEvidence, indicatorAdvisory: indicatorAdvisory, decisionRelevantAdvisory: decisionRelevantAdvisory,
    normalizeResponse: normalizeResponse, contextFlags: contextFlags, clauseProfile: clauseProfile,
    contextConflict: contextConflict, externalDirectiveFlags: externalDirectiveFlags, validateRequest: validateRequest,
    assessRequest: assessRequest, normalizeAccount: normalizeAccount, strictJSON: strictJSON, modelUnavailable: modelUnavailable,
    Session: Session, cpLen: cpLen
  };
});
