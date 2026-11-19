import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit
from arena import link_review as review

NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)
MESSAGE = "합성 https://example.org/a?id=private 확인"
UTC = NOW.isoformat()


class ReputationReviewTests(unittest.TestCase):
    def cache(self, code=200, host="example.org", key="fixture", **fields):
        record = {"domain": "example.org", "updated_at": UTC, "score": 42, **fields}
        transport = Mock(return_value=(code, record))
        return review.scam_cache(MESSAGE, host, key, NOW, transport), transport

    def test_only_selected_host_is_shared(self):
        obs, send = self.cache()
        send.assert_called_once_with("example.org", "fixture")
        self.assertEqual(obs["status"], "OBSERVED")
        self.assertEqual(obs["trust_score"], 42)
        self.assertNotIn("private", str(obs))

    def test_missing_key_and_unrelated_or_private_targets(self):
        for host, key, reason in [("example.org", "", "NO_KEY"), ("other.org", "fixture", "HOST_NOT_ELIGIBLE"),
                                  ("localhost", "fixture", "HOST_NOT_ELIGIBLE"), ("example.org/a", "fixture", "HOST_NOT_ELIGIBLE")]:
            with self.subTest(host=host):
                obs, send = self.cache(host=host, key=key)
                self.assertEqual(obs['status'], reason); send.assert_not_called()

    def test_status_and_schema_failures(self):
        for code, reason in [(403,"ACCESS_DENIED"),(404,"CACHE_MISS"),(429,"RATE_LIMIT"),(503,"STALE_OR_UNAVAILABLE"),(301,"PROVIDER_ERROR")]:
            self.assertEqual(self.cache(code=code)[0]["status"], reason)
        for values, expected in [({"score":True},"INVALID_RESPONSE"),({"score":101},"INVALID_RESPONSE"),
                                 ({"updated_at":"2020-01-01T00:00:00Z"},"AGE_OUT_OF_RANGE"),
                                 ({"domain":"another.org"},"UNBOUND_RESPONSE"),({"updated_at":"bad"},"INVALID_RESPONSE")]:
            self.assertEqual(self.cache(**values)[0]["status"],expected)

    def test_transport_uses_only_official_origin(self):
        with patch.object(review.http.client,"HTTPSConnection") as conn:
            client=conn.return_value
            reply=client.getresponse.return_value
            reply.status=200; reply.getheader.return_value="application/json"; reply.read.return_value=b'{}'
            self.assertEqual(review.request_cache("example.org","fixture"),(200,{}))
            conn.assert_called_once_with("api.scamadviser.cloud",timeout=4)
            method, uri=client.request.call_args.args
            self.assertEqual(method,"GET");self.assertEqual(urlsplit(uri).path,"/v3/url/get/cache")
            self.assertEqual(parse_qs(urlsplit(uri).query),{"url":["https://example.org/"],"apikey":["fixture"]})
            client.close.assert_called_once()

    def test_snapshot_exact_match_miss_stale_and_empty(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"feed.csv"
            header="url,verified,online\n"
            path.write_text(header+"https://example.org/a?id=private,yes,yes\n")
            self.assertEqual(review.local_feed(MESSAGE,path,UTC,NOW)["status"],"LISTED_EXACT")
            self.assertEqual(review.local_feed("https://example.org/b",path,UTC,NOW)["status"],"NO_EXACT_MATCH")
            self.assertEqual(review.local_feed(MESSAGE,path,"2020-11-20T00:00:00Z",NOW)["status"],"STALE_OR_FUTURE_SNAPSHOT")
            path.write_text(header)
            self.assertEqual(review.local_feed(MESSAGE,path,UTC,NOW)["status"],"SNAPSHOT_UNUSABLE")

    def test_structured_evidence_is_delivered_to_shadow_question(self):
        client=Mock()
        probs={k:float(k=="verify_first") for k in review.OPTIONS}
        client.infer.return_value=({"answers":{"q_review":{"type":"choice","probabilities":probs,"choice":"verify_first"}}},0)
        evidence,_=self.cache()
        result=review.second_read(MESSAGE,evidence,client)
        self.assertEqual(result,{"status":"TEST_DOUBLE","proposal":"verify_first"})
        state=client.infer.call_args.args[0]
        self.assertEqual(json.loads(state)["link_observation"],evidence)
        self.assertEqual(client.infer.call_args.kwargs["question_payload"]["state"],state)

    def test_timeout_and_missing_model(self):
        transport=Mock(side_effect=TimeoutError)
        self.assertEqual(review.scam_cache(MESSAGE,"example.org","fixture",NOW,transport)["status"],"UNAVAILABLE")
        client=Mock();client.infer.side_effect=review.bridge.ModelUnavailable("not configured")
        self.assertEqual(review.second_read(MESSAGE,{},client)["status"],"MODEL_UNAVAILABLE_OR_INVALID")
