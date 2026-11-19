"""Local System One typed-decision preview with arbitrary versioned business rulebooks.

No model invocation, network transfer, business side effects, or persistent task writes.
"""
import argparse
import json
from pathlib import Path

from rulebook.engine import decide, validate_book, RulebookError

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 65536


def read_strict_json(path):
    file = Path(path)
    if file.suffix.lower() != ".json" or not file.is_file() or file.stat().st_size > MAX_JSON_BYTES:
        raise RulebookError("INVALID_LOCAL_JSON_FILE")

    def unique(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise RulebookError("DUPLICATE_JSON_KEY")
            output[key] = value
        return output

    def nonfinite(_):
        raise RulebookError("NONFINITE_JSON")

    with file.open("r", encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=unique, parse_constant=nonfinite)


def main():
    parser = argparse.ArgumentParser(description="Strict local typed proposal preview; never a model/live action")
    book_group = parser.add_mutually_exclusive_group(required=True)
    book_group.add_argument("--book", choices=("refund_intake", "account_change"))
    book_group.add_argument("--book-file", help="Local versioned JSON book for a new domain")
    parser.add_argument("--answers", required=True, help="Local synthetic System One answer envelope")
    parser.add_argument("--tenant", default="tenant_demo")
    parser.add_argument("--event", default="event_demo")
    args = parser.parse_args()

    try:
        book_path = Path(args.book_file) if args.book_file else ROOT / "rulebook" / "presets" / (args.book + ".json")
        book = read_strict_json(book_path)
        raw = read_strict_json(args.answers)
        validate_book(book)
        result = decide(book, raw, tenant_id=args.tenant, event_id=args.event)
    except (RulebookError, ValueError, OSError, UnicodeError) as exc:
        # Never echo file contents, secret text or stack traces in a public demo.
        parser.exit(2, "RULEBOOK_INPUT_REJECTED: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    print("Execution mode: LOCAL_TYPED_FIXTURE; no Zoro inference, external actions or persistence.")


if __name__ == "__main__":
    main()
