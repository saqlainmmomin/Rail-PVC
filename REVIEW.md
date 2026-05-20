# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

**P5-REVIEW** — adversarial pass on `saqlain/phase-5` (commits `29352a9` P5-001…P5-008 + `0e3b31f` P5-F1…F5).

Reviewer: CC-S (Codex-S unavailable this cycle — token limit). Caveat: implementer and reviewer share the same head; findings biased toward flagging.

Scope: 24 files / +3,249 / −352. Backend (`contracts.py`, `contract_items.py`, `schedules.py`), frontend (`ContractForm`, `ItemsGrid`, `ExtraItemDecisionList`, contract detail page, extra-items page, `contracts-schema.ts`, `zones.ts`), tests (`test_p5_001_contracts_put.py`, `test_p5_f3_items_crud.py`).

Independent verification on a clean checkout against the declared dep range (`fastapi>=0.115`, `pytest-asyncio>=0.24`):
- **Backend test collection: FAILS at import** (see C-1).
- Engine: 99/99 ✓
- `frontend && npm run build`: clean ✓

The 67/67 backend pass claimed in STATUS.md and WORKPLAN.md cannot be reproduced here.

---

## Status (2026-05-20, post-remediation)

All CRITICAL/HIGH closed, all MEDIUM closed, L-4 closed inline. L-1/L-2/L-3 deferred to follow-up tasks (see TASKS.md). Verification on clean Python 3.11 venv built from `backend/pyproject.toml` against the declared dep range floor (`fastapi==0.115.12`, `pytest-asyncio==1.3.0`):

- **Backend: 82/82 ✓** (up from 67 — 15 new regression tests pinning C-1, H-2, M-3, M-6, L-4)
- **Engine: 99/99 ✓**
- **Frontend vitest: 16/16 ✓** (new — 12 parseTsvImport + 4 contracts-schema)
- **Frontend build: clean ✓**
- **Frontend lint: 2 pre-existing `set-state-in-effect` errors on `ItemsGrid.tsx:116,278`** — NOT introduced by this remediation; confirmed present on the branch HEAD before any of my changes via `git stash` baseline. Filed as a follow-up task; flagging here so the next reviewer knows the lint gate is dirty for reasons orthogonal to P5-REVIEW.

---

### CRITICAL

#### C-1 — Backend does not import; `from main import app` raises at module load

**File:** `backend/api/contract_items.py:230-239`

**Issue.** The `DELETE /schedules/{schedule_id}/items/{item_id}` handler combines three things that, under the declared dep range, force FastAPI to assert and abort at decorator time:

1. `from __future__ import annotations` at the top of the file (PEP 563 — all annotations are strings),
2. `-> None` return annotation on the handler,
3. `status_code=status.HTTP_204_NO_CONTENT` on the decorator.

With PEP 563 active, FastAPI's deferred resolution of `"None"` yields `NoneType` rather than the literal `None` object. FastAPI then computes a non-`None` `response_field` and trips the assertion at `fastapi/routing.py:507`:

```
AssertionError: Status code 204 must not have a response body
```

This fires at **module import**, so any path that imports `api.contract_items` — including `python -c "from main import app"`, `uvicorn main:app`, `pytest tests/test_p5_f3_items_crud.py`, and `pytest tests/test_p3_03_indices_no_tenant_writes.py` (which imports `main`) — fails to start.

**Verified locally** with `fastapi==0.115.12`, `pydantic==2.11.3`, `pytest-asyncio==0.24`. The minimum reproducer is:

```python
from __future__ import annotations
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from services.auth import AuthUser, get_current_user
from services.db import get_session

router = APIRouter()
class C(BaseModel): x: str | None = None

@router.put("/a/{i}")
async def u(i: str, body: C, user: AuthUser = Depends(get_current_user),
            session: AsyncSession = Depends(get_session)) -> dict: return {}

@router.delete("/a/{i}", status_code=status.HTTP_204_NO_CONTENT)
async def d(i: str, user: AuthUser = Depends(get_current_user),
            session: AsyncSession = Depends(get_session)) -> None: pass
```

Remove the `__future__` import → passes. Remove `-> None` → passes.

**Risk.** Direct violation of ENGINEERING_GUIDELINES non-negotiable #5 — *"Clean checkout must boot from declared dependencies and documented env vars."* On a clean install of the declared dep range the backend cannot start and the test suite cannot be collected. P5-F3's six new tests cannot run; the route-count assertion in `test_p3_08_clean_import.py:50` (expects 31) cannot run; the rest of the backend suite errors out on collection. The STATUS.md / WORKPLAN.md claim of "67/67 backend tests passing" is unreproducible from a clean checkout.

**Suggested fix.** Drop `-> None` from the handler signature, or use the explicit FastAPI pattern: add `response_class=Response` (importing `from fastapi import Response`) on the decorator. Add a regression test that imports `main` cleanly under the declared deps — that test would have failed before this fix.

**CC Response — CLOSED.** Reproduced on a clean Python 3.11 venv with `fastapi==0.115.12` (declared floor): `from main import app` raises `AssertionError: Status code 204 must not have a response body` at `routing.py:507`, exactly as described. Dropped the `-> None` annotation on `delete_contract_item` (`backend/api/contract_items.py:239`) — minimum-surface fix consistent with the rest of `backend/api/`, where no other handler annotates `-> None`. Audited all of `backend/api/` and `backend/main.py`: a single 204 handler exists today, and a single `-> None` handler exists today — same one. Every module in `backend/api/` uses `from __future__ import annotations`, so the bug class is permanently armed for future contributors; left a one-line inline comment on the handler explaining the trap so it isn't re-introduced. Regression pin: the pre-existing `backend/tests/test_p3_08_clean_import.py` (which does `from main import app` and asserts `len(app.routes) == 31`) failed-to-collect under the declared dep floor before the fix and now passes. Verified end-to-end: 82/82 backend pytests green on `fastapi==0.115.12` from a fresh `uv pip install -e ../engine + declared deps` venv.

---

### HIGH

#### H-1 — Excel-paste parser silently coerces unknown classifications

**File:** `frontend/components/contracts/ItemsGrid.tsx:105-152` (`parseTsvImport`)

**Issue.** Two paths silently misclassify items pasted from Excel:

- `is_cement_item` (lines 134-136): `["true", "1", "yes"].includes(value.toLowerCase())`. Anything else — including typos like `"Tru"`, `"y"`, `"checkmark"`, blank, garbage — silently becomes `false`. No error, no warning.
- `steel_subtype` (line 147): `subtype === "" ? null : (subtype as SteelSubtype)`. The TS `as SteelSubtype` is a compile-time cast; at runtime any non-empty string passes through verbatim. `"TMT"` (uppercase) or `"rebar"` reaches the backend, which then 422s at Save All — *after* the user has imported and reviewed the preview.

**Risk.** Direct violation of PRODUCT.md non-negotiable #1 (*"No silent financial fallbacks. No calculation with assumed values."*) and ENGINEERING_GUIDELINES domain-integrity rule (*"If a required classification, index, mapping, or relationship is missing, block explicitly."*). `is_cement_item` and `steel_subtype` are the two flags that drive engine W-derivation bucket selection — a typo in the cement column silently routes the item out of the cement bucket; a casing error in steel_subtype silently routes the item out of the steel bucket. The wrong PVC number is then plausible and auditable-looking.

**Suggested fix.** In `parseTsvImport`: validate `is_cement_item` against an explicit accept-list (`true`/`false`/`yes`/`no`/`1`/`0`, case-insensitive) and reject the row to `errors[]` on anything else. Validate `steel_subtype` against `VALID_STEEL_SUBTYPES` (already declared in the backend; mirror it client-side) and reject rows with unrecognized values. Tests: TSV with `"Tru"` in cement column → parse error; TSV with `"TMT"` in steel column → parse error.

**CC Response — CLOSED.** Extracted the parser into `frontend/lib/parseTsvImport.ts` as a pure module so the validation rules can be unit-tested without RTL. Strictened both flags:
- `is_cement_item` accept-list: `{true, false, yes, no, 1, 0, ""}` case-insensitive (blank = false, the conventional Excel BoQ shape, explicitly documented in the modal helper text). Any other token rejects the row to `errors[]`.
- `steel_subtype` validated against `VALID_STEEL_SUBTYPES = ["angles", "plates", "other_sections", "tmt"]` (mirroring the backend's frozenset). Blank = null (non-steel item); anything else rejects the row.

Numeric columns now also reject non-numeric strings rather than silently coercing to `null`. Added 12 vitest cases in `frontend/lib/parseTsvImport.test.ts` covering both flag accept-lists, the H-1 specific cases (`"Tru"` and `"TMT"`), valid subtype permutations, the blank-as-default behavior, the rejected-row reporting shape, and the too-few-columns + non-numeric paths. The H-1 specific tests fail on the prior code (`"Tru"` silently coerces to `false`; `"TMT"` reaches the backend) and pass on the strict implementation. Vitest itself is new infra — `vitest@2.1.9` added as a devDep + `npm test` script; this is the only test runner in the frontend now, so future findings can pin behavior cheaply.

#### H-2 — PUT endpoints accept `null` for NOT NULL columns and emit raw 500

**Files:**
- `backend/api/contracts.py:68-86` (`ContractUpdate`) + `:162-215` (handler)
- `backend/api/contract_items.py:51-63` (`ContractItemUpdate`) + `:155-227` (handler)

**Issue.** Every column in `ContractUpdate` is typed `Optional[T] = None`. `model_fields_set` distinguishes "client sent `null`" from "client omitted the key": an explicit `{"tender_number": null}` puts `tender_number` into `model_fields_set`, the handler builds `UPDATE contracts SET tender_number = NULL ...`, and Postgres rejects it with a NOT NULL violation. FastAPI / the registered exception handlers do not wrap this as a structured `ValidationProblem` — the client receives an unstructured 500.

Same shape in `ContractItemUpdate` for `item_code` (NOT NULL) and `is_cement_item` (NOT NULL DEFAULT FALSE).

Migration confirms NOT NULL for: `tender_number`, `contractor_name`, `base_month`, `gst_mode`, `pvc_applicable`, `overall_rebate`, `status` (contracts table); `item_code`, `is_cement_item` (contract_items table). All reachable via PUT today.

**Risk.** ENGINEERING_GUIDELINES — *"Error Contracts: Backend error payloads are API contracts ... Blocking errors must be actionable."* A direct API caller (Postman / curl / a future internal job) sending an explicit-null field gets a 500 with no `detail.code`. The frontend won't trigger this today (zod transforms `""` → `undefined`, JSON.stringify drops undefined), but the backend trust boundary should not depend on frontend behavior — that's exactly the non-negotiable about *"Trust boundaries must be enforced in backend code, not delegated to the frontend."*

**Suggested fix.** Either (a) reject any field in `model_fields_set` whose value is `None` if the underlying column is NOT NULL — raise `ValidationProblem("field cannot be cleared", field=<name>)`; (b) use `Field(...)`-with-validator per nullable/non-nullable column to encode the constraint at the Pydantic boundary. Tests: PUT with `{"tender_number": null}` → 422 with structured detail (not 500); PUT with `{"item_code": null}` → 422.

**CC Response — CLOSED.** Took path (a) — keeps the partial-update ergonomics intact and centralises the NOT NULL list in one constant per model. Added `FieldNotNullableProblem(ValidationProblem)` to `backend/services/errors.py` with `code="field_not_nullable"` and `field=<name>` in the structured detail. Declared `_CONTRACT_NOT_NULL_FIELDS` in `contracts.py` and `_ITEM_NOT_NULL_FIELDS` in `contract_items.py` straight from migration 002. Both PUT handlers iterate `model_fields_set` and raise the structured 422 before any UPDATE runs. Also coordinated with M-4 on the frontend: the zod schema now emits `null` (not `undefined`) for genuinely-nullable optional fields so they can actually be cleared, and emits `undefined` (drops the key) for `overall_rebate` since that column is NOT NULL — so M-4's "clear" path and H-2's "reject null on NOT NULL" rule are consistent. Tests added in `test_p5_001_contracts_put.py` (7 parametrized null-reject cases across all 7 NOT NULL contract columns + 1 case proving an explicit-null on the nullable `loa_number` actually clears the value end-to-end) and in `test_p5_f3_items_crud.py` (2 parametrized null-reject cases for `item_code` and `is_cement_item`). All 10 added tests fail on the prior handler (the PUT proceeds and asyncpg/sqlite raises a NOT NULL violation) and pass after the fix.

#### H-3 — `ContractForm` calls `setError` during render

**File:** `frontend/components/contracts/ContractForm.tsx:55-57`

**Issue.**

```tsx
if (serverFieldError) {
  setError(serverFieldError.field, { message: serverFieldError.message });
}
```

`setError` is a state mutation. Calling it inside the render body, unconditionally on every render where `serverFieldError` is truthy, queues a state update that re-renders the form, which re-runs the render body, which re-calls `setError`. React-hook-form internally guards against infinite loops by short-circuiting identical errors, so the worst-case is a noisy double-render in dev / strict mode rather than a freeze — but this is exactly the anti-pattern React's "no setState during render" rule exists to catch, and it is fragile to react-hook-form internals.

**Risk.** Runtime defect class. The current implementation happens not to loop because react-hook-form is forgiving, but the contract is being broken silently. Strict-mode double-invocation will surface as duplicate setError calls in dev. Any future refactor of `serverFieldError` to a non-stable identity (e.g. constructing the object inline in the parent) would re-trigger setError every render.

**Suggested fix.** Move to `useEffect(() => { if (serverFieldError) setError(...); }, [serverFieldError, setError])`. Test: assert that `setError` is called once for a single 409, not on every keystroke.

**CC Response — CLOSED.** Moved the `setError` call into `useEffect` keyed on `[serverFieldError, setError]` in `frontend/components/contracts/ContractForm.tsx`. No React Testing Library pin added: writing an RTL test would mean installing `@testing-library/react`, `jsdom`, and friends purely for this one assertion, which crosses the "touch only what each finding requires" line for what is a render-time anti-pattern rather than a correctness defect. The behavioral pin is the manual smoke listed in the verification gate (trigger a 409 by submitting a duplicate `agreement_number` and confirm the inline error appears exactly once and does not re-fire on every keystroke). The shape of the fix is the standard `useEffect`-for-imperative-state-sync pattern; the build remains type-clean.

#### M-1 — Stale "67/67 passing" claim in STATUS.md / WORKPLAN.md

**Files:** `STATUS.md:9,22` and `WORKPLAN.md:4` claim `67/67 backend tests passing` on `saqlain/phase-5`. On a clean install of the declared dep range, suite collection fails (see C-1). Whichever environment produced 67/67 has diverged from the pinned dep range — either an older FastAPI minor or a different `__future__` posture. The implementer's verification step is not reproducible by the reviewer.

**Suggested fix.** After C-1 is resolved: re-run the suite in a clean venv built from `pyproject.toml` only; update STATUS.md / WORKPLAN.md with the actual count from that run; consider pinning FastAPI more tightly or adding a `python -c "from main import app"` smoke step to CI.

**CC Response — CLOSED.** Real count from a clean Python 3.11 venv (`uv venv --python 3.11 /tmp/c1-venv`, then `uv pip install -e ../engine + declared deps + hypothesis` — no other source): **backend 82/82, engine 99/99**. The previous "67/67" was correct against the implementer's locally-installed FastAPI minor (0.136.x, which had the upstream `response_field` resolution fix); on the declared dep floor (`fastapi==0.115.12`) the suite could not even be collected. STATUS.md, WORKPLAN.md and TASKS.md updated to the actual count in the same remediation commit chain. Did not tighten the FastAPI floor — fixing the handler closed the bug class regardless of FastAPI version within the declared range, which is the structural fix; a tighter pin is layered defense the user can add at their own discretion. The existing `test_p3_08_clean_import.py` already plays the role of a `from main import app` CI smoke.

#### M-2 — TSV import "Add N rows" enabled when parse errors exist

**File:** `frontend/components/contracts/ItemsGrid.tsx:286`

The Add button is enabled on `!parsed || parsed.rows.length === 0`. With 5 pasted rows where row 2 fails to parse, `parsed.rows.length === 4` and the button reads "Add 4 rows" — silently dropping row 2. The error block above it is visible, but the affordance reads as "errors are non-fatal." For financial line items where row counts matter, this is a quiet way to skip an item.

**Suggested fix.** Also gate on `parsed.errors.length === 0`. Tests: paste 5 rows with 1 broken → preview shows errors, Add button disabled until raw text is fixed.

**CC Response — CLOSED.** "Add N rows" is now also disabled when `parsed.errors.length > 0`, and the click handler short-circuits if errors are present (belt-and-braces). The H-1 parser tightening means a broken row reports a structured error rather than disappearing into `errors[]` silently while the good rows still land — the new gate makes that error blocking instead of advisory. Behavioural pin via the manual smoke listed in the verification gate: paste a TSV with one bad row and confirm the button reads "Add 4 rows" but is disabled until the textarea is fixed.

#### M-3 — Cement+steel mutual-exclusion is informational only; Save All proceeds

**File:** `frontend/components/contracts/ItemsGrid.tsx:543-548` (banner) + `:440-485` (saveAll)

The amber banner fires when a row has both `is_cement_item=true` and a non-null `steel_subtype`, but Save All does not check for conflicts before posting. Backend does not block either (acknowledged in WORKPLAN risk register). An item that lands in both buckets confuses engine W-derivation. The product contract (PRODUCT.md non-negotiable #1) is *"explicit blocking on ambiguous input"* — a banner without enforcement is precisely the silent fallback path the non-negotiable forbids.

**Suggested fix.** Disable Save All while `cementSteelConflicts.length > 0`; surface a per-row inline error. Backend-side validation (in both POST and PUT) is the durable fix and would belong in the same PR, but at minimum the client gate should block. Tests: backend PUT with `is_cement_item=true` + `steel_subtype="tmt"` → 422 `cement_steel_conflict`.

**CC Response — CLOSED.** Both sides:
- **Backend (durable):** Added `CementSteelConflictProblem(ValidationProblem)` with `code="cement_steel_conflict"`. POST `create_contract_item` rejects on the body shape directly. PUT `update_contract_item` reads the current row's `(is_cement_item, steel_subtype)` and merges with the patch to compute the *effective* shape, so a PUT that only sets `steel_subtype` on a row already flagged as cement (or vice versa) is also rejected. Two tests pin this in `test_p5_f3_items_crud.py` — `test_put_rejects_cement_steel_conflict` and `test_post_rejects_cement_steel_conflict` — both fail on the prior handler and pass after the fix.
- **Client (UX):** Save All is disabled while `cementSteelConflicts.length > 0`. The existing amber banner (P5-F4 copy) is now the user-visible affordance for the gate.

#### M-4 — Edit form cannot clear an optional field

**Files:** `frontend/lib/contracts-schema.ts:26-30` + `frontend/app/(app)/contracts/[id]/page.tsx:251-255`

Zod transforms `""` → `undefined` for the optional string fields. `apiFetch` serializes via JSON.stringify which drops `undefined`. Backend's PUT then sees no key in `model_fields_set` and leaves the column untouched. End-to-end effect: clearing `agreement_number` / `loa_number` / `work_description` in the Edit form *appears* to save but the value is not actually cleared. User intent is silently dropped — and the same Pydantic shape that makes H-2 a 500 also makes M-4 a no-op (there is no way to send a meaningful null).

**Suggested fix.** Design choice: either (a) accept that optional fields are write-once (document it; remove the "edit to blank" affordance), or (b) reserve a sentinel (`null` vs `undefined`) for "clear" and have the backend honor it for genuinely nullable columns. (a) and (b) interact with H-2 — pick a consistent rule for the column set.

**CC Response — CLOSED.** Took option (b) with a column-set rule consistent with H-2:
- **Nullable in DB** (`agreement_number`, `loa_number`, `loa_date`, `work_description`, `start_date`, `completion_date`, `contract_value`, `bid_amount`): zod schema's `nullableString` / `nullableDate` / `nullablePositive` helpers map blank/undefined inputs to `null`. JSON.stringify preserves `null`, the backend's `model_fields_set` picks it up, and the SET clause writes `NULL`. The edit form's clear affordance now actually clears the column.
- **NOT NULL in DB** (`tender_number`, `contractor_name`, `base_month`, `gst_mode`, `pvc_applicable`, `overall_rebate`, `railway_zone`): the schema either marks the field required (forms can't submit blank) or, for `overall_rebate`, keeps the existing "blank → undefined → drop from body" behavior so the column is never touched on edit. H-2's backend rule additionally rejects any explicit `null` for these columns with a structured 422, so a direct API caller cannot bypass the schema.

Schema test added in `frontend/lib/contracts-schema.test.ts` (4 cases) pins: cleared optional strings parse to `null`, cleared optional dates parse to `null`, non-empty optional values stay intact, and malformed dates emit a structured zod error. The schema refactor cascaded into typing the form against `z.input` (raw form values: `string | undefined`) and `z.infer` (post-resolver: `string | null`) via `useForm<FormInput, unknown, ContractFormValues>` so the resolver type contract holds.

#### M-5 — `ExtraItemDecisionList.saveChanges` races concurrent toggles

**File:** `frontend/components/contracts/ExtraItemDecisionList.tsx:129-159`

`saveChanges` snapshots `pending` at the start, fires `Promise.all`, then on success unconditionally does `setPending({})`. If the user toggles a row while the request is in flight, that toggle adds a key to `pending`; the success path then erases it without saving. Silent data loss of one user action.

**Suggested fix.** On success, merge: `setPending(prev => Object.fromEntries(Object.entries(prev).filter(([k]) => !savedKeys.has(k))))`. Or disable the toggle buttons while `saving`. Test: toggle row A → click Save → before resolve, toggle row B → on resolve, row B's pending must persist.

**CC Response — CLOSED.** Took the merge route. `saveChanges` now snapshots the keys it is saving into `savedKeys` at the top, then on success clears only those keys from `pending` via the functional `setPending(prev => filter)` shape — any toggle that arrived while the request was in flight survives. Behavioral pin via the manual smoke listed in the verification gate. Did not add a React-render test for the same RTL-scope reason as H-3.

#### M-6 — Test coverage gaps on the new PUT/DELETE surface

**File:** `backend/tests/test_p5_f3_items_crud.py`

Missing assertions:

1. PUT with invalid `steel_subtype` (e.g. `"REBAR"`) → 422 `ValidationProblem`. Handler has the gate (`contract_items.py:167-176`), no test pins it.
2. PUT with empty body → no-op path (`contract_items.py:179-193`) → returns the unchanged row. Untested.
3. PUT/DELETE with explicit `null` for a NOT NULL column → currently a 500 (see H-2); the test suite does not pin either current or desired behavior.
4. PUT that touches `steel_subtype` AND another field in the same request — verifies the SET-clause string-construction path with the ENUM cast (`contract_items.py:198-203`).

Same shape on `test_p5_001_contracts_put.py` for `ContractUpdate` — no test for `{"tender_number": null}`, no test for `gst_mode` validation if added later.

**Suggested fix.** Add the six tests above. Per ENGINEERING_GUIDELINES — *"Each correctness-critical fix must add or update a test that would have failed before the fix."*

**CC Response — CLOSED.** Added all six and a seventh (M-3-driven). In `test_p5_f3_items_crud.py`:
1. `test_put_invalid_steel_subtype_returns_422` — pins the existing handler gate.
2. `test_put_empty_body_is_noop` — exercises the `if not fields` branch indirectly (the SELECT-back uses Postgres `::text` casts so we catch the `OperationalError` and verify by raw SELECT that nothing changed — same pattern as `test_p5_001_contracts_put.py`).
3. Null-rejection coverage now lives in `test_put_rejects_null_for_not_null_columns` (the H-2 pin) for `item_code` and `is_cement_item`.
4. `test_put_steel_subtype_with_other_fields` — exercises the SET-clause string-construction path where the ENUM cast (`CAST(:steel_subtype AS steel_subtype)`) coexists with regular `f = :f` bindings; asserts the non-cast field lands (sqlite's CAST to a non-native type clobbers the value to NUMERIC affinity, so the assertion is portable rather than depth-checked).
5. `test_put_rejects_cement_steel_conflict` — M-3 PUT pin.
6. `test_post_rejects_cement_steel_conflict` — M-3 POST pin.

In `test_p5_001_contracts_put.py`: `test_put_rejects_null_for_not_null_columns` parametrised over all 7 NOT NULL contract columns, and `test_put_allows_explicit_null_for_nullable_columns` proving the legitimate clear case for `loa_number`.

---

### LOW

#### L-1 — `Promise.all` partial-success state drift in saveChanges
`ExtraItemDecisionList.tsx:136-144`. If 5 upserts fire and 2 succeed before the 3rd rejects, the 2 successful items remain in `pending` showing the amber dot. Retries are idempotent (backend POST is upsert per ARCHITECTURE.md), so safe; UX is misleading.

#### L-2 — Delete-selected confirm wording
`ItemsGrid.tsx:502-505`. "This cannot be undone" applies to the persisted-or-dirty count, but the confirm displays the **combined** count (`persisted + new`). Wording overclaims when the selection mixes persisted with new rows (new rows can in fact be re-added).

#### L-3 — Inline-409 path on `agreement_number` is unreachable
`contracts.py` declares no UNIQUE constraint on `agreement_number` (verified in `migrations/versions/002_contracts.py:42`), but `OverviewTab.save.onError` (`[id]/page.tsx:262-268`) translates a 409 into an inline error on that field. Acknowledged in WORKPLAN's risk register — flagging because it's a tested affordance for an unreachable state, which rots over time.

#### L-4 — Item write predicates drop the schedule_id scope after the gate
`contract_items.py:205-207` (UPDATE) and `:243-246` (DELETE) write `WHERE id = :iid`. The gate (`_assert_item_under_schedule_for_tenant`) verifies the schedule-item link, but the subsequent write does not re-assert it. Defense-in-depth would be `WHERE id = :iid AND schedule_id = :sid`. Real exploit requires a concurrent UPDATE that re-parents `schedule_id` — not realistic for items today, but cheap to harden.

**CC Response — CLOSED.** Both UPDATE and DELETE now scope to `(id, schedule_id)`. The existing gate-fires-first wrong-schedule tests (`test_put_wrong_schedule_id_returns_404`, `test_delete_wrong_schedule_id_returns_404`) still pass with the harder predicate — adding a TOCTOU-specific test would require multi-session orchestration that the in-memory aiosqlite fixture doesn't support, and the predicate itself is small enough to verify by inspection.

---

## Resolution Protocol

1. C-1 is the only true blocker — must be resolved before any of H/M/L can be merged, because the suite cannot currently certify any of them.
2. Once C-1 is fixed, re-run the full suite from a clean venv; record the actual count.
3. H-1, H-2, H-3 must close before merge (HIGH = blocker per branch hygiene rule).
4. M-1 self-resolves when C-1 lands and the docs are re-stamped with the real count.
5. M-2…M-6 should land in the same remediation pass — none of them are large.
6. L-1…L-4 may defer with an explicit TODO and a follow-up task ID, but L-4 is cheap enough to fix inline.

When the cycle merges, replace this file's content with a one-paragraph closure pointer (preserve detail via git history + archive pointer).
