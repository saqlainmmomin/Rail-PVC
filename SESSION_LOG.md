# SESSION_LOG.md — Current Operational Log

Keep this file small.

Use it for current milestone decisions and recent sessions only.

## Canonical Links

- Current state: [STATUS.md](STATUS.md)
- Active task board: [TASKS.md](TASKS.md)
- Active review cycle: [REVIEW.md](REVIEW.md)
- Historical archive pointer: [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)

## Current Project State

- Phases 0–4 + Phase 3 backfill + TEST-P3P4: all complete on `main` as of 2026-05-19.
- **Phase 5 UI: P5-001…P5-008 + P5-F1…F5 implementation complete on `saqlain/phase-5` (PR #6). Awaiting P5-REVIEW.**
- Active (parallel): GET bill endpoints + export backend (Shubham, `shubham/phase-5-backend`).
- Test suite on branch: 67/67 backend, 99/99 engine. No open CRITICAL/HIGH findings.
- Local backend: `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000`
- Local frontend: `cd frontend && npm run build && npm start` (port 3000) — always rebuild after code changes
- DB: Supabase at `ivselmhloegjmqrjekcy.supabase.co`, migrations at head (012).
- Tenant provisioned for `saqlainmmomin@gmail.com` — tenant_id `bd589426-93ba-4847-b5f3-1f69b020b4c0`.

## Recent Sessions

### Session 18 — 2026-05-20 (P5-F1…F5 implementation landed)

- Implemented all five UX polish fixes in one session on `saqlain/phase-5`.
- **F1** — `TooltipHeader` custom AG Grid `headerComponent` with ⓘ icon + native `title` attribute; wired on `original_qty`, `revised_qty`, `base_rate`, `agreement_rate`, `is_cement_item`, `steel_subtype`. No external tooltip library.
- **F2** — "Import rows" toolbar button opens `ImportRowsModal` (absolutely-positioned overlay, no modal lib). `parseTsvImport` splits on `\n` / `\t`, normalises `is_cement_item` (TRUE/true/1/yes → true), and accepts blank `steel_subtype` as null. Preview table + parse-error list before commit; rows append as `_rowState: "new"`.
- **F3 backend** — `PUT` + `DELETE /api/schedules/{schedule_id}/items/{item_id}` in `backend/api/contract_items.py`. New helper `_assert_item_under_schedule_for_tenant` runs the two-step gate: first `assert_schedule_belongs_to_tenant` (tenant ownership of the schedule), then verify the item's `schedule_id` matches the URL. Either failure → 404 NotFoundProblem. `ContractItemUpdate` uses the established `model_fields_set` partial-update pattern; `steel_subtype` keeps the explicit ENUM cast (`CAST(:steel_subtype AS steel_subtype)`). 6 new tests in `test_p5_f3_items_crud.py` (PUT valid / wrong-schedule / wrong-tenant; DELETE valid / wrong-schedule / wrong-tenant). Route count assertion in `test_p3_08_clean_import.py` bumped 29 → 31.
- **F3 frontend** — `_rowState: "new" | "dirty" | "persisted"` per row. Loaded items default to `persisted`; cell edits demote `persisted → dirty` (never demote `new`). Save All routes `new → POST`, `dirty → PUT`, `persisted → skip`. Added a multi-select checkbox column (`checkboxSelection` on `item_code`, `headerCheckboxSelection`, `rowSelection="multiple"`, `suppressRowClickSelection`). "Delete selected (N)" appears when ≥1 row is selected; new rows are removed in-memory without API calls or confirms; persisted/dirty rows trigger `window.confirm(...)` then sequential `DELETE` calls, with the query invalidated only when persisted rows were touched.
- **F4** — One-line banner copy rewrite ("One or more items are marked as both a cement item and a steel item. Each item can only belong to one — please correct before saving.").
- **F5** — `ExtraItemDecisionList` rewritten around a local `pending: Record<itemId, Verdict>` map. Toggling a row updates `pending` only; clicking back to the server value drops the entry (so it stops showing as unsaved). Effective verdict for a row = `pending[id] ?? serverVerdict`; the undecided-count banner reads this merged view. "Save changes (N)" is enabled only when `pending` is non-empty, runs `Promise.all` of POSTs with `silent: true` (we render our own toast), preserves `pending` on failure for retry, and invalidates the decisions query on success. Per-row amber dot indicates a pending change.
- **Verification** — `cd backend && uv run python -m pytest -x -q` → 67 passed (61 prior + 6 new). `cd frontend && npm run build` → clean, 0 TS errors.
- **Lessons captured (used during implementation):**
  - aiosqlite doesn't bind `Decimal` to parameter values — tests with NUMERIC columns must use plain ints/floats. The Postgres `::text` casts in SELECT-back paths still fail under aiosqlite; the established pattern is to catch `OperationalError` and verify the UPDATE/DELETE landed via a plain follow-up `SELECT` (see `test_p5_001_contracts_put.py`).
  - The two-step gate (`assert_schedule_belongs_to_tenant` then per-item membership check) preserves the "wrong-tenant collapses to the same 404 as wrong-schedule" rule — no information leak.
  - `apiFetch` supports `{ silent: true }` to suppress the default Sonner toast; useful when the caller renders its own success/error UI (F5 batch save).

### Session 17 — 2026-05-20 (Smoke test complete; BUG-1 fixed; P5-F1…F5 planned)

- Restarted backend + frontend. BUG-1 diagnosed from browser devtools Network tab: actual error was **500 Internal Server Error**, not a network failure. The "Network error" toast was a misdiagnosis from the previous session.
- Root cause of 500: `INSERT INTO schedules VALUES (:stype::schedule_type …)` — SQLAlchemy's asyncpg dialect left `:stype` unsubstituted because `::schedule_type` immediately follows and breaks named-param parsing. Fix: `CAST(:stype AS schedule_type)`. One-line change in `backend/api/schedules.py`. CORS and auth were never the issue.
- Smoke test completed: all 7 flows green (Create, Edit, Validation, Schedules, Items, Mutual-exclusion warning, Extra-items).
- Saqlain ran live testing and raised 5 UX observations:
  1. Column tooltips needed on confusing Items grid fields (original_qty, revised_qty, base_rate, agreement_rate, is_cement_item, steel_subtype)
  2. No Excel paste support — multi-row copy from Excel collapses into a single cell. Decision: Option B (paste-area import dialog with TSV parsing + row preview), with Option C (file import) as a post-MVP addition.
  3. Items Save All always creates new rows — no update or delete. Decision: Option B (checkbox-select + "Delete selected" with confirmation; Save All distinguishes new/dirty/persisted rows; backend needs PUT + DELETE endpoints for items).
  4. Mutual-exclusion warning uses engine jargon ("engine treats these as mutually exclusive buckets"). Fix: user-facing copy.
  5. Extra-items auto-save feels unsafe. Decision: Option B (staged local changes + explicit "Save changes" button; batch POST on save).
- All 5 issues captured as P5-F1…F5 in TASKS.md. Implementation prompt written in WORKPLAN.md.
- P5-REVIEW is now gated on P5-F1…F5 landing.

### Session 16 — 2026-05-20 (Partial smoke; BUG-1 misdiagnosed as network error)

- Rebuilt frontend after finding stale bundle. Flows 1–3 (Create, Edit, Validation) passed.
- Flow 4 (Schedules) blocked — "Network error" toast on schedule POST. Investigated CORS + auth, found nothing. Root cause not identified (diagnosed in Session 17).
- `base_month` edit-mode fix committed to working tree (`toFormDefaults` slices to `YYYY-MM`).
- Servers shut down at end of session.

### Session 15 — 2026-05-19 (Phase 5 UI implementation — P5-001…P5-008 landed on `saqlain/phase-5`)

- Implemented all eight Phase 5 tasks end-to-end in a single session: backend PUT + expanded GET (P5-001), frontend deps + zod/zone constants (P5-002), `/contracts/new` form (P5-003), `/contracts/[id]` detail with tab shell (P5-004), Overview inline edit (P5-005), Schedules tab + `ScheduleForm` (P5-006), Items tab + AG Grid `ItemsGrid` (P5-007), extra-items decision page (P5-008).
- Backend: 6 new tests in `test_p5_001_contracts_put.py` (wrong-tenant 404, unknown 404, invalid zone 422, base_month day≠1 422, `model_fields_set` semantics, valid partial update); route count assertion in `test_p3_08` bumped 28 → 29.
- Frontend: `base_month` field uses `setValueAs` to auto-append `-01` before submit; `overall_rebate` UI says "as decimal, 0.15 = 15%" per OQ-5; items grid renders a soft warning when a row is marked both `is_cement_item=true` AND has `steel_subtype` set (engine buckets are mutually exclusive); decision toggles use TanStack `onMutate` for optimistic update + rollback on error.
- AG Grid theming via `themeQuartz.withParams({…})` + `AllCommunityModule` registration (v35 API; the docs are right, training data was wrong).
- Verified: 61/61 backend pass; `next build` reports 11 routes including 3 new (`/contracts/new`, `/contracts/[id]`, `/contracts/[id]/extra-items`).
- Branch `saqlain/phase-5` is **uncommitted** as of this entry — needs commit + push + PR + live smoke before P5-REVIEW.

### Session 14 — 2026-05-19 (TEST-P3P4 closed; Phase 5 + SH-P5 parallel tracks opened)

- TEST-P3P4 (TEST-01…07) confirmed complete and merged to `main` (fast-forwarded from `saqlain/test-p3p4`). M-1/M-2 closed.
- OQ-2 decided: B-5 items grid uses **explicit "Save All" button** — validates whole sheet client-side, then POSTs rows sequentially with progress indicator. Rationale: BOQ entry is one-time bulk import; per-row save has no atomicity and creates silent partial imports on failure.
- Shubham's parallel track (SH-P5) defined: GET bill endpoints (G-1/G-2) + export routes (G-3) on `shubham/phase-5-backend`.
- WORKPLAN.md + backend/Untitled pushed to `main` (commit `b5c0d13`).
- All context docs audited and brought to current state.

### Sessions 10–13 — 2026-05-17 (archived)

Detailed notes moved to git history and [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md). Summary:

- **Session 10:** Phase 3 remediation (P3-01…P3-09) on `saqlain/phase-3-remediation`. Key decisions: src-layout engine packaging, API-layer tenant isolation (no RLS), pure-function domain logic, DB-enforced idempotency, typed error contract.
- **Session 11:** PR #3 merged; Codex-S post-merge regression clean (99/99 engine + 31/31 backend).
- **Session 12:** Phase 4 P4-001/002/007 — Supabase auth wiring, login/signup pages, typed `ApiProblem` client.
- **Session 13:** Phase 4 P4-004/006 complete — contract list dashboard + typed API schema generated. Infra: switched to JWKS/ES256, rotated DB password, applied DDL for migrations 010–012, provisioned tenant.

## Current Decisions

- Active docs should be read in this order: STATUS → PRODUCT → ARCHITECTURE → TASKS → REVIEW
- Historical detail should not live in the active context set when a summary/link is sufficient
- `CLAUDE.md` and `CODEX.md` act as startup instructions, not duplicate project context
- B-5 items grid: **Save All button** (not per-row save). Decided 2026-05-19. See Session 14.

## Next Actions

1. [CC-S] Push `saqlain/phase-5` to origin; kick off `P5-REVIEW` (Codex-S adversarial pass).
2. [CC-S] Resolve P5-REVIEW findings; merge `saqlain/phase-5` once clean.
3. [CC-SH] Continue SH-P5 (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.
