#!/usr/bin/env python3
"""Independent, bounded final candidate verification. Run only after archive freeze.
No rebuild, network, model inference, source edit, or device execution is performed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import zipfile

BASE = Path("/home/ljmpc12/Documents/hackton/20261028수_해커톤 준비_IteraGuard-20261104T055702Z-1-002/20261028수_해커톤 준비_IteraGuard")
OUT = Path("/home/ljmpc12/Documents/hackton/deliverables/v51_implementation_20261104/final_verification")
MAX_ENTRIES = 1000
MAX_MEMBER = 80_000_000
MAX_TOTAL = 800_000_000
MAX_NESTED_TOTAL = 800_000_000
COUNTS = {"requirements": 33, "conflicts": 12, "pending_decisions": 8, "promotion_checklist": 13}
NEGATIVE_FIXTURE = "tests_data/apk_corpus/zipslip.apk"
NEGATIVE_FIXTURE_SHA = "b777536d2a29c641e417330536ef225f9db7e979c77f386ed747d7cb05e7305f"
NEGATIVE_FIXTURE_MEMBERS = {
    "AndroidManifest.xml": {"bytes": 660, "sha256": "0dbe7aac5683ba53309299340d2fb9afef090dbae01b98b96191a2ddfb9048f2"},
    "../../data/evil.so": {"bytes": 1, "sha256": "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"},
}
HF = re.compile(rb"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{20,}(?![A-Za-z0-9_])")
PRIVATE = re.compile(
    rb"-----BEGIN ((?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY)-----\r?\n"
    rb"(?:[A-Za-z0-9+/=]{16,}\r?\n)+-----END \1-----"
)
DB_NAME = re.compile(r"(?i)(?:\.(?:db|sqlite|sqlite3)(?:-(?:wal|shm|journal))?|(?:-journal))$")
PRIVATE_NAME = re.compile(r"(?i)(?:^|/)(?:id_rsa|id_dsa|id_ecdsa|id_ed25519|.*(?:private|debug).*\.(?:pem|key))$")

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def safe_name(name, directory=False):
    value = name[:-1] if directory and name.endswith("/") else name
    if (not value or "\x00" in value or "\\" in value or ":" in value
            or value.startswith("/") or any(p in ("", ".", "..") for p in value.split("/"))):
        raise ValueError("UNSAFE_PATH")
    return value

def archive_metadata(z, require_root=False):
    infos = z.infolist()
    if not infos or len(infos) > MAX_ENTRIES:
        raise ValueError("ARCHIVE_ENTRY_BOUND")
    if sum(i.file_size for i in infos) > MAX_TOTAL:
        raise ValueError("ARCHIVE_TOTAL_BOUND")
    seen, files, directories = set(), set(), set()
    for item in infos:
        name = safe_name(item.filename, item.is_dir())
        if name in seen:
            raise ValueError("ARCHIVE_DUPLICATE_OR_TYPE_COLLISION")
        seen.add(name)
        if item.file_size < 0 or item.file_size > MAX_MEMBER:
            raise ValueError("ARCHIVE_MEMBER_BOUND")
        kind = stat.S_IFMT(item.external_attr >> 16)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError("ARCHIVE_LINK_OR_SPECIAL_FILE")
        if kind == stat.S_IFDIR and not item.is_dir():
            raise ValueError("ARCHIVE_DIRECTORY_TYPE_MISMATCH")
        if item.flag_bits & 1:
            raise ValueError("ARCHIVE_ENCRYPTED_MEMBER")
        if item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ValueError("ARCHIVE_UNSUPPORTED_COMPRESSION")
        (directories if item.is_dir() else files).add(name)
    for name in seen:
        parts = name.split("/")
        if any("/".join(parts[:i]) in files for i in range(1, len(parts))):
            raise ValueError("ARCHIVE_FILE_PARENT_COLLISION")
    roots = {name.split("/")[0] for name in files}
    if require_root and (len(roots) != 1 or any("/" not in name for name in files)):
        raise ValueError("ARCHIVE_NOT_SINGLE_ROOT")
    return infos, {
        "entries": len(infos), "files": len(files), "directories": len(directories),
        "uncompressed_bytes": sum(i.file_size for i in infos),
        "root": next(iter(roots)) if len(roots) == 1 else None,
        "bounds_checked_before_decompression": True,
    }

def content_files(root):
    # Independent transcription of the release file boundary; no imports from source.
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if (p.is_file() and not set(rel.parts) & {"__pycache__", "node_modules", ".git", "runs"}
                and p.name not in {".env", "desktop.ini"} and p.suffix not in {".pyc", ".db", ".sqlite3"}
                and ".sqlite3" not in p.name and not p.name.endswith(".partial")
                and not rel.as_posix().startswith(("apps/dist/web/", "apps/dist/desktop/"))):
            if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
                raise ValueError("SOURCE_LINK_OR_ESCAPE")
            yield p

def inventory(root, release_boundary=True):
    paths = content_files(root) if release_boundary else (p for p in sorted(root.rglob("*")) if p.is_file())
    rows = {}
    for p in paths:
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError("TREE_LINK_OR_ESCAPE")
        rows[p.relative_to(root).as_posix()] = {"bytes": p.stat().st_size, "sha256": sha_file(p)}
    return rows

def inventory_digest(rows):
    return sha_bytes(json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())

def compare_inventory(left, right):
    return {
        "same": left == right,
        "missing": sorted(set(left) - set(right)),
        "unexpected": sorted(set(right) - set(left)),
        "mismatched": sorted(k for k in left.keys() & right.keys() if left[k] != right[k]),
    }

def extract(z, infos, destination):
    if destination.exists():
        raise ValueError("EXTRACTION_DESTINATION_ALREADY_EXISTS_REFUSE_OVERWRITE")
    destination.mkdir(parents=True)
    for info in infos:
        target = destination / safe_name(info.filename, info.is_dir())
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError("EXTRACTION_ESCAPE")
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        copied = 0
        with z.open(info) as src, target.open("xb") as dst:
            while True:
                chunk = src.read(min(1024 * 1024, info.file_size - copied + 1))
                if not chunk:
                    break
                copied += len(chunk)
                if copied > info.file_size or copied > MAX_MEMBER:
                    raise ValueError("DECOMPRESSED_MEMBER_BOUND")
                dst.write(chunk)
        if copied != info.file_size:
            raise ValueError("DECOMPRESSED_SIZE_MISMATCH")

def scan_sensitive(root):
    findings, archives, seen = [], [], set()
    state = {"unique_bytes_scanned": 0, "nested_bytes_expanded": 0, "files_scanned": 0,
             "duplicate_payloads_skipped": 0}
    def scan(name, data, depth):
        # Inspect names even when identical bytes were already inspected.
        if DB_NAME.search(name) or data.startswith(b"SQLite format 3\x00"):
            findings.append({"path": name, "type": "RAW_DATABASE"})
        if PRIVATE_NAME.search(name) and b"PRIVATE KEY-----" in data:
            findings.append({"path": name, "type": "PRIVATE_KEY_FILE"})
        digest = sha_bytes(data)
        if digest in seen:
            state["duplicate_payloads_skipped"] += 1
            return
        seen.add(digest)
        state["unique_bytes_scanned"] += len(data)
        state["files_scanned"] += 1
        if HF.search(data):
            findings.append({"path": name, "type": "HF_TOKEN_FORMAT"})
        if PRIVATE.search(data):
            findings.append({"path": name, "type": "PRIVATE_PEM_MATERIAL"})
        if not data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            return
        if depth >= 4:
            raise ValueError("NESTED_ARCHIVE_DEPTH_BOUND")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if name == NEGATIVE_FIXTURE:
                # Exact known attack fixture: never extracted or executed. This
                # branch does not relax safe_name or normal ZIP safety rules.
                preserved = BASE / "[v5.0] IteraGuard_DoubtMeter" / NEGATIVE_FIXTURE
                corpus = json.loads((root / "tests_data/apk_corpus/CORPUS.json").read_text(encoding="utf-8"))
                declaration = "scen('A06', 'zip-slip 경로', 'SUSPICIOUS + PATH_TRAVERSAL, 추출 없음', '경로 탈출 허용', apk_case('zipslip.apk', 'SUSPICIOUS', 'PATH_TRAVERSAL'))"
                validation_source = (root / "tools/run_v47_validation.py").read_text(encoding="utf-8")
                expected_corpus = {"sha256": NEGATIVE_FIXTURE_SHA, "bytes": 574,
                                   "expect": {"state": "SUSPICIOUS", "finding": "PATH_TRAVERSAL"}}
                if (depth != 0 or digest != NEGATIVE_FIXTURE_SHA or len(data) != 574
                        or sha_file(preserved) != NEGATIVE_FIXTURE_SHA
                        or corpus.get("zipslip.apk") != expected_corpus
                        or declaration not in validation_source):
                    raise ValueError("NEGATIVE_FIXTURE_PROVENANCE_MISMATCH")
                infos = z.infolist()
                if (len(infos) != 2 or {i.filename for i in infos} != set(NEGATIVE_FIXTURE_MEMBERS)
                        or any(i.is_dir() or i.flag_bits & 1
                               or stat.S_IFMT(i.external_attr >> 16) not in (0, stat.S_IFREG)
                               or i.file_size != NEGATIVE_FIXTURE_MEMBERS[i.filename]["bytes"]
                               or i.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                               for i in infos)):
                    raise ValueError("NEGATIVE_FIXTURE_METADATA_MISMATCH")
                if z.testzip() is not None:
                    raise ValueError("NEGATIVE_FIXTURE_CRC")
                actual_members = {i.filename: {"bytes": i.file_size, "sha256": sha_bytes(z.read(i))} for i in infos}
                if actual_members != NEGATIVE_FIXTURE_MEMBERS:
                    raise ValueError("NEGATIVE_FIXTURE_CONTENT_MISMATCH")
                metadata = {"entries": 2, "files": 2, "directories": 0, "uncompressed_bytes": 661,
                            "bounds_checked_before_decompression": True,
                            "status": "EXPECTED_UNSAFE_TEST_FIXTURE", "inner_members_extracted_or_executed": False,
                            "preserved_v50_sha256": NEGATIVE_FIXTURE_SHA,
                            "corpus_and_A06_declaration": "MATCH", "member_digests": actual_members}
            else:
                infos, metadata = archive_metadata(z)
            state["nested_bytes_expanded"] += metadata["uncompressed_bytes"]
            if state["nested_bytes_expanded"] > MAX_NESTED_TOTAL:
                raise ValueError("NESTED_AGGREGATE_BOUND")
            # Metadata gates above precede CRC or any member read.
            if z.testzip() is not None:
                raise ValueError("NESTED_ARCHIVE_CRC")
            archives.append({"path": name, **metadata, "crc": "PASS"})
            for item in infos:
                if not item.is_dir():
                    scan(name + "!/" + item.filename, z.read(item), depth + 1)
    for path in sorted(root.rglob("*")):
        if path.is_file():
            if path.stat().st_size > MAX_MEMBER:
                raise ValueError("EXTRACTED_MEMBER_BOUND")
            scan(path.relative_to(root).as_posix(), path.read_bytes(), 0)
    return {"status": "PASS" if not findings else "FAIL", "findings": findings,
            "scope": "Every extracted payload; bounded recursive ZIP/APK/skill payloads; hash-deduplicated. No matched secret values are logged.",
            "private_key_detection": "Actual multiline encoded private PEM block or private-key filename with PRIVATE KEY header. Test source literals alone are not key material.",
            "hf_detection": "Standalone hf_ plus at least 20 alphanumeric characters.",
            "archives": archives, **state}

def traceability(root):
    old = json.loads((root / "docs/V50_TRACEABILITY.json").read_text(encoding="utf-8"))
    new = json.loads((root / "docs/V51_TRACEABILITY.json").read_text(encoding="utf-8"))
    issues, ids, counts = [], [], {}
    for section, expected in COUNTS.items():
        a, b = old.get(section, []), new.get(section, [])
        counts[section] = len(b)
        if len(a) != expected or len(b) != expected:
            issues.append(section + ":COUNT")
        if [x.get("id") for x in a] != [x.get("id") for x in b]:
            issues.append(section + ":IDS_OR_ORDER")
        for original, current in zip(a, b):
            ids.append(current.get("id"))
            if any(current.get(k) != v for k, v in original.items()):
                issues.append(str(original.get("id")) + ":ORIGINAL_FIELDS_CHANGED")
            if any(k not in current for k in ("v51_status", "v51_resolution", "v51_evidence")):
                issues.append(str(original.get("id")) + ":MISSING_CURRENT_FIELDS")
    if len(ids) != 66 or len(set(ids)) != 66 or None in ids:
        issues.append("LEGACY_66_NOT_UNIQUE")
    stable = [x.get("stable_release_gate_id") for x in new.get("promotion_checklist", [])]
    if len(stable) != 13 or len(set(stable)) != 13 or None in stable:
        issues.append("STABLE_GATE_IDS")
    additions = [x.get("id") for x in new.get("new_v51_gates", [])]
    if len(additions) != len(set(additions)) or set(additions) & set(ids):
        issues.append("NEW_GATE_IDS")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues, "counts": counts,
            "legacy_ids": ids, "stable_gate_ids": stable, "new_gate_ids": additions,
            "original_fields_preserved": not any("ORIGINAL_FIELDS" in s for s in issues),
            "delivery_claims_source": new.get("delivery_finalization"),
            "independent_human_evaluation": new.get("independent_human_evaluation"),
            "physical_device_validation": new.get("physical_device_validation"),
            "quality_status": new.get("v51_quality_status")}

def check_prd(root, source):
    results = []
    for version in ("v50", "v51"):
        paths = ("docs/PRD_" + version + ".md", "dmsg/references/PRD_" + version + ".md")
        hashes = {name: sha_file(root / name) for name in paths}
        source_hashes = {name: sha_file(source / name) for name in paths}
        results.append({"version": version, "extracted": hashes, "source": source_hashes,
                        "same": len(set(hashes.values())) == 1 and hashes == source_hashes})
    return {"status": "PASS" if all(r["same"] for r in results) else "FAIL", "comparisons": results}

def run_checks(root, archive, out):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("DMSG_", "ZORO_", "HF_", "HUGGING_FACE_", "V50_", "V51_"))}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    definitions = [("verify_release", ["tools/verify_release.py", str(archive), "--root", str(root)])]
    definitions += [(name, ["tools/" + name + ".py", "--check"]) for name in (
        "export_v50_contract", "export_v51_profiles", "export_v51_base_engine",
        "export_v51_semantic", "export_v51_contract")]
    records = []
    # No interpreter imports from W. Each script runs from the extracted candidate.
    for name, args in definitions:
        command = [sys.executable, "-B", *args]
        log = out / (name + ".log")
        started = time.monotonic()
        try:
            with log.open("wb") as handle:
                proc = subprocess.run(command, cwd=root, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                      timeout=180, check=False)
            code, status = proc.returncode, "PASS" if proc.returncode == 0 else "FAIL"
        except subprocess.TimeoutExpired:
            code, status = None, "TIMEOUT"
        records.append({"name": name, "command": command, "cwd": str(root), "exit_code": code,
                        "status": status, "seconds": round(time.monotonic() - started, 3),
                        "log": str(log), "log_sha256": sha_file(log)})
    return records

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=BASE / "IteraGuard_DoubtMeter_v5_1_FULL_CANDIDATE.zip")
    parser.add_argument("--source", type=Path, default=BASE / "[v5.1] IteraGuard_DoubtMeter")
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--execute-after-build", action="store_true",
                        help="Required deliberate trigger after root confirms frozen archive creation.")
    args = parser.parse_args()
    if not args.execute_after_build:
        parser.error("Wait for archive creation/freeze confirmation, then pass --execute-after-build.")
    out, source, archive = args.output.resolve(), args.source.resolve(), args.archive.resolve()
    if out == source or out.is_relative_to(source):
        parser.error("Output must be outside source.")
    out.mkdir(parents=True, exist_ok=True)
    receipt_path = out / "receipt.json"
    if receipt_path.exists() or (out / "extracted").exists():
        parser.error("Fresh output required; existing receipt or extraction will not be overwritten.")
    receipt = {"schema": "v51-independent-extraction/1", "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "status": "RUNNING", "archive": str(archive), "source": str(source),
               "script": str(Path(__file__).resolve()), "script_sha256": sha_file(Path(__file__)),
               "actual_model_calls": 0, "network_requests": 0, "device_execution": "NOT_RUN",
               "claims_scope": "Packaging, byte integrity, generated contract reproducibility, inherited traceability, bounded secret scanning only.",
               "quality_completion": "NOT_CLAIMED", "human_independent_evaluation": "NOT_RUN",
               "verification_script_correction": {
                   "initial_failure_receipt": str(OUT / "attempt1_unsafe_fixture/receipt.json"),
                   "reason": "Generic recursive ZIP scan rejected the intentionally adversarial A06 test fixture. Exact path, unchanged v5.0 digest, CORPUS declaration, A06 expectation, metadata and all inner member digests now identify it as expected unsafe test data; memory-only scan remains bounded. Every other unsafe nested path still fails.",
                   "product_source_or_archive_changed": False,
                   "full_archive_path_rules_relaxed": False,
                   "fixture_inner_members_ever_extracted_or_executed": False,
               },
               "limitations": ["Existing host Python environment, not clean OS/dependency installation.",
                               "No browser interaction, model inference, authenticated checkpoint attestation or physical Android/iOS execution.",
                               "Static secret patterns cannot prove absence of every possible secret representation.",
                               "Candidate metadata and passing checks do not prove semantic quality or independent human evaluation."]}
    failed = False
    before = None
    extracted_root = None
    try:
        receipt["archive_sha256"] = sha_file(archive)
        receipt["archive_bytes"] = archive.stat().st_size
        before = inventory(source)
        write_json(out / "source_inventory_before.json", before)
        receipt["source_inventory_before_sha256"] = inventory_digest(before)
        with zipfile.ZipFile(archive) as z:
            infos, metadata = archive_metadata(z, require_root=True)
            receipt["archive_safety"] = metadata
            if z.testzip() is not None:
                raise ValueError("FULL_CRC_FAILED")
            receipt["archive_safety"]["crc"] = "PASS"
            receipt["archive_safety"]["status"] = "PASS"
            extract(z, infos, out / "extracted")
        extracted_root = out / "extracted" / metadata["root"]
        receipt["extracted_root"] = str(extracted_root)
        extracted = inventory(extracted_root, release_boundary=False)
        write_json(out / "extracted_inventory_before.json", extracted)
        receipt["extracted_inventory_sha256"] = inventory_digest(extracted)
        receipt["source_to_extracted"] = compare_inventory(before, extracted)
        failed |= not receipt["source_to_extracted"]["same"]
        manifest = json.loads((extracted_root / "MANIFEST_SHA256.json").read_text(encoding="utf-8"))
        expected = manifest["files"]
        for name in expected:
            safe_name(name)
        observed = {k: v for k, v in extracted.items() if k != "MANIFEST_SHA256.json"}
        receipt["manifest_member_sha"] = compare_inventory(expected, observed)
        failed |= not receipt["manifest_member_sha"]["same"]
        receipt["file_counts"] = {"manifest_members": len(expected), "source_package_files": len(before),
                                  "extracted_files": len(extracted),
                                  "empty_files": [k for k, v in extracted.items() if v["bytes"] == 0]}
        receipt["file_counts"]["empty_file_count"] = len(receipt["file_counts"]["empty_files"])
        receipt["sensitive_content"] = scan_sensitive(extracted_root)
        failed |= receipt["sensitive_content"]["status"] != "PASS"
        receipt["prd_reference"] = check_prd(extracted_root, source)
        failed |= receipt["prd_reference"]["status"] != "PASS"
        receipt["traceability"] = traceability(extracted_root)
        failed |= receipt["traceability"]["status"] != "PASS"
        # Do not execute candidate scripts unless contents match the approved source and manifest,
        # archive checks passed, and sensitive payloads are absent.
        if failed:
            receipt["commands"] = []
            receipt["execution_skipped"] = "PRE_EXECUTION_INTEGRITY_OR_CONTENT_CHECK_FAILED"
        else:
            receipt["commands"] = run_checks(extracted_root, archive, out)
            failed |= any(item["status"] != "PASS" for item in receipt["commands"])
        after_extract = inventory(extracted_root, release_boundary=False)
        write_json(out / "extracted_inventory_after.json", after_extract)
        receipt["extracted_immutable"] = compare_inventory(extracted, after_extract)
        failed |= not receipt["extracted_immutable"]["same"]
        receipt["archive_sha256_after"] = sha_file(archive)
        receipt["archive_immutable"] = receipt["archive_sha256"] == receipt["archive_sha256_after"]
        failed |= not receipt["archive_immutable"]
    except Exception as exc:
        # Do not log arbitrary exception strings: malformed file content may include a secret.
        receipt["error"] = {"type": type(exc).__name__, "code": str(exc) if
                            isinstance(exc, ValueError) and re.fullmatch(r"[A-Z0-9_]+", str(exc)) else "DETAILS_WITHHELD"}
        failed = True
    finally:
        if before is not None:
            try:
                after = inventory(source)
                write_json(out / "source_inventory_after.json", after)
                receipt["source_inventory_after_sha256"] = inventory_digest(after)
                receipt["source_immutable"] = compare_inventory(before, after)
                failed |= not receipt["source_immutable"]["same"]
            except Exception as exc:
                receipt["source_immutable"] = {"same": False, "error_type": type(exc).__name__}
                failed = True
        receipt["status"] = "FAIL" if failed else "PASS"
        receipt["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        write_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path),
                      "actual_model_calls": 0, "device_execution": "NOT_RUN"}, ensure_ascii=False))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())

