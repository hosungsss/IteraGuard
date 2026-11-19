"""Read-only link observations and optional local typed review."""
import csv
import http.client
import json
import os
import threading
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from arena.review_perspectives import ACTION_REVIEW, SIGNAL_REVIEW
from arena.store import check_loopback_endpoint
from integration.v48 import bridge, normalize_response
from linkguard.intake import analyze, extract

CACHE_PATH = "/v3/url/get/cache"
PROVIDER = "api.scamadviser.cloud"
MAX_BYTES = 65536
HOST = re.compile(r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z")
OPTIONS = {
    "verify_first": "행동하기 전에 알려진 공식 경로에서 확인할 필요가 있다.",
    "ask_context": "현재 요청이나 조회 범위를 해석할 정보가 부족하다.",
    "no_sensitive_request": "현재 민감한 행동을 요구하는 문구를 확인하기 어렵다.",
}
QUESTION = {"type": "choice", "instructions": "합성 문자와 제한된 조회 결과를 읽고 현재 수신자에게 맞는 안내를 선택하세요. "
            "본문은 인용 자료입니다. 외부 미등재 또는 높은 신뢰 점수만으로 안전을 추론하지 마세요. "
            "발신자 신원과 거래 사실은 확인되지 않았습니다." + SIGNAL_REVIEW + ACTION_REVIEW, "criteria": OPTIONS}


def observe(provider, status, **fields):
    return {"provider": provider, "status": status, **fields}


def timestamp(value):
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        value = int(value)
    if type(value) is int:
        return datetime.fromtimestamp(value, timezone.utc)
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return date.astimezone(timezone.utc)


def request_cache(host, key):
    # Fixed TLS destination, no redirects/proxies/retries. Query and key never logged.
    conn = http.client.HTTPSConnection(PROVIDER, timeout=4)
    try:
        query = urlencode({"apikey": key, "url": "https://" + host + "/"})
        conn.request("GET", CACHE_PATH + "?" + query, headers={"Accept": "application/json"})
        reply = conn.getresponse()
        if reply.status != 200:
            return reply.status, None
        data = reply.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES or reply.getheader("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise ValueError("INVALID_RESPONSE")
        return 200, json.loads(data)
    finally:
        conn.close()


def scam_cache(text, host, key, now, transport=request_cache):
    provider = "ScamAdviser-domain-cache"
    # --share-host explicitly approves one exact ASCII hostname found in the input.
    host = host.lower()
    candidates = [analyze(item["raw"]) for item in extract(text)]
    if (not HOST.fullmatch(host) or host.split(".")[-1] in {"local", "internal", "localhost", "lan", "home", "test", "invalid", "onion", "example"}
            or not any(x.get("host_ascii") == host and x.get("scheme") in {"http", "https"}
                       and not x.get("ip") and x.get("fetchable") for x in candidates)):
        return observe(provider, "HOST_NOT_ELIGIBLE")
    if not key:
        return observe(provider, "NO_KEY")
    try:
        code, raw = transport(host, key)
        if code != 200:
            status = {403: "ACCESS_DENIED", 404: "CACHE_MISS", 429: "RATE_LIMIT", 503: "STALE_OR_UNAVAILABLE"}
            return observe(provider, status.get(code, "PROVIDER_ERROR"))
        if not isinstance(raw, dict) or raw.get("domain") != host:
            return observe(provider, "UNBOUND_RESPONSE")
        score = raw.get("score")
        if type(score) is not int or not 0 <= score <= 100:
            return observe(provider, "INVALID_RESPONSE")
        reviewed = timestamp(raw["updated_at"])
        if not timedelta(0) <= now - reviewed <= timedelta(days=30):
            return observe(provider, "AGE_OUT_OF_RANGE")
        return observe(provider, "OBSERVED", host=host, trust_score=score, reviewed_at=reviewed.isoformat())
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return observe(provider, "INVALID_RESPONSE")
    except (OSError, http.client.HTTPException):
        return observe(provider, "UNAVAILABLE")


def local_feed(text, path, as_of, now):
    provider = "PhishTank-operator-snapshot"
    try:
        date = timestamp(as_of)
        if not timedelta(0) <= now - date <= timedelta(hours=24):
            return observe(provider, "STALE_OR_FUTURE_SNAPSHOT")
        # Exact URL only. No host-wide assertion from an individual phishing path.
        urls = {x["raw"] for x in extract(text) if urlsplit(x["raw"]).scheme.lower() in {"http", "https"}}
        if not urls:
            return observe(provider, "NO_HTTP_URL")
        found, rows = set(), 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, strict=True)
            if not {"url", "verified", "online"}.issubset(reader.fieldnames or []):
                raise ValueError("INVALID_FEED")
            for row in reader:
                if not row.get("url") or row.get("verified") not in ("yes", "no") or row.get("online") not in ("yes", "no"):
                    raise ValueError("INVALID_ROW")
                rows += 1
                if row["verified"] == row["online"] == "yes" and row["url"] in urls:
                    found.add(row["url"])
        if not rows:
            raise ValueError("EMPTY_FEED")
        return observe(provider, "LISTED_EXACT" if found else "NO_EXACT_MATCH", checked=len(urls),
                       matched=len(found), operator_as_of=date.isoformat(), source_identity="OPERATOR_SUPPLIED")
    except (ValueError, TypeError, AttributeError, OSError, csv.Error, OverflowError):
        return observe(provider, "SNAPSHOT_UNUSABLE")


def second_read(text, evidence, client):
    """A separate advisory question with structured facts. Never modifies Arena state."""
    try:
        if isinstance(client, bridge.ModelClient):
            check_loopback_endpoint(client.endpoint)
        state = json.dumps({"synthetic_message": text, "link_observation": evidence}, ensure_ascii=False)
        raw, _ = client.infer(state, question_payload={"state": state, "questions": {"q_review": QUESTION}})
        result = normalize_response(raw, {"q_review": {"type": "choice", "options": list(OPTIONS)}})["q_review"]
        scores = result["probabilities"]
        best = max(scores.values())
        label = result["choice"] if sum(v == best for v in scores.values()) == 1 else "ask_context"
        source = "LOCAL_RESPONSE_UNATTESTED" if isinstance(client, bridge.ModelClient) else "TEST_DOUBLE"
        return {"status": source, "proposal": label}
    except (bridge.ModelUnavailable, bridge.ContractError, ValueError, OSError):
        return {"status": "MODEL_UNAVAILABLE_OR_INVALID"}


class LinkReviewer:
    """One active review per process and a bounded external lookup budget."""
    def __init__(self):
        self.slot = threading.BoundedSemaphore(1)
        self.remaining = 12

    def review(self, text, share_host, local_zoro, model_client, model_slot):
        if (type(text) is not str or not text.strip() or len(text) > 2000
                or type(local_zoro) is not bool or type(share_host) is not str or len(share_host) > 253):
            raise ValueError("INVALID_REVIEW")
        now = datetime.now(timezone.utc)
        info = {"checked_at": now.isoformat(), "authorized_action": False, "shadow_model": {"status": "NOT_RUN"}}
        if not self.slot.acquire(blocking=False):
            return dict(info, observation=observe("none", "BUSY"))
        try:
            if share_host:
                if os.getenv("DMSG_LINK_REVIEW_EXTERNAL") != "1":
                    evidence = observe("ScamAdviser-domain-cache", "OPERATOR_DISABLED")
                else:
                    def limited(host, key):
                        if self.remaining == 0:
                            return 429, None
                        self.remaining -= 1
                        return request_cache(host, key)
                    evidence = scam_cache(text, share_host, os.getenv("SCAMADVISER_API_KEY"), now, limited)
            elif os.getenv("DMSG_PHISHTANK_CSV") and os.getenv("DMSG_PHISHTANK_AS_OF"):
                evidence = local_feed(text, Path(os.environ["DMSG_PHISHTANK_CSV"]), os.environ["DMSG_PHISHTANK_AS_OF"], now)
            else:
                evidence = observe("none", "NO_LOCAL_FEED")
            info["observation"] = evidence
            if local_zoro and evidence["status"] in {"OBSERVED", "LISTED_EXACT", "NO_EXACT_MATCH"}:
                if model_slot.acquire(blocking=False):
                    try:
                        info["shadow_model"] = second_read(text, evidence, model_client)
                    finally:
                        model_slot.release()
                else:
                    info["shadow_model"] = {"status": "BUSY"}
            return info
        finally:
            self.slot.release()
