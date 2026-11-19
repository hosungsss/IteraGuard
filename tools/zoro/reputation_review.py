"""Read-only synthetic message review. See --help."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from arena.link_review import local_feed, observe, scam_cache, second_read
from integration.v48 import bridge


def main():
    parser = argparse.ArgumentParser(description="합성 문자 한 건을 표준입력으로 받습니다. 기본은 외부 전송 없음.")
    parser.add_argument("--synthetic", action="store_true", required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--share-host", help="이 도메인 한 개만 ScamAdviser 캐시로 보내는 데 동의")
    group.add_argument("--phishtank-csv", type=Path, help="운영자가 확보한 online-valid CSV를 오프라인으로 대조")
    parser.add_argument("--as-of", help="CSV 실제 확보 시각, 시간대 포함 ISO 8601")
    parser.add_argument("--local-zoro", action="store_true", help="선택형 보조 질문을 기존 로컬 모델에 전송")
    args = parser.parse_args()
    if bool(args.phishtank_csv) != bool(args.as_of):
        parser.error("--phishtank-csv and --as-of must be used together")
    text = sys.stdin.read(2002).removesuffix("\n")
    if not text.strip() or len(text) > 2000 or sys.stdin.read(1):
        parser.error("provide one synthetic message of 1–2000 characters")
    now = datetime.now(timezone.utc)
    evidence = observe("none", "NOT_REQUESTED")
    if args.share_host:
        evidence = scam_cache(text, args.share_host, os.environ.get("SCAMADVISER_API_KEY"), now)
    if args.phishtank_csv:
        evidence = local_feed(text, args.phishtank_csv, args.as_of, now)
    result = {"checked_at": now.isoformat(), "observation": evidence, "authorized_action": False,
              "shadow_model": second_read(text, evidence, bridge.ModelClient()) if args.local_zoro and evidence["status"] in {"OBSERVED", "LISTED_EXACT", "NO_EXACT_MATCH"} else {"status": "NOT_RUN"}}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
