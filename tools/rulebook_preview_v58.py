"""Local, synthetic-only System One decision preview; never calls Zoro or sends data."""
import argparse
import json
from pathlib import Path
from rulebook.engine import decide, validate_book, RulebookError


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--book", choices=("refund_intake", "account_change"), required=True)
    p.add_argument("--answers", required=True, help="Local JSON file containing System One answers")
    p.add_argument("--tenant", default="tenant_demo")
    p.add_argument("--event", default="event_demo")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    book = json.loads((root / "rulebook" / "presets" / (args.book + ".json")).read_text(encoding="utf-8"))
    src = Path(args.answers)
    if src.stat().st_size > 50000:
        raise SystemExit("INVALID_INPUT_SIZE")
    raw = json.loads(src.read_text(encoding="utf-8"),
                     parse_constant=lambda _: (_ for _ in ()).throw(RulebookError("INVALID_NUMBER")))
    validate_book(book)
    result = decide(book, raw, tenant_id=args.tenant, event_id=args.event)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Execution mode: LOCAL_TYPED_FIXTURE; no model invocation or side effects.")


if __name__ == "__main__":
    main()
