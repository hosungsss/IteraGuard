# dmsg v5.2 optional decision sandbox reference

Compatibility: `/dmsg` and `name: dmsg` unchanged. Existing v5.1 behaviour is the production **baseline**; v5.2 is only experimental developer guidance.

Never interpret a model's raw noul, choice, or score as proven real-world fraud probability. Model identity attestation and independent target-event calibration are separate controls.

New code: `integration/v52_decision_sandbox.py`, `tools/v52_exploratory_train.py` (outside portable skill). Only a sandbox observation is produced; `action_permission=NONE`, `may_override_v51_policy=false`.

Use five inputs in fixed order: q_scam, q_pressure, q_current_exposure, q_payment_anomaly and q_request_scope.sensitive_request. Reject missing/non-finite/malformed fields. No safe shortcut on mismatches.

Separate reasoning uncertainty threshold 0.7 from the action threshold p*=CFP/(CFP+CFN), which requires independently calibrated P(target event). A reverse odds calculation is not independent evidence. The source PDF `Decision_Agent_v3.1_표지포함.pdf` is **not** included and must never be bundled.

Review gate: train on development only; record label source; group by scenario family; no locked-data fitting. Report paired net-utility, false alarms, misses, abstentions and response latency; keep a NO CHANGE option. Human independent evaluation, real Zoro-1 typed runtime and NPU/device testing remain NOT_RUN in this addition.
