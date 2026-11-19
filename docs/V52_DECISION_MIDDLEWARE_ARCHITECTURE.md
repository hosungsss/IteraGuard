# IteraGuard v5.2 — Decision Sandbox and Evidence-Gated Middleware

Status: **EXPERIMENTAL_SOURCE_CANDIDATE**, not production or model-authenticated. Baseline: uploaded v5.1 (SHA-256 `b7aa499b2306203710e94bd77a367de922f1ac5e5b44aec112c5d2d39703bbb1`). Developed on 2026-11-10.

## Provenance and non-inclusion

- `Decision_Agent_v3.1_표지포함.pdf` (Handbook, 3rd ed., 2026-11-09) informed *principles only* (chapters 20, 21, 24–27), **NOT COPIED OR BUNDLED** into this project or skill. Do not copy this book's prose, figures, or source into the package.
- `IteraGuard_Upgrade_Prompt.md` requests keeping inference uncertainty threshold 0.7 distinct from the cost-based action threshold p*, and permits NO CHANGE absent independent measured gain.
- The user-provided team discussion proposes **middleware-before/after-Zoro**, atomic factual questions, an empirical five-feature logistic model, odds-ratio backcheck, and a transistor-like intake/controller/output architecture. These are *proposals*, not evidence of effectiveness.
- Google Drive top-level folder `1CosYeNIQUJQLNuOYx5PzjGLsdj0hWfMY` has a v5.1 folder, v5.0 and archived prior folders. Current project source of truth is the **uploaded v5.1 ZIP**, which was locally inspected and hashed. Drive listing is read-only metadata; the complete historical Drive contents were **not all fetched or incorporated**. Do not falsely claim an exhaustive semantic merge. No Drive writes.

## Architecture and trust boundaries

    untrusted message + trusted context
      -> deterministic normalization, source labels, existing v5.1 question profile/binding
      -> [outside this sandbox: existing real/mocked Zoro-1 typed adapter]
      -> strict `noul`/`choice` feature extractor (no model identity attestation)
      -> five-feature exploratory logistic estimate (NOT a confirmed fraud probability)
      -> optional empirical direct-vs-reasoned gain analysis (requires separately calibrated target event probabilities)
      -> authorized *independent* v5.1 policy gate (unchanged)
      -> human verification task / audit

Three architectural functions inspired by a BJT metaphor:

1. `intake`: obtain typed model outputs and provenance, validate five features and refuse malformed/missing questions;
2. `controller`: compare *exploratory* statistical signal with independently checked facts, locked cost policy and model provenance;
3. `emitter`: show recommendation and uncertainty without granting payment, identity, URL navigation, or APK execution authority.

A transistor analogy is an interface-design mnemonic **not a claim of electronic equivalence**. Do not call the logistic score an independent corroborating observation.

### Five features (frozen in order)

`q_scam.yes`, `q_pressure.yes`, `q_current_exposure.yes`, `q_payment_anomaly.yes`, `q_request_scope.sensitive_request`.

`q_scam` is a model's answer to a textual *deceptive-coercion question*, **not** P(real-world fraud). A logistic fit trained against synthetic `pause_required` is **not** a real-world fraud probability. The model is default-disabled.

### Inference threshold versus action threshold

- **Reasoning threshold `tau_reason=0.70`**: top-choice confidence used only to select an additional *checkable* Zoro-1 reasoning experiment when model/reasoning access and a separate calibration are present. Current sandbox does not call it.
- **Decision threshold `p*=C_FP/(C_FP+C_FN)`**: valid only when the cost units are explicit and input is a separately calibrated probability of the exact target event. Never feed `q_scam` or an uncertified exploratory score directly into p* to authorize an action.
- The existing v5.1 semantic threshold `0.70` and any legacy `0.70` are frozen and may not be silently reinterpreted as cost thresholds.

### Inverse odds and independent evidence

`inverse_odds_check` shows algebraic invertibility given known priors and valid posterior probabilities. Reversing a model output cannot independently verify its truth. Independent evidence needs, for example, separately authenticated sender identity, bank account registry checks, or human verified outcomes **outside** the original model output.

### Value of additional reasoning (VOI)

Use the same cases and paired observations: direct predicted event probability, reasoned predicted event probability, verified event label, and cost of extra inference *all in comparable utility units*. Count action changes, mean net utility, confidence intervals using family-cluster bootstrap, false alarms, misses, abstention, p95. Compare a single candidate selected on development data with a family-locked independent holdout. A confidence gate is not a universal VOI optimum; a p-value alone is not evidence of deployment benefit.

## Actual implementation

- `integration/v52_decision_sandbox.py`: pure Python strict extractor, five-feature exploratory logistic, family-split guard, independent cost thresholds, inverse-odds caveat, paired empirical gain, advisory-only output.
- `tools/v52_exploratory_train.py`: explicit AI-authored label acknowledgement required, 5 family-grouped folds. Never uses `data/v51_validation24.jsonl` for training.
- `tests_v52/test_decision_sandbox.py`: offline positive and fail-close unit/contract checks. No real model or NPU hardware inference.
- `internal/evidence/v52/EXPLORATORY_RESULTS.json`: reproducible model-fit comparison. The comparator's q_scam semantics differ from the pause label; it is an illustrative diagnostic, not a calibrated classifier contest.

## Experiment outcome and non-promotion

Existing AI-authored development records: n=61, grouped families=37, positive pause-required labels=20; negative=41. Grouped 5-fold exploratory Brier for the logistic output = **0.1120304591**; raw `q_scam` versus a different `pause_required` binary label = **0.1102680449**. This does **NOT** establish superiority, independent calibration, or external validity. **NO CHANGE to v5.1 production policy/model**, following supplied patch governance. No Android APK rebuilt and no new Zoro-1 call was performed.

## SNM / 4D / NPU

- **SNM:** direct, quoted, negated and indirect request; credential exposure; anomalous payment; legitimate notices; omitted/malformed typed fields; stale responses; repeated re-prompts; model unavailability; user confirmation; callback replay.
- **Structure:** sender claim, message, model version/head, probabilities, feature extractor, facts, policy and reviewer are distinct entities.
- **Time:** record checkpoint revision, message date, model receipt, caller binding, policy version, human observation and revocation status separately.
- **Perspective:** legitimate customer false alarm, scam-victim missed threat, auditor evidence, model developer confounders and privacy subject data minimization.
- **Direction:** run input → typed head → feature → policy → UI, then independently reverse trace each UI decision back to source/event evidence. Model self-interpretation is not independent validation.
- **NPU:** **NOT_RUN**; there is no hardware profiler here. No claimed speedup, provider assignment or power savings.

## Release gates

Block production promotion while: `model_attested=false`, domain calibration NOT_ESTABLISHED, independent human evaluation NOT_RUN, missed PAUSE 2/7 and excessive ASK 5/12 in the historical AI-locked set, Android device NOT_RUN, and publisher/runtime verification incomplete. Reconfirm official Track 1 policies at the event.
