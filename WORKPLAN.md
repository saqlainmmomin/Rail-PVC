# WORKPLAN.md — Phase 5: Contract Setup UI

**Last updated:** 2026-05-19 (Phase 5 implementation complete on `saqlain/phase-5`, uncommitted)
**Status snapshot:** Phases 0–4 + TEST-P3P4 merged to `main`. **Phase 5 UI implementation complete (P5-001…P5-008) on `saqlain/phase-5`** — 61/61 backend tests, `next build` clean. Needs commit + manual smoke + `P5-REVIEW` before merge. Shubham's SH-P5 backend track still in progress.

---

## Next Steps (in order)

1. **Commit P5-001…P5-008 on `saqlain/phase-5`** in a single meaningful commit, then push to origin.
2. **Open PR** (`saqlain/phase-5` → `main`) with description listing the 8 tasks + acceptance criteria covered.
3. **Manual browser smoke** (see "Manual Smoke Plan" below) — must run before review since the existing test suite does not exercise the new pages live.
4. **Kick off `P5-REVIEW`** — Codex-S adversarial pass; record findings in `REVIEW.md`.
5. **Resolve any CRITICAL/HIGH findings** from review; iterate until clean.
6. **Merge `saqlain/phase-5`** to `main` once review is clean (no CRITICAL/HIGH).
7. **Delete merged branches**: `saqlain/phase-5`, `saqlain/test-p3p4` (and any older merged remotes).
8. **Sync with Shubham on SH-P5 progress** (G-1/G-2/G-3) — coordinate `SH-P5-REVIEW` once his branch is ready.
9. **Phase 6 kickoff once both Phase 5 merge + SH-P5 G-1/G-2 are on `main`** — bill entry UI (C-1…C-3).

### Manual Smoke Plan (before P5-REVIEW)

| Flow | Steps | Expected |
|---|---|---|
| Create | `/contracts` → "New contract" → fill required fields → submit | Redirects to `/contracts/{id}` with new tender_number in header, status badge "Draft" |
| Edit | Overview → Edit → change `contractor_name` → Save | Returns to read view with new name; query invalidated |
| Validation | Submit with `completion_date < start_date` | Inline error, no API call |
| Schedules | Schedules tab → Add ExtraNS schedule | Row appears; "Manage extra-item decisions →" link appears in header |
| Items | Items tab → select schedule → +Add row → fill → Save All | "Saved N row(s)"; rows persist on tab reload |
| Mutual-exclusion warning | Items grid: set `is_cement_item=true` + `steel_subtype=tmt` | Amber warning banner visible above grid |
| Extra-items | Click header link → toggle one item Undecided → Yes | Banner updates; row persists across reload |

---

---

## Phase 5 — Contract Setup UI

### Goals

A user starts with an empty tenant and, by the end of Phase 5, can produce a contract that is fully configured for bill entry (Phase 6) and PVC calculation (Phase 7). That means: a contract row with all required metadata, at least one schedule, contract items under each schedule (with `is_cement_item` and `steel_subtype` correctly classified), and — when the contract has ExtraNS items — explicit eligibility decisions that prevent the engine from blocking at run time. The user navigates from the contract list, clicks "New contract", fills a form, is redirected to a persistent detail page with tabs for schedules and items, and can link out to a dedicated extra-items page. No session continuity is required: the contract row is created as `Draft` on first submit, so the user can always return.

---

### Out of Scope

- Bills, bill_lines, recoveries (Phase 6)
- PVC runs, approvals, run results (Phase 7)
- Carry-forwards (Phase 6/7)
- Document upload UI — page stub exists; stays empty
- Index ingestion — ops-side; read-only in this app
- PVC rule set editing — auto-created by P3-07 on contract creation; edit surface is Phase 7 prep
- multi-user RBAC (post-MVP)

---

### Resolved Decisions

| # | Question | Choice | Reason |
|---|---|---|---|
| Q1 | Creation flow shape | Shallow create at `/contracts/new` → redirect to `/contracts/[id]` with tabs (Overview \| Schedules \| Items) | Matches the DB structure; each step is atomic and recoverable; no in-memory draft state required |
| Q2 | Items entry UX | AG Grid inline-editable table + Save All button | BOQ entries are bulk; row-by-row form doesn't scale to 50+ items; AG Grid already in ARCHITECTURE.md |
| Q3 | Form library | `react-hook-form` + `zod` | Already decided; zod mirrors Pydantic ContractCreate; `@hookform/resolvers/zod` bridges them |
| Q4 | Railway zone picker | Typed dropdown, all 16 VALID_ZONES, no escape hatch | Wrong zone = wrong JPC city = wrong steel series; enum is exhaustive; new zones require a migration so the dropdown can be updated at the same time |
| Q5 | Save-and-resume | Backend draft rows — `POST /api/contracts` creates `status='Draft'` immediately; user can return via contract list | Matches existing status enum; no localStorage second-source-of-truth |
| Q6 | Validation split | Client validates dates + numerics; server owns uniqueness | Client catches date ordering + `bid_amount ≤ contract_value` instantly; `agreement_number` uniqueness can only be checked server-side; zod is already present so `.refine()` costs nothing |
| Q7 | Extra-item decisions | Separate page `/contracts/[id]/extra-items`, linked from contract detail when ExtraNS schedule exists | Keeps the detail page tabs uncluttered; decisions are a distinct workflow, not part of setup navigation |
| Q8 | Out-of-scope confirmation | All confirmed out of scope | See list above |

---

### Route Map

```
frontend/app/(app)/
└── contracts/
    ├── page.tsx                      [P4 — done] Contract list
    │   Modify: enable "New contract" button (→ /contracts/new)
    │   Modify: enable "View" row links (→ /contracts/[id])
    │
    ├── new/
    │   └── page.tsx                  [P5-003] Creation form
    │       Auth: inherited from (app) layout
    │       API: POST /api/contracts → 201 → redirect /contracts/[id]
    │
    └── [id]/
        ├── page.tsx                  [P5-004, P5-005, P5-006, P5-007]
        │   Auth: inherited from (app) layout
        │   API (mount): GET /api/contracts/{id}
        │   Tabs (via ?tab= searchParam, default=overview):
        │   ├── overview              GET /api/contracts/{id} (read) 
        │   │                         PUT /api/contracts/{id} (edit mode)
        │   ├── schedules             GET /api/contracts/{id}/schedules
        │   │                         POST /api/contracts/{id}/schedules
        │   └── items                 GET /api/contracts/{id}/schedules (schedule selector)
        │                             GET /api/schedules/{id}/items (per selected schedule)
        │                             POST /api/schedules/{id}/items (Save All)
        │
        └── extra-items/
            └── page.tsx              [P5-008] Eligibility decisions
                Auth: inherited from (app) layout
                Shown: link visible on /contracts/[id] only when ≥1 ExtraNS schedule exists
                API: GET /api/contracts/{id}/extra-item-decisions
                     POST /api/contracts/{id}/extra-item-decisions (upsert per item)
```

**Backend gap — must land before B-3 can ship:**

`PUT /api/contracts/{id}` is in `ARCHITECTURE.md` but **does not exist** in `backend/api/contracts.py`. Task P5-001 adds it.

---

### Component Inventory

| New component | Location | Props summary | Reuses |
|---|---|---|---|
| `ContractForm` | `components/contracts/ContractForm.tsx` | `defaultValues?: Partial<ContractDraft>`, `onSubmit(data): Promise<void>`, `isSubmitting: bool` | `Button` (submit), native inputs |
| `ZoneSelect` | `components/contracts/ZoneSelect.tsx` | `value: string`, `onChange(zone: string): void`, `error?: string` | Tailwind select; VALID_ZONES constant from `lib/zones.ts` |
| `ContractOverviewTab` | inline in `[id]/page.tsx` | `contract: ContractDetail`, `onEdit(): void` | `Badge` (status), `Button` (Edit) |
| `ScheduleForm` | `components/contracts/ScheduleForm.tsx` | `contractId: string`, `onCreated(schedule): void` | `Button` (submit) |
| `ScheduleList` | inline in `[id]/page.tsx` schedules tab | `schedules: Schedule[]`, `selectedId: string \| null`, `onSelect(id): void` | `Badge` (schedule_type) |
| `ItemsGrid` | `components/contracts/ItemsGrid.tsx` | `scheduleId: string`, `onSaved(): void` | AG Grid Community; `Button` (Save All) |
| `ExtraItemDecisionList` | `components/contracts/ExtraItemDecisionList.tsx` | `contractId: string` | `Button` (per decision toggle) |

**AG Grid is not yet installed** — P5-002 adds it. `ItemsGrid` cannot be built before P5-002 completes.

---

### Task Status (post-implementation, 2026-05-19)

| ID | Task | Status |
|---|---|---|
| P5-001 | Backend: PUT `/api/contracts/{id}` + expanded GET | ✅ complete |
| P5-002 | Frontend deps + `lib/zones.ts` + `lib/contracts-schema.ts` | ✅ complete |
| P5-003 / B-1 | `/contracts/new` creation form | ✅ complete |
| P5-004 / B-2 | `/contracts/[id]` detail page + tab shell | ✅ complete |
| P5-005 / B-3 | Overview tab inline edit | ✅ complete |
| P5-006 / B-4 | Schedules tab + `ScheduleForm` | ✅ complete |
| P5-007 / B-5 | Items tab — AG Grid `ItemsGrid` | ✅ complete |
| P5-008 | `/contracts/[id]/extra-items` decision page | ✅ complete |

**Implementation notes captured during the session:**

- AG Grid 35.x API uses `AllCommunityModule` registration and `themeQuartz.withParams({…})` (legacy module imports are gone).
- `react-hook-form` `setValueAs` is the cleanest way to append `-01` to a `<input type="month">` value — keeps validation pure inside zod and avoids a separate submit transform.
- Postgres `::text` casts in the GET SELECT make the route handler impossible to fully exercise under aiosqlite; the P5-001 test split is: tenant-gate + validation paths run end-to-end, the SELECT-back path is documented as Postgres-only.
- `model_fields_set` is the canonical way to express "patch semantics" in Pydantic v2 — no need for a custom `exclude_unset` dance.

---

### Task Breakdown

#### P5-001 — Backend: `PUT /api/contracts/{id}`

**Scope:** Add the missing update endpoint so B-3 (edit) has something to call.

**Files touched:**
- `backend/api/contracts.py` — add `ContractUpdate` Pydantic model + `@router.put("/{contract_id}")` handler
- `backend/tests/test_contracts_put.py` — new test file

**Acceptance criteria:**
- `PUT /api/contracts/{id}` with valid body → `200 + updated fields`
- Wrong-tenant contract → `404 NotFoundProblem`
- Invalid `railway_zone` → `422 ValidationProblem`
- `base_month.day != 1` → `422 ValidationProblem`
- `agreement_number` conflict (if unique constraint exists) → `409 ConflictProblem`
- Existing backend suite (55 tests) still green

**Test plan:**
- Unit: valid update, wrong-tenant → 404, bad zone → 422, bad base_month → 422
- `ContractUpdate` should use `model_fields_set` so unset optional fields do not overwrite existing values (partial update semantics)

**LOC estimate:** ~60 backend + ~40 test ≈ 100 total

---

#### P5-002 — Frontend: Install deps + shared constants

**Scope:** Add missing packages and the frontend VALID_ZONES constant. Unblocks all other P5 tasks.

**Files touched:**
- `frontend/package.json` — add `react-hook-form`, `@hookform/resolvers`, `zod`, `ag-grid-community`, `@ag-grid-community/react`
- `frontend/lib/zones.ts` — new; exports `VALID_ZONES` as a typed tuple of 16 zone codes with display names
- `frontend/lib/contracts-schema.ts` — new; exports `contractCreateSchema` (zod) mirroring `ContractCreate`

**Acceptance criteria:**
- `next build` clean after install
- `VALID_ZONES` list matches `backend/services/zone_mapping.py:VALID_ZONES` exactly (manually verified at task time)
- `contractCreateSchema` validates: `tender_number` non-empty, `contractor_name` non-empty, `railway_zone` in VALID_ZONES, `base_month` matches `/^\d{4}-\d{2}-01$/`, `start_date ≤ completion_date` (if both supplied), `base_month ≤ start_date` (if both supplied), `contract_value > 0` (if supplied), `bid_amount ≤ contract_value` (if both supplied)

**Test plan:**
- Unit (Vitest): zod schema — valid input passes, each `.refine()` rejects correctly
- No browser test needed for constants

**LOC estimate:** ~80 (schema + zones + lockfile excluded)

---

#### P5-003 — B-1: Contract creation form `/contracts/new`

**Scope:** Creation form; on submit creates a Draft contract and redirects to the detail page.

**Files touched:**
- `frontend/app/(app)/contracts/new/page.tsx` — new page
- `frontend/components/contracts/ContractForm.tsx` — new; driven by react-hook-form + `contractCreateSchema`
- `frontend/components/contracts/ZoneSelect.tsx` — new; renders 16-option `<select>` from VALID_ZONES
- `frontend/app/(app)/contracts/page.tsx` — change "New contract" button from `disabled` to `<Link href="/contracts/new">`

**Field list (from `ContractCreate` Pydantic model):**

| Field | Type | Required | Client rule |
|---|---|---|---|
| `tender_number` | text | yes | non-empty |
| `agreement_number` | text | no | — |
| `loa_number` | text | no | — |
| `loa_date` | date | no | — |
| `contractor_name` | text | yes | non-empty |
| `work_description` | textarea | no | — |
| `railway_zone` | dropdown | yes | must be in VALID_ZONES |
| `base_month` | month input → `YYYY-MM-01` | yes | must be first of month |
| `start_date` | date | no | ≤ completion_date, ≥ base_month |
| `completion_date` | date | no | ≥ start_date |
| `contract_value` | decimal | no | > 0 if supplied |
| `bid_amount` | decimal | no | ≤ contract_value if both supplied |
| `gst_mode` | select | yes | `inclusive` / `exclusive` |
| `pvc_applicable` | checkbox | yes | default true |
| `overall_rebate` | decimal | no | stored as fraction (0.15 = 15%); label must say "e.g. 0.15 for 15%" |

**Acceptance criteria:**
- Zod errors shown inline per field before submit
- `base_month` `<input type="month">` → appends `-01` before sending to API
- On `POST /api/contracts` success → `router.push("/contracts/" + id)`
- On 422 `conflict` (agreement_number) → inline error on that field, not just toast
- On network error → toast (existing apiFetch behavior)

**Test plan:**
- Unit: `ContractForm` renders; zod validation fires; submit calls `apiFetch` with correct body
- Browser: fill all required fields → submit → land on `/contracts/{id}` with correct tender_number in heading
- Browser: submit with completion_date before start_date → inline error, no API call

**LOC estimate:** ~240 (form + zone select + page)

---

#### P5-004 — B-2: Contract detail page (read view + tab shell)

**Scope:** Detail page fetches the contract and renders an Overview tab (read-only) plus empty tab placeholders for Schedules and Items.

**Files touched:**
- `frontend/app/(app)/contracts/[id]/page.tsx` — new
- `frontend/app/(app)/contracts/page.tsx` — change row "View" button from `disabled` to `<Link href="/contracts/{id}">`

**Acceptance criteria:**
- `GET /api/contracts/{id}` fetched via TanStack Query on mount
- All ContractOut fields displayed in Overview tab (tender_number, contractor_name, base_month, railway_zone, status, and any additional fields returned by the GET endpoint)
- 404 or wrong-tenant → error state with "Contract not found" message, no crash
- Tab bar shows Overview (active), Schedules, Items; tab switching changes `?tab=` in URL without page reload
- Link "Manage extra-item decisions" is present but hidden (rendered when ExtraNS schedule exists — wired in P5-006)

**Test plan:**
- Unit: loading state renders spinner; error state renders error message; data renders contract fields
- Browser: navigate from contract list → detail page → correct fields appear; click Schedules tab → URL changes to `?tab=schedules`

**LOC estimate:** ~180

---

#### P5-005 — B-3: Contract inline edit (Overview tab)

**Scope:** Adds an Edit mode to the Overview tab; reuses `ContractForm`; calls `PUT /api/contracts/{id}`.

**Dependency:** P5-001 (PUT endpoint) + P5-004 (detail page)

**Files touched:**
- `frontend/app/(app)/contracts/[id]/page.tsx` — add edit mode toggle + PUT call
- `frontend/components/contracts/ContractForm.tsx` — accept `defaultValues` prop (already in component interface)

**Acceptance criteria:**
- "Edit" button switches Overview from read view to `ContractForm` pre-populated with current values
- On submit: `PUT /api/contracts/{id}` → success → invalidate `["contract", id]` query → return to read view
- On 422 conflict (agreement_number) → inline error on field
- "Cancel" discards edits, returns to read view with no API call

**Test plan:**
- Unit: edit mode renders form with correct defaultValues; cancel restores read view
- Browser: edit contractor_name → save → read view shows new value; edit with bad completion_date → inline error, no API call

**LOC estimate:** ~120

---

#### P5-006 — B-4: Schedules tab

**Scope:** Schedules tab lists existing schedules and provides a form to add new ones.

**Files touched:**
- `frontend/components/contracts/ScheduleForm.tsx` — new; fields: `name` (text), `schedule_type` (select: DSR / NS / ExtraNS), `bid_discount_pct` (decimal, default 0)
- `frontend/app/(app)/contracts/[id]/page.tsx` — add Schedules tab content; add ExtraNS detection logic for extra-items link visibility

**Acceptance criteria:**
- TanStack Query: `GET /api/contracts/{id}/schedules` on tab mount (not on page load — defer with `enabled: activeTab === "schedules"`)
- Schedule list shows name, type badge, bid_discount_pct
- Add Schedule form submits to `POST /api/contracts/{id}/schedules` → on success invalidates schedules query
- After any ExtraNS schedule is created, the "Manage extra-item decisions" link becomes visible in the page header
- Invalid `schedule_type` never reaches the API — select only allows DSR/NS/ExtraNS

**Test plan:**
- Unit: form renders; submit calls POST with correct body; ExtraNS detection flips link visibility
- Browser: add DSR schedule → appears in list; add ExtraNS schedule → extra-items link appears

**LOC estimate:** ~180

---

#### P5-007 — B-5: Items tab (AG Grid)

**Scope:** Items tab shows a schedule selector; when a schedule is selected, its items load in an AG Grid inline-editable table. "Save All" POSTs new/modified rows sequentially.

**Dependency:** P5-006 (schedules must exist)

**Files touched:**
- `frontend/components/contracts/ItemsGrid.tsx` — new; wraps AG Grid Community
- `frontend/app/(app)/contracts/[id]/page.tsx` — add Items tab content

**AG Grid column config:**

| Column | Type | Editable | Cell renderer/editor |
|---|---|---|---|
| `item_code` | text | yes | plain text |
| `description` | text | yes | plain text |
| `unit` | text | yes | plain text |
| `original_qty` | numeric | yes | numeric editor |
| `revised_qty` | numeric | yes | numeric editor |
| `base_rate` | numeric | yes | numeric editor |
| `agreement_rate` | numeric | yes | numeric editor |
| `is_cement_item` | boolean | yes | checkbox cell renderer |
| `steel_subtype` | enum | yes | select cell editor: `—` / `angles` / `plates` / `other_sections` / `tmt` |

**Acceptance criteria:**
- Schedule selector (dropdown) drives which schedule's items load
- `GET /api/schedules/{id}/items` fetched when schedule selected
- "+ Add row" appends a blank row to the grid (client-side only until Save All)
- "Save All" POSTs each new/modified row to `POST /api/schedules/{id}/items` sequentially; shows progress count ("Saving 3 of 12…"); on any failure, stops and shows which row failed
- Rows with `is_cement_item=true` and `steel_subtype` both set → client-side warning (a cement item cannot also be a steel item; the engine treats them as mutually exclusive buckets)
- `steel_subtype = null` is sent when the dropdown shows `—`

**Test plan:**
- Unit: AG Grid renders with correct columns; Save All iterates rows and calls POST per row; cement+steel mutual exclusion warning appears
- Browser: add 3 items → Save All → reload tab → items reappear; set `is_cement_item=true` + `steel_subtype=tmt` → warning indicator appears

**LOC estimate:** ~260

---

#### P5-008 — Extra-items page `/contracts/[id]/extra-items`

**Scope:** Dedicated page listing all ExtraNS items for a contract with their current eligibility decision; user can flip decisions inline.

**Dependency:** P5-006 (ExtraNS schedule + items must exist before this page is useful)

**Files touched:**
- `frontend/app/(app)/contracts/[id]/extra-items/page.tsx` — new
- `frontend/components/contracts/ExtraItemDecisionList.tsx` — new

**Acceptance criteria:**
- Fetches `GET /api/contracts/{id}/extra-item-decisions` + cross-references with items from `GET /api/contracts/{id}/schedules` + `GET /api/schedules/{id}/items` for ExtraNS schedules to build the full item list
- Each row shows: item_code, description, schedule name, eligible status (Yes / No / Undecided ⚠)
- Clicking Yes/No/Undecided calls `POST /api/contracts/{id}/extra-item-decisions` (upsert); updates optimistically; reverts on error
- If all items are decided (none undecided), shows green confirmation: "All extra items are decided — PVC run can proceed"
- If any undecided, shows warning banner: "N item(s) undecided — PVC run will be blocked until all are decided"
- Back link to `/contracts/[id]`

**Test plan:**
- Unit: undecided badge renders; toggle triggers POST with correct body; optimistic update + revert on error
- Browser: flip item from Undecided → Yes → row updates immediately; banner clears when last undecided item is decided

**LOC estimate:** ~200

---

### Risk Register

- **VALID_ZONES drift.** Frontend `lib/zones.ts` must match `backend/services/zone_mapping.py:VALID_ZONES` exactly. If the backend ENUM is extended (new zone added via migration), the frontend dropdown must be updated in the same PR. Prevention: cross-check at P5-002 task time; add a comment in `zones.ts` linking to the migration file.

- **`base_month` format mismatch.** `<input type="month">` returns `"YYYY-MM"` not `"YYYY-MM-01"`. The backend rejects anything where `day != 1`. Prevention: `ContractForm` must append `-01` in the zod transform or submit handler before calling `apiFetch`. Zod schema `.transform()` on that field.

- **PUT /api/contracts/{id} missing.** B-3 (edit) is blocked until P5-001 ships. If P5-001 is skipped, the Overview edit mode has no endpoint to call. Prevention: P5-001 is a hard dependency of P5-005 and must ship first.

- **AG Grid not installed.** B-5 is blocked until P5-002 ships. Prevention: P5-002 is the first frontend task; no other task depends on AG Grid until P5-007.

- **`is_cement_item` + `steel_subtype` mutual exclusion.** The engine treats cement and steel as separate subtraction buckets in W derivation. An item marked as both confuses the calculation. The backend does not currently block this combination. Prevention: client-side warning in ItemsGrid (P5-007 AC); flag as a future backend hardening item.

- **ExtraNS items blocking PVC run silently.** If a user creates ExtraNS items but never visits `/contracts/[id]/extra-items`, the engine will block at run time (Phase 7) with an undecided-items error. Prevention: the "Manage extra-item decisions" link on the detail page becomes visible as soon as an ExtraNS schedule exists (P5-006 AC), with an ⚠ indicator if any items are undecided. This makes the blocking condition visible before Phase 7.

- **`bid_amount > contract_value` not backend-validated.** `ContractCreate` Pydantic model does not check `bid_amount ≤ contract_value`. The client-side zod check (Q6 decision) catches this before the API call, but the server will accept violating values if the API is called directly. Prevention: noted; backend hardening is a future task outside Phase 5 scope.

- **`GET /api/contracts/{id}` returns a slim ContractOut.** The existing `GET /api/contracts/{id}` in `contracts.py` returns only: `id, tender_number, contractor_name, base_month, railway_zone, status`. Fields like `contract_value`, `bid_amount`, `loa_number`, etc. are not in the current response. The Overview tab will be missing these fields until the GET endpoint is expanded. Prevention: P5-004 must verify what the live endpoint actually returns and either display only available fields or flag the gap for a backend fix.

---

### Open Questions Still Requiring Product Input

| # | Question | Blocked task | What's needed |
|---|---|---|---|
| OQ-5 | `overall_rebate` storage format: migration says `NUMERIC(5,4)` (max 9.9999). Is this stored as a fraction (0.15 = 15%) or a percentage (15 = 15%)? The label on the form must be accurate. | P5-003 | Confirm before ContractForm ships |
| OQ-6 | `GET /api/contracts/{id}` currently returns only 6 fields (see contracts.py:97-116). Should all `ContractCreate` fields be returned for the Overview edit view, or is a separate `GET /api/contracts/{id}/detail` endpoint needed? | P5-004 | Decide before P5-004 starts; if yes, backend must be expanded (small change to contracts.py SELECT) |

---

## Track G — SH-P5: GET Bill Endpoints + Export Backend `[SH]`

> Parallel to Phase 5 UI. Branch: `shubham/phase-5-backend`. Touches `backend/api/` only.

### G-1: GET Bill List + Detail

**Goal:** Expose read endpoints for bills so Phase 6 UI can list and view them.

**Deliverables:**
- `GET /api/contracts/{contract_id}/bills` — list bills; returns `list[BillOut]`; tenant-checked via contract
- `GET /api/bills/{bill_id}` — single bill; `BillOut`; tenant-checked via bill→contract
- Add to `backend/api/bills.py`
- `BillOut`: `{ id, contract_id, bill_number, bill_date, measurement_date, gross_amount, net_amount, status, created_at }`

**Acceptance criteria:**
- Empty list (not 404) when no bills exist for a contract
- Wrong-tenant contract → `NotFoundProblem(404)` (not 403 — don't leak existence)
- Tests: valid list, zero-row list, wrong-tenant → 404

---

### G-2: GET Bill Lines + Recoveries

**Deliverables:**
- `GET /api/bills/{bill_id}/lines` → `list[BillLineOut]`; tenant-checked via line→bill→contract
- `GET /api/bills/{bill_id}/recoveries` → `list[RecoveryOut]`; tenant-checked
- Add to `backend/api/bills.py`

**Acceptance criteria:** Same isolation rules as G-1; wrong-tenant test per route.

**Dependency:** G-1

---

### G-3: Export Endpoints (Excel + PDF)

**Goal:** Allow downloading approved PVC run results.

**Context:** Check `engine/engine/` for existing export logic before writing routes. Wire it, don't rewrite.

**Deliverables:**
- `GET /api/pvc-runs/{run_id}/export/excel` → `application/vnd.openxmlformats...` download
- `GET /api/pvc-runs/{run_id}/export/pdf` → `application/pdf` download
- Both: tenant-check via run→contract; status must be `Approved` or return `422` with `detail.code = "run_not_approved"`
- `Content-Disposition: attachment; filename="pvc_run_{id}.xlsx"` (and `.pdf`)

**Acceptance criteria:** Unapproved run → 422; wrong-tenant → 404; tests for both cases.

**Dependency:** G-1 + G-2

---

## Parallel Track Summary

```
Right now (parallel):
  saqlain/phase-5         P5-001 → P5-002 → P5-003 → P5-004 → P5-005 → P5-006 → P5-007 → P5-008
  shubham/phase-5-backend G-1 → G-2 → G-3

P5 task order (strict):
  P5-001 and P5-002 can run in parallel (different codebases)
  P5-003 depends on P5-002
  P5-004 depends on P5-003 (redirect target must exist)
  P5-005 depends on P5-001 + P5-004
  P5-006 depends on P5-004
  P5-007 depends on P5-002 + P5-006
  P5-008 depends on P5-006

Phase 6 unblocked when: B-2 stable + G-1+G-2 merged
Phase 7 unblocked when: Phase 6 complete
```

---

## Next Review Checkpoint

`P5-REVIEW` — Codex-S adversarial pass. **Implementation is on `saqlain/phase-5` (uncommitted at the time of this note); the next concrete actions are listed in "Next Steps" at the top of this file.**
