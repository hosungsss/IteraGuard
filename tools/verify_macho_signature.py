"""Verify that a Mach-O executable's embedded CodeDirectory hashes match its pages.

Apple Silicon refuses to run arm64 code whose signature is missing or whose page hashes do
not match. This recomputes every code-slot hash from the file bytes (no Apple tools needed).
It does NOT check Developer ID trust, notarization or Gatekeeper policy.
Usage: python tools/verify_macho_signature.py <binary> [...]
"""
import hashlib, json, struct, sys

HASHES = {1: hashlib.sha1, 2: hashlib.sha256, 3: lambda b: hashlib.sha256(b), 4: hashlib.sha384}


def check(path):
    d = open(path, 'rb').read()
    magic = struct.unpack('<I', d[:4])[0]
    if magic != 0xfeedfacf:
        return {'file': path, 'status': 'NOT_THIN_MACHO64'}
    ncmds = struct.unpack('<I', d[16:20])[0]
    off = 32
    for _ in range(ncmds):
        cmd, size = struct.unpack('<II', d[off:off + 8])
        if cmd == 0x1d:
            sig_off, sig_size = struct.unpack('<II', d[off + 8:off + 16])
            break
        off += size
    else:
        return {'file': path, 'status': 'UNSIGNED'}
    blob = d[sig_off:sig_off + sig_size]
    smagic, _, count = struct.unpack('>III', blob[:12])
    results = []
    for i in range(count):
        typ, boff = struct.unpack('>II', blob[12 + 8 * i:20 + 8 * i])
        if struct.unpack('>I', blob[boff:boff + 4])[0] != 0xfade0c02:
            continue
        cd = blob[boff:]
        (_, _, version, flags, hash_off, ident_off, n_special, n_code, code_limit, hash_size, hash_type, _plat, page_log2) = struct.unpack('>IIIIIIIIIBBBB', cd[:40])
        page = 1 << page_log2 if page_log2 else code_limit
        fn = HASHES.get(hash_type)
        bad = 0
        for slot in range(n_code):
            start = slot * page
            chunk = d[start:min(start + page, code_limit)]
            want = cd[hash_off + slot * hash_size: hash_off + (slot + 1) * hash_size]
            if fn(chunk).digest()[:hash_size] != want:
                bad += 1
        results.append({'slot_type': typ, 'hash_type': hash_type, 'flags': hex(flags), 'adhoc': bool(flags & 0x2),
                        'code_limit': code_limit, 'file_size': len(d), 'covers_whole_code': code_limit == sig_off,
                        'code_slots': n_code, 'mismatched_slots': bad})
    ok = bool(results) and all(r['mismatched_slots'] == 0 and r['covers_whole_code'] for r in results)
    return {'file': path, 'status': 'PAGE_HASHES_VALID' if ok else 'PAGE_HASHES_INVALID', 'code_directories': results,
            'note': 'Structural check only; Gatekeeper/notarization not evaluated.'}


if __name__ == '__main__':
    out = [check(p) for p in sys.argv[1:]]
    print(json.dumps(out, indent=1))
    sys.exit(0 if all(o['status'] == 'PAGE_HASHES_VALID' for o in out) else 1)
