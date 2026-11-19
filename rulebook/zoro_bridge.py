"""Opt-in System One -> strict industry rulebook proposal bridge.

Uses the EXISTING Arena ModelClient transport; does not change Zoro weights,
production v5.1 policy, payment channels, or external business systems.
"""
import math
from arena.store import check_loopback_endpoint
from integration.v48 import bridge
from rulebook.engine import build_questions, decide


def run_rulebook(book, state, *, tenant_id, event_id, allow_live=False, client=None):
    """Call configured System One only under explicit opt-in.

    A test double can be passed via client, but a test double is never a
    VERIFIED_MODEL. Neither real nor fake responses authorize a business action.
    """
    payload = build_questions(book, state)
    if not allow_live:
        result = decide(book, {}, tenant_id=tenant_id, event_id=event_id)
        result.update(source="NOT_RUN", model_request_attempted=False,
                      model_response_received=False, latency_ms=None,
                      reason="LIVE_OPT_IN_REQUIRED")
        return result

    actual = client if client is not None else bridge.ModelClient()
    try:
        if isinstance(actual, bridge.ModelClient):
            check_loopback_endpoint(actual.endpoint)
        raw, elapsed = actual.infer(state, question_payload=payload)
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise bridge.ModelUnavailable("INVALID_MODEL_LATENCY")
    except (bridge.ModelUnavailable, bridge.ContractError, ValueError, TypeError, OSError):
        result = decide(book, {}, tenant_id=tenant_id, event_id=event_id)
        result.update(source="MODEL_UNAVAILABLE", model_request_attempted=True,
                      model_response_received=False, latency_ms=None,
                      reason="MODEL_TRANSPORT_OR_CONTRACT_FAILURE")
        return result

    result = decide(book, raw, tenant_id=tenant_id, event_id=event_id)
    result.update(source=("LOCAL_HTTP_MODEL_UNATTESTED" if isinstance(actual, bridge.ModelClient)
                          else "TEST_DOUBLE_NOT_ZORO"),
                  model_request_attempted=True, model_response_received=True,
                  latency_ms=round(elapsed, 3))
    return result
