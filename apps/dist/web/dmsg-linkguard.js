/*
 * LinkGuard on-device port (linkguard/intake.py + linkguard/policy.py).
 * Reference data comes from apps/shared/linkguard-data.js, generated from Python by tools/linkguard/export_linkguard_data.py.
 * Offsets are Unicode code points, as in Python. No network calls; nothing is opened or fetched.
 * Equality with Python is checked by apps/conformance/run_linkguard.js.
 */
(function (root, factory) {
  var api = factory(root.LINKGUARD_DATA || (typeof require === 'function' ? (require('./linkguard-data.js'), root.LINKGUARD_DATA) : null));
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.LinkGuard = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (D) {
  'use strict';
  if (!D) throw new Error('LINKGUARD_DATA_MISSING');
  var SCHEME_CLASS = D.scheme_class, TLDS = D.tlds;
  var SET = function (a) { var s = new Set(); a.forEach(function (x) { s.add(x); }); return s; };
  var TWO = SET(D.two_level_suffixes), SHORT = SET(D.shorteners), MSG = SET(D.messenger_hosts), STORE = SET(D.app_store_hosts), SENS = SET(D.sensitive_keys);
  function cps(s) { return Array.from(s); }
  function cpLen(s) { var n = 0; for (var _ of s) n++; return n; }

  function ci(w) { return Array.from(w).map(function (c) { return (c >= 'a' && c <= 'z') ? '[' + c + c.toUpperCase() + ']' : (/[.+*?^$()|[\]{}\\\/]/.test(c) ? '\\' + c : c); }).join(''); }
  var schemes = Object.keys(SCHEME_CLASS).sort(function (a, b) { return b.length - a.length; }).map(ci).join('|');
  var tldAlt = TLDS.slice().sort(function (a, b) { return b.length - a.length; }).map(ci).join('|');
  var HOSTCH = '[A-Za-z0-9\\u00C0-\\u024F\\u0370-\\u03FF\\u0400-\\u04FF\\uAC00-\\uD7A3\\u4E00-\\u9FFF\\u3040-\\u30FF\\uFF10-\\uFF19-]';
  var URL_RX = new RegExp(
    '(?:(?<![A-Za-z0-9])(?:' + schemes + '):(?:\\/\\/)?[^\\s<>"\\u3000]+)' +
    '|(?:(?<![A-Za-z0-9@._-])(?:' + HOSTCH + '+(?:\\.|\\[\\.\\]|\\(\\.\\)))+(?:' + tldAlt + ')(?![A-Za-z0-9])(?::[0-9]{1,5})?(?:\\/[^\\s<>"\\u3000]*)?)' +
    '|(?:(?<![A-Za-z0-9.])[0-9]{1,3}(?:\\.[0-9]{1,3}){3}(?::[0-9]{1,5})?(?:\\/[^\\s<>"\\u3000]*)?)', 'gu');
  var TRAIL = ".,;:!?)]}'\"’”>";
  var OPEN_CLOSE = { ')': '(', ']': '[', '}': '{' };
  function isHangul(ch) { return (ch >= '가' && ch <= '힣') || (ch >= 'ᄀ' && ch <= 'ᇿ') || (ch >= '㄰' && ch <= '㆏'); }
  function count(arr, c) { var n = 0; arr.forEach(function (x) { if (x === c) n++; }); return n; }
  // Python's \s (str patterns) — used where the reference splits on whitespace
  function authorityEnd(a) {
    var m = /^(?:[A-Za-z][A-Za-z0-9+.-]*:(?:\/\/)?)?/.exec(a.join('')), start = m ? cpLen(m[0]) : 0;
    for (var i = start; i < a.length; i++) if ('/?#'.indexOf(a[i]) >= 0) return i;
    return a.length;
  }
  function trim(raw) {
    var a = cps(raw), he = authorityEnd(a);
    for (var i = 0; i < a.length; i++) if (i >= he && isHangul(a[i])) { a = a.slice(0, i); break; }
    while (a.length && TRAIL.indexOf(a[a.length - 1]) >= 0) {
      var c = a[a.length - 1];
      if (OPEN_CLOSE[c] && count(a, OPEN_CLOSE[c]) >= count(a, c)) break;
      a.pop();
    }
    return a.join('');
  }
  function extract(text) {
    if (typeof text !== 'string') throw new TypeError('TEXT_REQUIRED');
    text = cps(text).slice(0, D.max_text).join('');
    var out = [], m; URL_RX.lastIndex = 0;
    while ((m = URL_RX.exec(text)) !== null) {
      if (m[0].length === 0) { URL_RX.lastIndex++; continue; }
      var raw = trim(m[0]);
      if (!raw || (raw.indexOf('.') < 0 && raw.indexOf(':') < 0 && raw.indexOf('[.]') < 0)) continue;
      var st = cpLen(text.slice(0, m.index));
      out.push({ raw: raw, start: st, end: st + cpLen(raw) });
      if (out.length >= D.max_urls) break;
    }
    return out;
  }

  // ---------- punycode (RFC 3492) ----------
  var BASE = 36, TMIN = 1, TMAX = 26, SKEW = 38, DAMP = 700, IBIAS = 72, IN = 128;
  function adapt(delta, n, first) {
    delta = first ? Math.floor(delta / DAMP) : Math.floor(delta / 2);
    delta += Math.floor(delta / n); var k = 0;
    while (delta > Math.floor(((BASE - TMIN) * TMAX) / 2)) { delta = Math.floor(delta / (BASE - TMIN)); k += BASE; }
    return k + Math.floor((BASE - TMIN + 1) * delta / (delta + SKEW));
  }
  function digit(d) { return String.fromCharCode(d + 22 + 75 * (d < 26 ? 1 : 0)); }
  function punyEncode(label) {
    var c = cps(label).map(function (x) { return x.codePointAt(0); }), out = [];
    c.forEach(function (x) { if (x < 0x80) out.push(String.fromCharCode(x)); });
    var b = out.length, h = b; if (out.length) out.push('-');
    var n = IN, delta = 0, bias = IBIAS;
    while (h < c.length) {
      var m = Infinity; c.forEach(function (x) { if (x >= n && x < m) m = x; });
      delta += (m - n) * (h + 1); n = m;
      for (var i = 0; i < c.length; i++) {
        var x = c[i];
        if (x < n) delta++;
        if (x === n) {
          var q = delta, k = BASE;
          for (;;) {
            var t = k <= bias ? TMIN : (k >= bias + TMAX ? TMAX : k - bias);
            if (q < t) break;
            out.push(digit(t + (q - t) % (BASE - t))); q = Math.floor((q - t) / (BASE - t)); k += BASE;
          }
          out.push(digit(q)); bias = adapt(delta, h + 1, h === b); delta = 0; h++;
        }
      }
      delta++; n++;
    }
    return out.join('');
  }
  function punyDecode(s) {
    var b = s.lastIndexOf('-'), out = [];
    if (b > 0) for (var j = 0; j < b; j++) out.push(s.charCodeAt(j));
    var i = 0, n = IN, bias = IBIAS, pos = b > 0 ? b + 1 : 0;
    while (pos < s.length) {
      var oldi = i, w = 1, k = BASE;
      for (;;) {
        if (pos >= s.length) return null;
        var ch = s[pos++], lc = ch.toLowerCase(), d = (ch >= '0' && ch <= '9') ? ch.charCodeAt(0) - 48 + 26 : (lc >= 'a' && lc <= 'z' ? lc.charCodeAt(0) - 97 : -1);
        if (d < 0) return null;
        i += d * w;
        var t = k <= bias ? TMIN : (k >= bias + TMAX ? TMAX : k - bias);
        if (d < t) break;
        w *= BASE - t; k += BASE;
      }
      bias = adapt(i - oldi, out.length + 1, oldi === 0); n += Math.floor(i / (out.length + 1)); i %= out.length + 1;
      if (n > 0x10FFFF) return null;
      out.splice(i, 0, n); i++;
    }
    try { return out.map(function (x) { return String.fromCodePoint(x); }).join(''); } catch (e) { return null; }
  }

  // ---------- helpers ----------
  function script(ch) {
    var o = ch.codePointAt(0);
    if (o < 0x80) return /[A-Za-z]/.test(ch) ? 'LATIN' : 'COMMON';
    if (o >= 0xC0 && o <= 0x24F) return 'LATIN';
    if (o >= 0x370 && o <= 0x3FF) return 'GREEK';
    if (o >= 0x400 && o <= 0x4FF) return 'CYRILLIC';
    if ((o >= 0xAC00 && o <= 0xD7A3) || (o >= 0x1100 && o <= 0x11FF) || (o >= 0x3130 && o <= 0x318F)) return 'HANGUL';
    if (o >= 0x4E00 && o <= 0x9FFF) return 'HAN';
    if (o >= 0x3040 && o <= 0x30FF) return 'KANA';
    if (o >= 0xFF10 && o <= 0xFF19) return 'FULLWIDTH_DIGIT';
    return 'OTHER';
  }
  function ipv4Parse(host) {
    var parts = host.split('.');
    if (parts.length < 1 || parts.length > 4 || parts.some(function (p) { return p === ''; })) return [null, false];
    var vals = [], obf = parts.length !== 4;
    for (var i = 0; i < parts.length; i++) {
      var pl = parts[i].toLowerCase(), v;
      if (pl.indexOf('0x') === 0) { if (!/^[0-9a-f]*$/.test(pl.slice(2))) return [null, false]; v = pl.length > 2 ? parseInt(pl.slice(2), 16) : 0; obf = true; }
      else if (pl.length > 1 && pl[0] === '0' && /^[0-7]+$/.test(pl)) { v = parseInt(pl, 8); obf = true; }
      else if (/^[0-9]+$/.test(pl)) v = parseInt(pl, 10);
      else return [null, false];
      vals.push(v);
    }
    var P32 = 4294967296, num;
    if (vals.length === 4 && vals.every(function (v) { return v < 256; })) num = ((vals[0] * 256 + vals[1]) * 256 + vals[2]) * 256 + vals[3];
    else if (vals.length === 1 && vals[0] < P32) num = vals[0];
    else if (vals.length === 2 && vals[0] < 256 && vals[1] < 16777216) num = vals[0] * 16777216 + vals[1];
    else if (vals.length === 3 && vals[0] < 256 && vals[1] < 256 && vals[2] < 65536) num = vals[0] * 16777216 + vals[1] * 65536 + vals[2];
    else return [null, false];
    return [num, obf];
  }
  function v4Str(n) { return [Math.floor(n / 16777216) % 256, Math.floor(n / 65536) % 256, Math.floor(n / 256) % 256, n % 256].join('.'); }
  var V4 = D.v4_reserved.map(function (r) { var a = r[0].split('.').map(Number); return [((a[0] * 256 + a[1]) * 256 + a[2]) * 256 + a[3], r[1], r[2]]; });
  function v4Category(num) {
    for (var i = 0; i < V4.length; i++) {
      var size = Math.pow(2, 32 - V4[i][1]);
      if (Math.floor(num / size) * size === V4[i][0]) return V4[i][2];
    }
    return 'PUBLIC';
  }
  function v6Category(h) {
    h = h.toLowerCase();
    if (h === '::1') return 'LOOPBACK';
    if (h === '::') return 'UNSPECIFIED';
    if (h.indexOf('::ffff:') === 0) { var r = ipv4Parse(h.slice(7)); return r[0] !== null ? 'MAPPED_' + v4Category(r[0]) : 'RESERVED'; }
    var head = h.split(':')[0];
    if (!/^[0-9a-f]*$/.test(head)) return 'INVALID';
    var first = head ? parseInt(head, 16) : 0;
    if ((first & 0xFE00) === 0xFC00) return 'PRIVATE';
    if ((first & 0xFFC0) === 0xFE80) return 'LINK_LOCAL';
    if ((first & 0xFF00) === 0xFF00) return 'MULTICAST';
    if (first === 0x2001 && h.split(':')[1] === 'db8') return 'DOCUMENTATION';
    return 'PUBLIC';
  }
  function registrable(h) {
    var l = h.split('.');
    if (l.length >= 3 && TWO.has(l.slice(-2).join('.'))) return l.slice(-3).join('.');
    return l.length >= 2 ? l.slice(-2).join('.') : h;
  }
  function redactPath(path) {
    return path.split('/').map(function (s) {
      return (cpLen(s) >= 24 && /^[A-Za-z0-9_\-.~%=+]+$/.test(s) && /[0-9]/.test(s) && /[A-Za-z]/.test(s)) ? '{REDACTED}' : s;
    }).join('/');
  }
  function partition(s, sep) { var i = s.indexOf(sep); return i < 0 ? [s, '', ''] : [s.slice(0, i), sep, s.slice(i + sep.length)]; }
  function redactQuery(q) {
    if (!q) return ['', [], false];
    var keys = [], parts = [], hit = false;
    q.split('&').forEach(function (kv) {
      var p = partition(kv, '='), k = p[0], eq = p[1], v = p[2];
      keys.push(k);
      if (SENS.has(k.toLowerCase()) || (cpLen(v) >= 32 && /^[A-Za-z0-9_\-.~%=+\/]+$/.test(v || '-'))) { parts.push(k + (eq ? '=REDACTED' : '')); hit = true; }
      else parts.push(kv);
    });
    return [parts.join('&'), keys, hit];
  }
  function uniqSort(a) { return Array.from(new Set(a)).sort(); }
  function isDigits(s) { return /^[0-9]+$/.test(s); }

  function analyze(raw) {
    var flags = [], notes = [], s = raw, defanged = false;
    if (/^[hH][xX][xX][pP][sS]?:/.test(s)) { s = 'http' + s.slice(3); defanged = true; }
    if (s.indexOf('[.]') >= 0 || s.indexOf('(.)') >= 0) { s = s.split('[.]').join('.').split('(.)').join('.'); defanged = true; }
    if (defanged) flags.push('DEFANGED');
    var m = /^([A-Za-z][A-Za-z0-9+.-]*):(\/\/)?/.exec(s);
    var scheme = m && Object.prototype.hasOwnProperty.call(SCHEME_CLASS, m[1].toLowerCase()) ? m[1].toLowerCase() : '';
    var explicit = !!scheme, rest;
    if (!explicit) { scheme = 'http'; rest = s; notes.push('NO_SCHEME_ASSUMED_HTTP'); } else rest = s.slice(m[0].length);
    var sclass = SCHEME_CLASS[scheme] || 'OTHER';
    var res = { raw: raw, scheme: scheme, scheme_class: sclass, explicit_scheme: explicit };
    if (sclass === 'DEEPLINK' || sclass === 'DANGEROUS' || sclass === 'OTHER' || (sclass === 'APP_STORE' && scheme === 'market')) {
      flags.push('NON_HTTP_SCHEME');
      if (sclass === 'DANGEROUS') flags.push('DANGEROUS_SCHEME');
      if (['intent', 'kakaotalk', 'line', 'tg', 'whatsapp'].indexOf(scheme) >= 0) flags.push('MESSENGER_OR_APP_DEEPLINK');
      return Object.assign(res, { host_ascii: null, host_unicode: null, port: null, registrable_domain: null, display_url: scheme + ':' + (rest ? '…' : ''),
        external_url: null, ip: null, idn: null, query_keys: [], flags: uniqSort(flags), notes: notes, fetchable: false });
    }
    var end = rest.length;
    for (var i = 0; i < rest.length; i++) if ('/?#'.indexOf(rest[i]) >= 0) { end = i; break; }
    var authority = rest.slice(0, end), tail = rest.slice(end), userinfo = null;
    if (authority.indexOf('@') >= 0) { var at = authority.lastIndexOf('@'); userinfo = authority.slice(0, at); authority = authority.slice(at + 1); flags.push('USERINFO_AT'); }
    var port = null, host = authority;
    if (authority[0] === '[') {
      var close = authority.indexOf(']');
      host = close > 0 ? authority.slice(1, close) : authority.slice(1);
      var after = close > 0 ? authority.slice(close + 1) : '';
      if (after[0] === ':' && isDigits(after.slice(1))) port = parseInt(after.slice(1), 10);
    } else if (authority.indexOf(':') >= 0) {
      var ci = authority.lastIndexOf(':'), hp = authority.slice(0, ci), pp = authority.slice(ci + 1);
      if (isDigits(pp)) { host = hp; port = parseInt(pp, 10); }
    }
    if (port !== null && (port === 0 || port > 65535)) flags.push('INVALID_PORT');
    else if (port !== null && port !== 80 && port !== 443) flags.push('NONSTANDARD_PORT');
    host = host.replace(/\.+$/, '');
    var path = tail, query = '', hi;
    if ((hi = path.indexOf('#')) >= 0) path = path.slice(0, hi);
    if ((hi = path.indexOf('?')) >= 0) { query = path.slice(hi + 1); path = path.slice(0, hi); }
    var ip = null, hostAscii = null, hostUnicode = null, idn = null;
    if (host.indexOf(':') >= 0 && /^[0-9a-fA-F:.]+$/.test(host)) {
      ip = { version: 6, address: host.toLowerCase(), category: v6Category(host), obfuscated: false };
      hostAscii = hostUnicode = '[' + host.toLowerCase() + ']';
    } else {
      var pr = (host && /^[0-9a-fxA-FX.]+$/.test(host)) ? ipv4Parse(host) : [null, false];
      if (pr[0] !== null) {
        ip = { version: 4, address: v4Str(pr[0]), category: v4Category(pr[0]), obfuscated: pr[1] };
        hostAscii = hostUnicode = v4Str(pr[0]);
        if (pr[1]) flags.push('OBFUSCATED_IP');
      } else {
        var labels = host.split('.').map(function (l) { return l.toLowerCase(); }), asc = [], uni = [], nonascii = false, mixed = false, puny = false;
        labels.forEach(function (l) {
          var labU;
          if (l.indexOf('xn--') === 0) {
            var dec = punyDecode(l.slice(4)); puny = true;
            uni.push(dec !== null ? dec : l); asc.push(l);
            if (dec === null) notes.push('INVALID_PUNYCODE');
            labU = dec || '';
          } else if (/^[\x00-\x7f]*$/.test(l)) { asc.push(l); uni.push(l); labU = l; }
          else { nonascii = true; asc.push('xn--' + punyEncode(l)); uni.push(l); labU = l; }
          var sc = new Set(); cps(labU).forEach(function (c) { var x = script(c); if (x !== 'COMMON' && x !== 'FULLWIDTH_DIGIT') sc.add(x); });
          if (sc.size > 1 && !Array.from(sc).every(function (x) { return x === 'HAN' || x === 'KANA' || x === 'HANGUL'; })) mixed = true;
          if (cps(labU).some(function (c) { return script(c) === 'FULLWIDTH_DIGIT'; })) mixed = true;
        });
        hostAscii = asc.join('.'); hostUnicode = uni.join('.');
        var isIdn = nonascii || puny;
        idn = { is_idn: isIdn, punycode_in_text: puny, mixed_script: mixed };
        if (isIdn) flags.push('IDN');
        if (puny) flags.push('PUNYCODE');
        if (mixed) flags.push('MIXED_SCRIPT');
      }
    }
    if (ip) { flags.push('IP_LITERAL'); if (ip.category !== 'PUBLIC') flags.push('NON_PUBLIC_IP'); }
    var reg = hostAscii && !ip ? registrable(hostAscii) : null;
    if (hostUnicode && !ip) {
      var lowU = hostUnicode.toLowerCase(), skel = cps(lowU).map(function (c) { return Object.prototype.hasOwnProperty.call(D.confusables, c) ? D.confusables[c] : c; }).join('');
      var brands = Object.keys(D.brands);
      for (var bi = 0; bi < brands.length; bi++) {
        var br = brands[bi];
        if (skel.indexOf(br) >= 0 && D.brands[br].indexOf(reg) < 0) {
          flags.push(lowU.indexOf(br) < 0 ? 'HOMOGLYPH_BRAND' : 'BRAND_NOT_OFFICIAL_DOMAIN'); res.brand = br; break;
        }
      }
    }
    if (hostAscii && !ip) {
      if (SHORT.has(hostAscii) || SHORT.has(reg)) flags.push('SHORTENER');
      if (MSG.has(hostAscii) || MSG.has(reg)) flags.push('MESSENGER_LINK');
      if (STORE.has(hostAscii)) flags.push('APP_STORE_LINK');
      if (hostAscii.split('.').length >= 5) flags.push('DEEP_SUBDOMAIN');
      if (reg && ['test', 'invalid', 'example', 'localhost'].indexOf(reg.split('.').pop()) >= 0) flags.push('RESERVED_TLD');
    }
    var pl = path.toLowerCase();
    if (/\.(?:apk|xapk|apks|apkm)(?:$|[\/?#])/.test(pl) || /\.(?:apk|xapk|apks)(?:&|$)/.test(query.toLowerCase())) flags.push('APK_DOWNLOAD');
    var rq = redactQuery(query);
    if (rq[2]) flags.push('SENSITIVE_QUERY');
    var pr2 = redactPath(path);
    if (pr2 !== path) flags.push('OPAQUE_PATH_TOKEN');
    if (userinfo !== null) notes.push('USERINFO_REMOVED_FROM_DISPLAY');
    var hostport = (hostAscii || '') + (port !== null ? ':' + port : '');
    var fl = uniqSort(flags);
    return Object.assign(res, { host_ascii: hostAscii, host_unicode: hostUnicode, port: port, registrable_domain: reg,
      display_url: scheme + '://' + hostport + (pr2 || '') + (rq[0] ? '?' + rq[0] : ''), external_url: scheme + '://' + hostport + (pr2 || '/'),
      ip: ip, idn: idn, query_keys: rq[1], flags: fl, notes: notes,
      fetchable: !!hostAscii && fl.indexOf('INVALID_PORT') < 0 && !(ip && ip.category !== 'PUBLIC') });
  }

  function intake(message, opts) {
    opts = opts || {};
    if (typeof message !== 'string' || cpLen(message) > D.max_text) throw new Error('INVALID_MESSAGE');
    var found = extract(message);
    (opts.extra_urls || []).forEach(function (u) { if (typeof u === 'string' && u.trim()) found.push({ raw: cps(u.trim()).slice(0, 2048).join(''), start: null, end: null }); });
    var urls = found.slice(0, D.max_urls).map(function (f) { var a = analyze(f.raw); a.start = f.start; a.end = f.end; return a; });
    var c = opts.consent || {};
    return { message_id: opts.message_id || '', url_count: urls.length, urls: urls,
      consent: { external_reputation: !!c.external_reputation, web_analysis: !!c.web_analysis }, stage: 'INTAKE_DONE', network_used: false };
  }

  // ---------- policy (port of linkguard/policy.py) ----------
  var P = D.policy;
  function reputationLocal(u, bl) {
    if (!bl) return { provider: 'local_list', status: 'NOT_RUN', reason: 'NO_LIST_LOADED' };
    var doms = new Set(bl.domains || []);
    return { provider: 'local_list', status: 'DONE', listed: doms.has(u.host_ascii) || doms.has(u.registrable_domain), source: bl.source === undefined ? null : bl.source, as_of: bl.as_of === undefined ? null : bl.as_of };
  }
  function reputationExternal(consent, keys, provider) {
    if (!consent.external_reputation) return { provider: provider, status: 'NOT_RUN', reason: 'NO_CONSENT' };
    if (!keys) return { provider: provider, status: 'NOT_RUN', reason: 'NO_API_KEY_ON_SERVER' };
    return { provider: provider, status: 'NOT_RUN', reason: 'NOT_EXECUTED_IN_THIS_ENVIRONMENT' };
  }
  function assessUrl(u, opts) {
    var consent = opts.consent || {}, flags = u.flags || [];
    var st = { intake: 'DONE', local_reputation: null, safe_browsing: null, virustotal: null, web_analysis: null };
    var rl = reputationLocal(u, opts.blocklist || null); st.local_reputation = rl.status;
    var ext = ['google_safe_browsing', 'virustotal'].map(function (p) { return reputationExternal(consent, !!opts.keys_present, p); });
    st.safe_browsing = ext[0].status; st.virustotal = ext[1].status;
    st.web_analysis = consent.web_analysis ? P.web_analysis_status : 'NOT_RUN';
    var reasons = flags.filter(function (f) { return P.suspicious_url_flags.indexOf(f) >= 0; });
    var cautions = flags.filter(function (f) { return P.caution_url_flags.indexOf(f) >= 0; });
    var keys = ['intake', 'local_reputation', 'safe_browsing', 'virustotal', 'web_analysis'], state;
    if (rl.listed) state = 'KNOWN_MALICIOUS';
    else if (reasons.length) state = 'SUSPICIOUS';
    else if (['DEEPLINK', 'OTHER', 'APP_STORE'].indexOf(u.scheme_class) >= 0 && !u.host_ascii) state = 'NOT_SCANNED';
    else {
      var ran = keys.filter(function (k) { return st[k] === 'DONE' && k !== 'intake'; });
      state = ran.length ? 'INCONCLUSIVE' : 'NOT_SCANNED';
      if (ran.length && !cautions.length && st.local_reputation === 'DONE' && !['safe_browsing', 'virustotal', 'web_analysis'].some(function (k) { return st[k] === 'DONE'; }))
        state = 'NO_KNOWN_THREAT_FOUND';
    }
    return { display_url: u.display_url, state: state, reasons: reasons, cautions: cautions, stages: st,
      checked: keys.filter(function (k) { return st[k] === 'DONE'; }), not_checked: keys.filter(function (k) { return st[k] !== 'DONE'; }),
      reputation: [rl].concat(ext), is_safe_claim: false, note: 'NO_DETECTION_IS_NOT_SAFETY' };
  }
  function assessMessage(ir, opts) {
    opts = opts || {};
    var items = ir.urls.map(function (u) { return assessUrl(u, { consent: ir.consent || {}, blocklist: opts.blocklist, keys_present: opts.keys_present }); });
    var overall = items.length ? items.map(function (i) { return i.state; }).reduce(function (a, b) { return P.rank[b] > P.rank[a] ? b : a; }) : 'NOT_SCANNED';
    return { message_id: ir.message_id, overall: overall, urls: items, url_count: items.length, network_used: false };
  }
  function fuse(adv, link, apkState) {
    var base = (adv || {}).policy_action || 'NO_STRONG_SIGNAL';
    if (!Object.prototype.hasOwnProperty.call(P.action_rank, base)) base = 'ASK_HUMAN';
    var target = base, why = [];
    [(link || {}).overall, apkState].filter(function (x) { return x; }).forEach(function (s) {
      var want = P.link_to_action[s];
      if (want && P.action_rank[want] > P.action_rank[target]) { target = want; why.push('LINKGUARD_' + s); }
    });
    return { policy_action: target, base_action: base, escalated: target !== base, escalation_reasons: why,
      link_state: (link || {}).overall === undefined ? null : (link || {}).overall, apk_state: apkState === undefined ? null : apkState, downgraded: false };
  }
  return { version: '4.7', extract: extract, analyze: analyze, intake: intake, punycodeEncode: punyEncode, punycodeDecode: punyDecode,
    assessUrl: assessUrl, assessMessage: assessMessage, fuse: fuse, data: D };
});
