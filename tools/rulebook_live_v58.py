"""Explicit opt-in, synthetic-only local Zoro System One Rulebook CLI.

No user transcript is persisted. No payment, refund, SMS or other business action.
Actual checkpoint/head provenance remains UNVERIFIED even if HTTP succeeds.
"""
import argparse
import json
import os
from pathlib import Path

from rulebook.engine import RulebookError
from rulebook.zoro_bridge import run_rulebook
from tools.rulebook_preview_v58 import ROOT, read_strict_json


def main():
    p = argparse.ArgumentParser(description="Optional live System One typed-decision preview")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--book", choices=("refund_intake", "account_change"))
    group.add_argument("--book-file", help="Local business rulebook JSON")
    p.add_argument("--state-file", required=True, help="Text file containing synthetic scenario only")
    p.add_argument("--synthetic-only", action="store_true")
    p.add_argument("--tenant", default="tenant_demo")
    p.add_argument("--event", default="event_demo")
    a = p.parse_args()
    if os.environ.get("DMSG_V58_RULEBOOK_LIVE_ENABLE") != "1" or not a.synthetic_only:
        p.exit(2, "RULEBOOK_LIVE_EXPLICIT_OPT_IN_REQUIRED\n")
    try:
        source = Path(a.book_file) if a.book_file else ROOT / "rulebook" / "presets" / (a.book + ".json")
        book = read_strict_json(source)
        text_file = Path(a.state_file)
        if not text_file.is_file() or text_file.stat().st_size > 6000:
            raise RulebookError("INVALID_SYNTHETIC_FILE")
        text = text_file.read_text(encoding="utf-8")
        result = run_rulebook(book, text, tenant_id=a.tenant, event_id=a.event, allow_live=True)
    except (RulebookError, OSError, ValueError, UnicodeError) as exc:
        p.exit(2, "RULEBOOK_LIVE_REJECTED: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    print("No business effect executed. Model checkpoint identity not attested.")


if __name__ == "__main__":
    main()
