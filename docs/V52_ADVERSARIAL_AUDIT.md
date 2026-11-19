# v5.2 adversarial audit — elenchus, falsification and remaining issues

## Core repeated assumption

**Assumption under scrutiny:** "Reversing Zoro-1's probability with odds ratios and feeding a 3–5 variable logistic regression can validate the original answer and improve accuracy."

**Counterexample:** In an institution-impersonation SMS, Zoro-1 incorrectly emits `q_scam=0.95` and `q_pressure=0.93` because both questions depend on the same misunderstood sentence. A five-feature model trained on near-duplicate AI-authored examples can emit an even higher probability. The inverse-log-odds calculation reconstructs the very same assumption, not a new fact. An attacker then asks for an OTP.

**Direct answer:** No independent truth was added. Only a verified caller record or independent evaluation on human-annotated, group-locked examples can validate the claim. The final action remains behind a deterministic stop/verify gate. Mathematically consistent numbers can still be wrong.

### Findings

| ID | Severity | Finding | Reproduction/evidence | Resolution or hold |
|---|---|---|---|---|
| A01 | P0 | v5.1 requires PAUSE but historical AI-locked set produced ASK on 2 of 7 cases | `docs/V51_OPEN_ISSUES.md` | Not resolved; independent new dataset needed |
| A02 | P0 | Unnecessary ASK on 5 of 12 normal synthetic locked cases | Same | Not resolved; evaluate legitimate-user burden |
| A03 | P0 | Actual model source and independent attestation | `model_attested=false` in v5.1 status | Not authenticated here; don't infer identity from echoed name |
| A04 | P0 | Regression scores versus true fraud outcomes | Only AI-authored labels used for this prototype | Experimental logistic disabled for production |
| A05 | P0 | Odds inverse is algebraic, not external confirmation | `inverse_odds_check` tests | Explicit no-independent-evidence flag; separate facts needed |
| A06 | P0 | Confounded threshold use | v5.1 semantic `0.70`, book's reasoning 0.7, action p* | Separate functions and contracts, no silent tuning |
| A07 | P1 | Python 3.13 Unicode 15.1.0 regeneration differs from packaged JS generated with Unicode 15.0.0 | `tools/export_v51_semantic.py --check` reproduces `STALE_V51_SEMANTIC_DATA` | Frozen v5.1 generated artifact preserved; a pinned Unicode build env needed |
| A08 | P1 | v5.1 LinkGuard skills path registry missing two v5.1 references | `tests_linkguard` pre-upgrade test | Metadata path inventory corrected in v5.2 |
| A09 | P0 | No real Zoro-1 or NPU execution was carried out this upgrade | Current session tools and logs | NOT_RUN; v5.1 historical records are not new execution |
| A10 | P1 | Android actual device installation and performance | v5.1 state | NOT_RUN |
| A11 | P1 | Source package including debug APK; no verified production signature | v5.1 apps/README | Debug only, not release certified |
| A12 | P1 | Full Drive historical merge not verified | Root+current Drive folder metadata; uploaded ZIP actual | Do not merge every past file blindly; user-selected v5.1 baseline governs |

## 4D audit of a failure

- **Structure:** a text classification score is not a sender-identity or bank registry fact.
- **Time:** model direct output, optional reasoning, updated message, human report and stale UI must have distinct versions.
- **Perspective:** a bank worker incurs workload from false holds while a potential victim suffers loss from missed holds; both matter.
- **Direction/reverse:** an emitted warning must trace to actual observed evidence; re-evaluating the same Zoro statement is not an independent source.

## SNM counterexample families

`S01` valid direct request → expected risk hold; `S02` quote/negation with keywords → no unjustified PAUSE; `S03` implicit off-platform solicitation → caution; `S04` partial fields/NaN → fail-closed; `S05` provider unavailable → no fabricated inference; `S06` duplicated/out-of-order request → immutable version; `S07` new authentic independent verification → human review update only; `S08` trained logistic overfits → default NO CHANGE and rollback; `S09` NPU unavailable → CPU still measured separately, no NPU claim.

## Next acceptance evidence

A. Human-independent labels and source provenance. B. Real typed Zoro-1 checkpoint/head/runtime manifest (temperature, exact revision, no silent default). C. Group-held-out signed evaluation with paired false negative/false positive/abstention and p95. D. Separate direct-vs-reasoned calibration and net-utility confidence interval in consistent units. E. Android APK build and real device run. F. Repackage + CRC + clean extractions and exact verified paths. G. Official contest conditions before live demo and P0 ownership approval.
