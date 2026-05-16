## P2-01: Quarter Mode Is Silently Ignored
Severity: CRITICAL
File: engine/calculator.py (line 83), engine/types.py (line 45)
Issue: `PVCRuleSet.quarter_mode` accepts both `"measurement_date"` and `"bill_date"`, but `calculate_pvc()` always calls `resolve_quarter(bill.measurement_date)` and never branches on `rules.quarter_mode`. A run with `quarter_mode="bill_date"` returns `validation_errors=[]` and still computes using `measurement_date`.
Risk: The engine can persist a rule set that appears to support a different quarter anchor while silently producing measurement-date numbers. That is exactly the kind of plausible-but-wrong output this review is supposed to stop before Phase 3.
Suggested fix: Either remove `"bill_date"` from the schema/UI entirely, or add the missing input and branching logic. If only measurement-date mode is supported, reject any other mode with a validation error instead of ignoring it.

## P2-02: Missing General Weights Are Treated As Zero Instead Of Blocking
Severity: HIGH
File: engine/components.py (line 72), engine/types.py (line 46)
Issue: `compute_general_w_components()` uses `rules.component_weights.get(cat)` and skips the component when the key is missing or falsy. That means an incomplete or misspelled rules payload silently under-calculates PVC with `validation_errors=[]`. In a direct run, full standard weights produced `85.00`, while `{"labour": 0.20}` produced `20.00` with no error.
Risk: Any malformed persisted rule set or partial API payload can drop plant/fuel/materials from the calculation without any visible failure. This is a silent wrong-number path in the core formula engine.
Suggested fix: Validate `component_weights` strictly in the Pydantic model. Require the expected keys for general works, reject unknown keys, and distinguish an explicit `0` weight from a missing key. The engine should block if a required configured component is absent.

## P2-03: Carry-Forward Payload Invariants Are Unenforced
Severity: HIGH
File: engine/types.py (lines 16-23), engine/w_derivation.py (lines 27-31)
Issue: `CarryForwardPayload` has no guardrails for `paid_ratio`, `recorded_qty`, `paid_qty_source`, or `carry_qty`, and `prorate_carry_forwards()` blindly applies `cf.amount * cf.paid_ratio`. A payload with `paid_ratio=1.2`, `paid_qty_source > recorded_qty`, and `carry_qty=-2` returns `validation_errors=[]` and increases the steel deduction anyway.
Risk: The engine accepts impossible carry-forward states and converts them into deterministic but incorrect W deductions. This is especially dangerous because Phase 3 plans to call the engine synchronously and trust its result.
Suggested fix: Add model validation for `0 <= paid_ratio <= 1`, `recorded_qty >= 0`, `paid_qty_source >= 0`, `paid_qty_source <= recorded_qty`, and `carry_qty >= 0`. Also reject duplicate carry-forward entries for the same source item/target bill combination instead of summing them blindly.

## P2-04: `carry_qty` Is Ignored Completely During Proration
Severity: HIGH
File: engine/types.py (line 21), engine/w_derivation.py (lines 18-31)
Issue: The engine stores `carry_qty` on the payload but never uses it in the math. A carry-forward with `carry_qty=0` still contributes `cf.amount * cf.paid_ratio` to the steel bucket. In a direct run, a bill with `steel_angles_amount=100` and a carry-forward of `amount=500`, `paid_ratio=1.0`, `carry_qty=0` produced `steel_angles=600` and `W=400`.
Risk: The carry-forward boundary case explicitly called out in the brief is currently wrong: a record that says there is no carried quantity can still reduce W. That can distort both the current bill and every downstream negative-carry recovery.
Suggested fix: Tie the monetary proration to the carried quantity invariant instead of ignoring it. At minimum, reject any carry-forward with `carry_qty <= 0` before using it. Prefer deriving the carry amount from `recorded_qty`, `paid_qty_source`, and `carry_qty` so the numbers cannot diverge.

## P2-05: Required Real-Workbook Regression Coverage Is Missing
Severity: HIGH
File: engine/tests/test_real_tender_fixtures.py (lines 20-38), engine/tests/fixtures/real_tenders/README.md (line 1)
Issue: The “real tender fixture” test is effectively disabled because there are no JSON fixtures in `engine/tests/fixtures/real_tenders/`. The directory test just skips when empty, so there is no automated Bill-1/Bill-2 regression against BCT-24-25-252 despite Phase 2 acceptance requiring real workbook values and despite the known Bill-2 workbook divergence needing explicit documentation.
Risk: The engine currently has no pinned end-to-end regression proving that current outputs match the trusted workbook inputs for the real tender case. Phase 3 could build on top of a numerically drifting engine without any red test.
Suggested fix: Add at least the confirmed BCT-24-25-252 Bill-1 and Bill-2 fixtures now, including the intentional Q4-vs-Q2 divergence note for Bill-2, and make the regression test fail when the fixture directory is empty.

## P2-06: Trace Output Does Not Meet The Accepted Provenance Contract
Severity: MEDIUM
File: engine/calculator.py (lines 25-67)
Issue: Phase 2 acceptance says every trace field should point to `{input_field, formula, index_ref, bill_line_ref}`. The current trace only stores rendered values plus quarter/base-month metadata. It does not identify which input field populated a component, which formula variant was used, or which source line/item produced the deduction.
Risk: Phase 3/7 cannot reliably expose cell-level provenance from the engine result even though the interface claims it exists. That weakens auditability and increases the chance that the frontend or export layer will re-derive explanations on its own.
Suggested fix: Expand the trace schema now to include formula identifiers, index series/month references, and source field/item references for W deductions and each component. If that structure is intentionally deferred, lower the acceptance claim in `TASKS.md` instead of returning a misleading trace shape.
