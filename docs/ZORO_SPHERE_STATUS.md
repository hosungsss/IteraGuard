# Sphere API connection indicator

The sphere starts at 대기. A new /api/evaluate response with model_status VALID, execution_source LOCAL_HTTP_MODEL_UNATTESTED and a 64-character response SHA256 shows ZORO-1 연결 완료 for 60 seconds. This confirms recent API response evidence, not model checkpoint identity or uninterrupted availability. Configuration alone, cached session reads and controlled fixtures do not set this state. No automatic extra model calls are introduced; a real evaluation must succeed first.

A controlled fixture shows 테스트 응답. Failed or malformed responses clear connected state. Expiry returns to 대기. Connected canvas brightness/glow cycles gently every 3.2 seconds; reduced-motion disables this animation. Decision messages remain in the verdict panel.

Validation: 21 tests_v59 pass. Actual Edge with intercepted synthetic API envelopes passes initial state, fixture rejection, simulated live response, glow style, reduced-motion style, 61-second time advance, and failed response reset, with zero page errors. These tests are not real Zoro inference. Actual Zoro and public deployment remain unverified.
