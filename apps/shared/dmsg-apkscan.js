/*
 * On-device static APK inspection (port of linkguard/apk.py). The file never leaves the device, is never installed
 * and nothing in it is executed. Same report schema as Python; checked by apps/conformance/run_apkscan.js.
 * Needs DecompressionStream('deflate-raw') and crypto.subtle (modern browsers, Android WebView 103+, Node 18+).
 * Not a malware verdict: permissions and API strings are capabilities, not intent.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ApkScan = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var MAX_APK_BYTES = 150 * 1024 * 1024, MAX_ENTRIES = 20000, MAX_ENTRY_UNCOMPRESSED = 256 * 1024 * 1024,
    MAX_TOTAL_UNCOMPRESSED = 1024 * 1024 * 1024, MAX_RATIO = 200, MAX_DEX_SCAN = 64 * 1024 * 1024;
  var ATTR_IDS = { 0x01010003: 'name', 0x01010010: 'exported', 0x0101021b: 'versionCode', 0x0101021c: 'versionName', 0x0101020c: 'minSdkVersion',
    0x01010270: 'targetSdkVersion', 0x01010006: 'permission', 0x0101000f: 'debuggable', 0x01010280: 'allowBackup', 0x010104ec: 'usesCleartextTraffic', 0x0101000e: 'enabled' };
  var DANGEROUS = { 'android.permission.READ_SMS': 'SMS', 'android.permission.RECEIVE_SMS': 'SMS', 'android.permission.SEND_SMS': 'SMS',
    'android.permission.RECEIVE_MMS': 'SMS', 'android.permission.RECEIVE_WAP_PUSH': 'SMS', 'android.permission.READ_CALL_LOG': 'CALL_LOG',
    'android.permission.WRITE_CALL_LOG': 'CALL_LOG', 'android.permission.PROCESS_OUTGOING_CALLS': 'CALL_LOG', 'android.permission.CALL_PHONE': 'PHONE',
    'android.permission.READ_PHONE_STATE': 'PHONE', 'android.permission.READ_PHONE_NUMBERS': 'PHONE', 'android.permission.ANSWER_PHONE_CALLS': 'PHONE',
    'android.permission.READ_CONTACTS': 'CONTACTS', 'android.permission.WRITE_CONTACTS': 'CONTACTS', 'android.permission.GET_ACCOUNTS': 'CONTACTS',
    'android.permission.RECORD_AUDIO': 'MICROPHONE', 'android.permission.CAMERA': 'CAMERA', 'android.permission.ACCESS_FINE_LOCATION': 'LOCATION',
    'android.permission.ACCESS_BACKGROUND_LOCATION': 'LOCATION', 'android.permission.READ_EXTERNAL_STORAGE': 'STORAGE', 'android.permission.MANAGE_EXTERNAL_STORAGE': 'STORAGE' };
  var SPECIAL = { 'android.permission.SYSTEM_ALERT_WINDOW': 'OVERLAY', 'android.permission.BIND_ACCESSIBILITY_SERVICE': 'ACCESSIBILITY',
    'android.permission.REQUEST_INSTALL_PACKAGES': 'INSTALL_PACKAGES', 'android.permission.BIND_DEVICE_ADMIN': 'DEVICE_ADMIN',
    'android.permission.BIND_NOTIFICATION_LISTENER_SERVICE': 'NOTIFICATION_LISTENER', 'android.permission.QUERY_ALL_PACKAGES': 'PACKAGE_VISIBILITY',
    'android.permission.PACKAGE_USAGE_STATS': 'USAGE_STATS', 'android.permission.BIND_VPN_SERVICE': 'VPN', 'android.permission.WRITE_SETTINGS': 'WRITE_SETTINGS',
    'android.permission.FOREGROUND_SERVICE': 'FOREGROUND_SERVICE', 'android.permission.RECEIVE_BOOT_COMPLETED': 'BOOT',
    'android.permission.USE_FULL_SCREEN_INTENT': 'FULL_SCREEN_INTENT', 'android.permission.BIND_SCREENING_SERVICE': 'CALL_SCREENING', 'android.permission.BIND_INCALL_SERVICE': 'INCALL' };
  var API_MARKERS = [
    ['Landroid/telephony/SmsManager;', 'SMS_SEND_API'], ['sendTextMessage', 'SMS_SEND_API'], ['Landroid/provider/Telephony$Sms', 'SMS_PROVIDER_READ'],
    ['content://sms', 'SMS_PROVIDER_READ'], ['Landroid/accessibilityservice/AccessibilityService;', 'ACCESSIBILITY_SERVICE'],
    ['performGlobalAction', 'ACCESSIBILITY_AUTOMATION'], ['dispatchGesture', 'ACCESSIBILITY_AUTOMATION'], ['TYPE_APPLICATION_OVERLAY', 'OVERLAY_WINDOW'],
    ['Landroid/view/WindowManager$LayoutParams;', 'WINDOW_PARAMS'], ['Ldalvik/system/DexClassLoader;', 'DYNAMIC_CODE_LOADING'],
    ['Ldalvik/system/InMemoryDexClassLoader;', 'DYNAMIC_CODE_LOADING'], ['Ldalvik/system/PathClassLoader;', 'CLASS_LOADER'], ['loadLibrary', 'NATIVE_LOAD'],
    ['Ljava/lang/System;->load', 'NATIVE_LOAD'], ['Ljava/lang/reflect/Method;', 'REFLECTION'], ['Ljava/lang/Runtime;', 'RUNTIME_EXEC'],
    ['Ljava/lang/ProcessBuilder;', 'RUNTIME_EXEC'], ['addJavascriptInterface', 'WEBVIEW_JS_BRIDGE'], ['setJavaScriptEnabled', 'WEBVIEW_JS'],
    ['setAllowFileAccess', 'WEBVIEW_FILE_ACCESS'], ['setAllowUniversalAccessFromFileURLs', 'WEBVIEW_UNIVERSAL_FILE_ACCESS'],
    ['Landroid/app/admin/DevicePolicyManager;', 'DEVICE_ADMIN_API'], ['Landroid/content/pm/PackageInstaller;', 'PACKAGE_INSTALLER'],
    ['Landroid/media/projection/MediaProjection', 'SCREEN_CAPTURE'], ['Landroid/telecom/TelecomManager;', 'TELECOM'],
    ['Landroid/service/notification/NotificationListenerService;', 'NOTIFICATION_READ'], ['Ljavax/crypto/Cipher;', 'CRYPTO'], ['Landroid/util/Base64;', 'BASE64'],
    ['Ljava/net/HttpURLConnection;', 'NETWORK_HTTP'], ['Lokhttp3/', 'NETWORK_HTTP'], ['Ljava/net/Socket;', 'NETWORK_SOCKET'], ['Landroid/hardware/camera2/', 'CAMERA_API'],
    ['Landroid/media/AudioRecord;', 'AUDIO_RECORD'], ['Landroid/location/LocationManager;', 'LOCATION_API'], ['getDeviceId', 'DEVICE_ID'], ['getSubscriberId', 'DEVICE_ID']];
  var URL_IN_DEX = /(?:https?|wss?):\/\/[A-Za-z0-9.\-]{3,253}(?::[0-9]{1,5})?(?:\/[^\s"'<>]{0,120})?/g;
  var IPV4_IN_DEX = /(?<![0-9.])(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}(?![0-9.])/g;
  var RISK_COMBOS = [[['SMS'], ['ACCESSIBILITY'], 'SMS_PLUS_ACCESSIBILITY'], [['SMS'], ['OVERLAY'], 'SMS_PLUS_OVERLAY'],
    [['CALL_LOG', 'PHONE'], ['ACCESSIBILITY'], 'CALL_CONTROL_PLUS_ACCESSIBILITY'], [[], ['ACCESSIBILITY', 'OVERLAY'], 'ACCESSIBILITY_PLUS_OVERLAY'],
    [[], ['DEVICE_ADMIN', 'INSTALL_PACKAGES'], 'DEVICE_ADMIN_PLUS_INSTALLER']];
  function E(code) { var e = new Error(code); e.name = 'ApkError'; e.code = code; return e; }
  var dec8 = new TextDecoder('utf-8'), dec16 = new TextDecoder('utf-16le');
  function u16(b, p) { if (p + 2 > b.length) throw E('TRUNC'); return b[p] | (b[p + 1] << 8); }
  function u32(b, p) { if (p + 4 > b.length) throw E('TRUNC'); return (b[p] | (b[p + 1] << 8) | (b[p + 2] << 16)) + b[p + 3] * 16777216; }
  function i32(b, p) { var v = u32(b, p); return v >= 2147483648 ? v - 4294967296 : v; }
  function u64(b, p) { return u32(b, p) + u32(b, p + 4) * 4294967296; }
  function hex(buf) { return Array.from(new Uint8Array(buf)).map(function (x) { return (x < 16 ? '0' : '') + x.toString(16); }).join(''); }
  async function sha256(b) { return hex(await (globalThis.crypto || require('crypto').webcrypto).subtle.digest('SHA-256', b)); }
  var CRC = (function () { var t = new Uint32Array(256); for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { var c = 0xFFFFFFFF; for (var i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function bytesEq(b, p, s) { for (var i = 0; i < s.length; i++) if (b[p + i] !== s.charCodeAt(i)) return false; return true; }
  function rfind(b, sig, from) { for (var i = b.length - sig.length; i >= from; i--) if (bytesEq(b, i, sig)) return i; return -1; }
  function uniqSort(a) { return Array.from(new Set(a)).sort(); }

  function zipEntries(b) {
    var problems = [], eocd = rfind(b, 'PK\x05\x06', Math.max(0, b.length - 65557));
    if (eocd < 0) throw E('NO_ZIP_EOCD');
    if (eocd + 22 > b.length) throw E('TRUNC');
    var disk = u16(b, eocd + 4), cdDisk = u16(b, eocd + 6), nDisk = u16(b, eocd + 8), nTotal = u16(b, eocd + 10), cdSize = u32(b, eocd + 12), cdOff = u32(b, eocd + 16);
    if (disk || cdDisk || nDisk !== nTotal) problems.push('MULTI_DISK');
    if (nTotal === 0xFFFF || cdOff === 0xFFFFFFFF) problems.push('ZIP64_UNSUPPORTED');
    if (nTotal > MAX_ENTRIES) throw E('TOO_MANY_ENTRIES');
    if (cdOff + cdSize > eocd) throw E('BAD_CENTRAL_DIRECTORY');
    var out = [], p = cdOff, seen = new Set();
    for (var k = 0; k < nTotal; k++) {
      if (!bytesEq(b, p, 'PK\x01\x02')) throw E('BAD_CENTRAL_DIRECTORY');
      var flags = u16(b, p + 8), method = u16(b, p + 10), crc = u32(b, p + 16), csize = u32(b, p + 20), usize = u32(b, p + 24),
        nlen = u16(b, p + 28), xlen = u16(b, p + 30), cmlen = u16(b, p + 32), lho = u32(b, p + 42);
      var name = dec8.decode(b.subarray(p + 46, p + 46 + nlen));
      p += 46 + nlen + xlen + cmlen;
      if (seen.has(name)) problems.push('DUPLICATE_ENTRY');
      seen.add(name);
      if (name[0] === '/' || name[0] === '\\' || name.split(/[\\/]/).indexOf('..') >= 0 || /^[A-Za-z]:/.test(name)) problems.push('PATH_TRAVERSAL');
      if (flags & 1) problems.push('ENCRYPTED_ENTRY_FLAG');
      if (method !== 0 && method !== 8) problems.push('UNSUPPORTED_COMPRESSION');
      if (usize > MAX_ENTRY_UNCOMPRESSED) problems.push('ENTRY_TOO_LARGE');
      if (csize && usize / Math.max(csize, 1) > MAX_RATIO && usize > 10 * 1024 * 1024) problems.push('HIGH_COMPRESSION_RATIO');
      out.push({ name: name, method: method, crc: crc, csize: csize, usize: usize, flags: flags, lho: lho });
    }
    var tot = 0; out.forEach(function (e) { tot += e.usize; }); if (tot > MAX_TOTAL_UNCOMPRESSED) problems.push('TOTAL_UNCOMPRESSED_TOO_LARGE');
    return { entries: out, cdOff: cdOff, eocd: eocd, problems: uniqSort(problems) };
  }
  async function inflateRaw(data, limit) {
    if (typeof DecompressionStream === 'undefined') throw E('DECOMPRESSOR_UNAVAILABLE');
    var ds = new DecompressionStream('deflate-raw'), w = ds.writable.getWriter(), r = ds.readable.getReader(), chunks = [], n = 0;
    w.write(data).catch(function () {}); w.close().catch(function () {});
    try {
      for (;;) { var x = await r.read(); if (x.done) break; chunks.push(x.value); n += x.value.length; if (n > limit) { r.cancel().catch(function () {}); throw E('ENTRY_TOO_LARGE'); } }
    } catch (e) { if (e.code) throw e; throw E('INFLATE_FAILED'); }
    var o = new Uint8Array(n), q = 0; chunks.forEach(function (c) { o.set(c, q); q += c.length; }); return o;
  }
  async function zipRead(b, e, limit) {
    limit = limit === undefined ? MAX_ENTRY_UNCOMPRESSED : limit;
    var p = e.lho;
    if (!bytesEq(b, p, 'PK\x03\x04')) throw E('BAD_LOCAL_HEADER');
    var start = p + 30 + u16(b, p + 26) + u16(b, p + 28), data = b.subarray(start, start + e.csize);
    if (e.usize > limit) throw E('ENTRY_TOO_LARGE');
    var raw;
    if (e.method === 0) raw = data; else if (e.method === 8) raw = await inflateRaw(data, limit); else throw E('UNSUPPORTED_COMPRESSION');
    if (raw.length !== e.usize || crc32(raw) !== e.crc) throw E('CRC_MISMATCH');
    return raw;
  }
  function spStrings(b, off) {
    var hsz = u16(b, off + 2), size = u32(b, off + 4), count = u32(b, off + 8), flags = u32(b, off + 16), sstart = u32(b, off + 20), utf8 = !!(flags & 0x100), res = [];
    var base = off + sstart;
    for (var i = 0; i < count; i++) {
      var q = base + u32(b, off + hsz + 4 * i), n;
      if (utf8) {
        n = b[q]; q += (n & 0x80) ? 2 : 1;
        n = b[q]; var m = n;
        if (n & 0x80) { m = ((n & 0x7F) << 8) | b[q + 1]; q += 2; } else q += 1;
        res.push(dec8.decode(b.subarray(q, q + m)));
      } else {
        n = u16(b, q); q += 2;
        if (n & 0x8000) { n = ((n & 0x7FFF) * 65536) + u16(b, q); q += 2; }
        res.push(dec16.decode(b.subarray(q, q + 2 * n)));
      }
    }
    return res;
  }
  function parseAxml(b) {
    if (b.length < 8 || u16(b, 0) !== 0x0003) throw E('MANIFEST_NOT_BINARY_XML');
    var strings = [], resIds = [], out = [], depth = 0, p = u16(b, 2), end = Math.min(b.length, u32(b, 4));
    while (p + 8 <= end) {
      var typ = u16(b, p), hsz = u16(b, p + 2), size = u32(b, p + 4);
      if (size < 8 || p + size > end) throw E('MANIFEST_CORRUPT');
      if (typ === 0x0001) strings = spStrings(b, p);
      else if (typ === 0x0180) { resIds = []; for (var j = 0; j < Math.floor((size - hsz) / 4); j++) resIds.push(u32(b, p + hsz + 4 * j)); }
      else if (typ === 0x0102) {
        var nameI = i32(b, p + 20), aStart = u16(b, p + 24), aSize = u16(b, p + 26), aCount = u16(b, p + 28);
        var tag = (nameI >= 0 && nameI < strings.length) ? strings[nameI] : '?', attrs = {}, q = p + 16 + aStart;
        for (var i = 0; i < aCount; i++) {
          var o = q + i * aSize, aname = i32(b, o + 4), araw = i32(b, o + 8), vtype = b[o + 15], vdata = u32(b, o + 16);
          if (o + 20 > b.length) throw E('TRUNC');
          var key = (aname >= 0 && aname < strings.length) ? strings[aname] : '';
          if (aname >= 0 && aname < resIds.length && ATTR_IDS[resIds[aname]]) key = ATTR_IDS[resIds[aname]];
          var val;
          if (vtype === 0x03 && vdata < strings.length) val = strings[vdata];
          else if (araw >= 0 && araw < strings.length) val = strings[araw];
          else if (vtype === 0x12) val = vdata !== 0;
          else if (vtype === 0x10 || vtype === 0x11) val = vdata < 2147483648 ? vdata : vdata - 4294967296;
          else if (vtype === 0x01) val = '@0x' + ('0000000' + vdata.toString(16)).slice(-8);
          else val = vdata;
          attrs[key] = val;
        }
        out.push([depth, tag, attrs]); depth++;
      } else if (typ === 0x0103) depth--;
      p += size;
    }
    return out;
  }
  function manifestSummary(nodes) {
    var m = { package: null, version_code: null, version_name: null, min_sdk: null, target_sdk: null, permissions: [], declared_permissions: [], components: [],
      debuggable: false, allow_backup: null, cleartext: null }, stack = [];
    var g = function (a, k) { return a[k] === undefined ? null : a[k]; };
    nodes.forEach(function (nd) {
      var depth = nd[0], tag = nd[1], a = nd[2];
      stack = stack.slice(0, depth).concat([[tag, a]]);
      if (tag === 'manifest') { m.package = g(a, 'package'); m.version_code = g(a, 'versionCode'); m.version_name = g(a, 'versionName'); }
      else if (tag === 'uses-sdk') { m.min_sdk = g(a, 'minSdkVersion'); m.target_sdk = g(a, 'targetSdkVersion'); }
      else if ((tag === 'uses-permission' || tag === 'uses-permission-sdk-23') && a.name) m.permissions.push(a.name);
      else if (tag === 'permission' && a.name) m.declared_permissions.push(a.name);
      else if (tag === 'application') { m.debuggable = a.debuggable === true; m.allow_backup = g(a, 'allowBackup'); m.cleartext = g(a, 'usesCleartextTraffic'); }
      else if (['activity', 'activity-alias', 'service', 'receiver', 'provider'].indexOf(tag) >= 0)
        m.components.push({ type: tag, name: g(a, 'name'), exported: g(a, 'exported'), permission: g(a, 'permission'), actions: [] });
      else if (tag === 'action' && stack.length >= 3 && stack[stack.length - 2][0] === 'intent-filter' && m.components.length) m.components[m.components.length - 1].actions.push(g(a, 'name'));
    });
    m.components.forEach(function (c) {
      var hasFilter = c.actions.length > 0;
      c.exported_effective = c.exported === null ? (c.type !== 'provider' ? hasFilter : false) : !!c.exported;
      c.binds = c.permission;
    });
    m.permissions = uniqSort(m.permissions);
    return m;
  }
  function uleb(b, p) { var r = 0, s = 0, x; do { x = b[p++]; r += (x & 0x7F) * Math.pow(2, s); s += 7; } while (x & 0x80); return [r, p]; }
  function dexStrings(b) {
    if (b.length < 0x70 || !bytesEq(b, 0, 'dex\n')) throw E('NOT_DEX');
    var version = String.fromCharCode(b[4], b[5], b[6]), n = u32(b, 0x38), off = u32(b, 0x3C), tn = u32(b, 0x40), toff = u32(b, 0x44);
    if (off + 4 * n > b.length) throw E('DEX_CORRUPT');
    var out = [];
    for (var i = 0; i < n; i++) {
      var so = u32(b, off + 4 * i); if (so >= b.length) throw E('DEX_CORRUPT');
      var q = uleb(b, so)[1], e = b.indexOf(0, q); if (e < 0) e = b.length;
      out.push(dec8.decode(b.subarray(q, e)));
    }
    var types = [];
    for (var j = 0; j < Math.min(tn, 200000); j++) { var idx = u32(b, toff + 4 * j); if (idx < out.length) types.push(out[idx]); }
    return [version, out, types];
  }
  function obfuscationScore(types) {
    var pre = ['Landroid/', 'Ljava/', 'Ljavax/', 'Lkotlin/', 'Landroidx/', 'Ldalvik/', 'Lorg/'];
    var app = types.filter(function (t) { return t[0] === 'L' && t[t.length - 1] === ';' && !pre.some(function (x) { return t.indexOf(x) === 0; }); });
    if (!app.length) return [0, 0];
    var short = app.filter(function (t) { var s = t.slice(1, -1).split('/').pop(); return /^[a-z]{1,2}(?:\$[A-Za-z0-9]+)?$/.test(s); }).length;
    return [Math.round(short / app.length * 10000) / 10000, app.length];
  }
  function derLen(b, p) { var l = b[p]; p++; if (l < 0x80) return [l, p]; var n = l & 0x7F, v = 0; for (var i = 0; i < n; i++) v = v * 256 + b[p + i]; return [v, p + n]; }
  function x509Fields(cert) {
    var res = {};
    try {
      var tlv = function (p) { if (p >= cert.length) throw E('IDX'); var t = cert[p], d = derLen(cert, p + 1); return [t, d[1], d[1] + d[0]]; };
      var a = tlv(0)[1], tb = tlv(a), p = tb[1];
      if (cert[p] === 0xA0) p = tlv(p)[2];
      p = tlv(p)[2]; p = tlv(p)[2];
      ['issuer', 'validity', 'subject'].forEach(function (key) {
        var t = tlv(p), s = t[1], e = t[2];
        if (key === 'validity') {
          var v1 = tlv(s), v2 = tlv(v1[2]);
          res.not_before = String.fromCharCode.apply(null, cert.subarray(v1[1], v1[2])); res.not_after = String.fromCharCode.apply(null, cert.subarray(v2[1], v2[2]));
        } else {
          var blob = cert.subarray(s, e), cn = -1;
          for (var i = 0; i + 5 <= blob.length; i++) if (blob[i] === 6 && blob[i + 1] === 3 && blob[i + 2] === 0x55 && blob[i + 3] === 4 && blob[i + 4] === 3) { cn = i; break; }
          if (cn >= 0) { var q = cn + 5, d = derLen(blob, q + 1); res[key + '_cn'] = dec8.decode(blob.subarray(d[1], d[1] + d[0])); }
        }
        p = e;
      });
    } catch (e) { res.parse = 'PARTIAL'; }
    return res;
  }
  async function signingBlock(b, cdOff) {
    if (cdOff < 32 || !bytesEq(b, cdOff - 16, 'APK Sig Block 42')) return [];
    var size = u64(b, cdOff - 24), start = cdOff - size - 8;
    if (start < 0 || u64(b, start) !== size) return [];
    var p = start + 8, end = cdOff - 24, out = [], ids = { 0x7109871a: 'v2', 0xf05368c0: 'v3', 0x1b93ad61: 'v3.1' };
    while (p + 12 <= end) {
      var ln = u64(b, p), bid = u32(b, p + 8), val = b.subarray(p + 12, p + 8 + ln), scheme = ids[bid];
      if (scheme) {
        try {
          var q = 4, sl = u32(val, q); q += 4;
          var signer = val.subarray(q, q + sl), sdl = u32(signer, 0), sd = signer.subarray(4, 4 + sdl), dl = u32(sd, 0), cl = u32(sd, 4 + dl),
            certs = sd.subarray(8 + dl, 8 + dl + cl), c1 = u32(certs, 0), cert = certs.subarray(4, 4 + c1);
          out.push(Object.assign({ scheme: scheme, cert_sha256: await sha256(cert) }, x509Fields(cert)));
        } catch (e) { out.push({ scheme: scheme, cert_sha256: null, parse: 'FAILED' }); }
      }
      p += 8 + ln;
    }
    return out;
  }
  function sniff(b, filename) {
    var kinds = [];
    if (bytesEq(b, 0, 'PK\x03\x04')) kinds.push('ZIP');
    if (bytesEq(b, 0, 'dex\n')) kinds.push('DEX');
    if (bytesEq(b, 0, '\x7fELF')) kinds.push('ELF');
    if (bytesEq(b, 0, '%PDF-')) kinds.push('PDF');
    if (bytesEq(b, 0, 'MZ')) kinds.push('PE');
    var ext = filename.indexOf('.') >= 0 ? filename.toLowerCase().split('.').pop() : '';
    return [kinds.length ? kinds[0] : 'UNKNOWN', ext];
  }
  function finish(rep) {
    var groups = new Set(rep.permission_groups || []), special = new Set(rep.special_access || []), caps = new Set(rep.capabilities || []), combos = [];
    RISK_COMBOS.forEach(function (c) {
      var gOk = !c[0].length || c[0].some(function (x) { return groups.has(x); });
      if (gOk && c[1].every(function (x) { return special.has(x); })) combos.push(c[2]);
    });
    if (caps.has('SMS_RECEIVE_HOOK') && (special.has('ACCESSIBILITY') || special.has('OVERLAY'))) combos.push('SMS_HOOK_PLUS_SCREEN_CONTROL');
    if (caps.has('DYNAMIC_CODE_LOADING') && (groups.has('SMS') || groups.has('CALL_LOG'))) combos.push('DYNAMIC_CODE_PLUS_SENSITIVE_DATA');
    rep.risk_combinations = uniqSort(combos);
    if (rep.obfuscation && rep.obfuscation.likely && rep.findings.indexOf('OBFUSCATION_LIKELY') < 0) rep.findings.push('OBFUSCATION_LIKELY');
    if (rep.state === null) {
      if (rep.risk_combinations.length || rep.findings.indexOf('PATH_TRAVERSAL') >= 0) rep.state = 'SUSPICIOUS';
      else if (rep.findings.indexOf('MANIFEST_PARSE_FAILED') >= 0 || rep.findings.indexOf('DEX_PARSE_FAILED') >= 0) rep.state = 'INCONCLUSIVE';
      else rep.state = 'NO_KNOWN_THREAT_FOUND';
    }
    rep.not_checked = ['DYNAMIC_BEHAVIOR', 'SERVER_SIDE_CODE', 'SIGNATURE_CRYPTO_VALIDITY', 'REPUTATION_OF_HASH_UNLESS_CONSENTED', 'NATIVE_CODE_CONTENTS', 'ENCRYPTED_OR_DOWNLOADED_PAYLOADS'];
    return rep;
  }
  async function inspect(input, filename, opts) {
    filename = filename || 'upload.apk'; opts = opts || {};
    var b = input instanceof Uint8Array ? input : new Uint8Array(input), maxBytes = opts.max_bytes || MAX_APK_BYTES;
    var rep = { filename_ext: null, size: b.length, sha256: null, stages: {}, findings: [], capabilities: [], scope_note: 'STATIC_ONLY_NOT_EXECUTED', verdict_basis: 'NOT_A_MALWARE_VERDICT' }, st = rep.stages;
    if (b.length > maxBytes) { st.size_check = 'FAILED'; rep.findings.push('FILE_TOO_LARGE'); rep.state = 'NOT_SCANNED'; return rep; }
    st.size_check = 'PASS'; rep.sha256 = await sha256(b); st.hash = 'PASS';
    var sn = sniff(b, filename); rep.filename_ext = sn[1]; rep.magic = sn[0];
    if (sn[0] !== 'ZIP') { st.magic = 'FAILED'; rep.findings.push('NOT_AN_APK_CONTAINER' + ((sn[1] === 'apk' || sn[1] === 'xapk') ? '_EXTENSION_MISMATCH' : '')); rep.state = 'SCAN_FAILED'; return rep; }
    if (['apk', 'apks', 'xapk', 'zip', ''].indexOf(sn[1]) < 0) rep.findings.push('EXTENSION_MISMATCH');
    st.magic = 'PASS';
    var z;
    try { z = zipEntries(b); } catch (e) { st.zip = 'FAILED'; rep.findings.push('ZIP_' + (e.name === 'ApkError' && e.code !== 'TRUNC' ? e.code : 'CORRUPT')); rep.state = 'SCAN_FAILED'; return rep; }
    rep.findings = rep.findings.concat(z.problems); st.zip = z.problems.length ? 'WARN' : 'PASS';
    var names = {}; z.entries.forEach(function (e) { names[e.name] = e; }); rep.entry_count = z.entries.length;
    if (z.problems.indexOf('PATH_TRAVERSAL') >= 0 || z.problems.indexOf('ZIP64_UNSUPPORTED') >= 0) { rep.state = z.problems.indexOf('PATH_TRAVERSAL') >= 0 ? 'SUSPICIOUS' : 'SCAN_FAILED'; return finish(rep); }
    if (!names['AndroidManifest.xml']) { st.manifest = 'FAILED'; rep.findings.push('NO_ANDROID_MANIFEST'); rep.state = 'SCAN_FAILED'; return finish(rep); }
    var man;
    try { man = manifestSummary(parseAxml(await zipRead(b, names['AndroidManifest.xml'], 8 * 1024 * 1024))); st.manifest = 'PASS'; }
    catch (e) { st.manifest = 'FAILED'; rep.findings.push('MANIFEST_PARSE_FAILED'); rep.state = 'SCAN_FAILED'; return finish(rep); }
    rep.manifest = man;
    rep.permission_groups = uniqSort(man.permissions.filter(function (p) { return DANGEROUS[p]; }).map(function (p) { return DANGEROUS[p]; }));
    var special = new Set(man.permissions.filter(function (p) { return SPECIAL[p]; }).map(function (p) { return SPECIAL[p]; }));
    man.components.forEach(function (c) {
      if (c.binds === 'android.permission.BIND_ACCESSIBILITY_SERVICE') special.add('ACCESSIBILITY');
      if (c.binds === 'android.permission.BIND_NOTIFICATION_LISTENER_SERVICE') special.add('NOTIFICATION_LISTENER');
      if (c.binds === 'android.permission.BIND_DEVICE_ADMIN') special.add('DEVICE_ADMIN');
    });
    rep.special_access = uniqSort(Array.from(special));
    rep.exported = man.components.filter(function (c) { return c.exported_effective; }).map(function (c) { return { type: c.type, name: c.name, protected_by: c.permission }; });
    if (man.components.some(function (c) { return c.actions.indexOf('android.provider.Telephony.SMS_RECEIVED') >= 0; })) rep.capabilities.push('SMS_RECEIVE_HOOK');
    if (man.debuggable) rep.findings.push('DEBUGGABLE');
    rep.signing = await signingBlock(b, z.cdOff);
    rep.signing_v1_files = Object.keys(names).filter(function (n) { return /^META-INF\/[^/]+\.(?:RSA|DSA|EC)$/.test(n); }).sort();
    st.signature = (rep.signing.length || rep.signing_v1_files.length) ? 'PASS' : 'WARN';
    if (!rep.signing.length && !rep.signing_v1_files.length) rep.findings.push('UNSIGNED');
    rep.signature_note = 'CERTIFICATE_EXTRACTED_SIGNATURE_NOT_VERIFIED';
    var dexNames = Object.keys(names).filter(function (n) { return /^classes[0-9]*\.dex$/.test(n); }).sort();
    rep.dex_files = dexNames;
    var caps = new Set(rep.capabilities), urls = new Set(), ips = new Set(), allTypes = [], versions = new Set(), scanned = 0;
    for (var i = 0; i < dexNames.length; i++) {
      var e = names[dexNames[i]];
      if (scanned + e.usize > MAX_DEX_SCAN) { rep.findings.push('DEX_SCAN_TRUNCATED'); break; }
      var ds;
      try { ds = dexStrings(await zipRead(b, e, MAX_DEX_SCAN)); } catch (err) { rep.findings.push('DEX_PARSE_FAILED'); continue; }
      scanned += e.usize; versions.add(ds[0]); allTypes = allTypes.concat(ds[2]);
      ds[1].forEach(function (s) {
        API_MARKERS.forEach(function (mk) { if (s.indexOf(mk[0]) >= 0) caps.add(mk[1]); });
        if (Array.from(s).length < 400) {
          (s.match(URL_IN_DEX) || []).forEach(function (u) { urls.add(Array.from(u).slice(0, 160).join('')); });
          (s.match(IPV4_IN_DEX) || []).forEach(function (ip) { if (!/^(?:0\.|1\.0\.|2\.)/.test(ip) && ip.split('.').length === 4) ips.add(ip); });
        }
      });
    }
    st.dex = dexNames.length && rep.findings.indexOf('DEX_PARSE_FAILED') < 0 ? 'PASS' : (dexNames.length ? 'FAILED' : 'NO_DEX');
    rep.dex_versions = uniqSort(Array.from(versions));
    rep.capabilities = uniqSort(Array.from(caps));
    var ul = uniqSort(Array.from(urls));
    rep.network_indicators = { urls: ul.slice(0, 50), ipv4: uniqSort(Array.from(ips)).slice(0, 50), url_total: ul.length };
    var ob = obfuscationScore(allTypes);
    rep.obfuscation = { short_name_ratio: ob[0], app_classes: ob[1], likely: ob[0] >= 0.5 && ob[1] >= 20 };
    rep.native_libs = uniqSort(Object.keys(names).filter(function (n) { return n.indexOf('lib/') === 0 && /\.so$/.test(n) && n.split('/').length - 1 >= 2; })
      .map(function (n) { return n.split('/')[1] + ':' + n.split('/').pop(); })).slice(0, 60);
    rep.nested_packages = Object.keys(names).filter(function (n) { return /\.(?:apk|dex|jar)$/.test(n) && !/^classes[0-9]*\.dex$/.test(n); }).sort().slice(0, 30);
    if (rep.nested_packages.length) rep.capabilities = uniqSort(rep.capabilities.concat(['EMBEDDED_PACKAGE']));
    rep.state = null;
    return finish(rep);
  }
  return { version: '4.7', inspect: inspect, MAX_APK_BYTES: MAX_APK_BYTES };
});
