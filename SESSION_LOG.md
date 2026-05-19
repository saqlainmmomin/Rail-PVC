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
- **Phase 5 UI: implementation complete on `saqlain/phase-5` (uncommitted) — 61/61 backend, `next build` clean. Awaiting commit + push + P5-REVIEW.**
- Active (parallel): GET bill endpoints + export backend (Shubham, `shubham/phase-5-backend`).
- Test suite on branch: 61/61 backend, 99/99 engine. No open CRITICAL/HIGH findings.
- Local backend: `cd backend && uv run uvicorn main:app --reload --port 8000`
- Local frontend: `cd frontend && npm start` (port 3000)
- DB: Supabase at `ivselmhloegjmqrjekcy.supabase.co`, migrations at head (012).
- Tenant provisioned for `saqlainmmomin@gmail.com` — tenant_id `bd589426-93ba-4847-b5f3-1f69b020b4c0`.

## Recent Sessions

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

1. [CC-S] Commit P5-001…P5-008 on `saqlain/phase-5`, push to origin, open PR.
2. [CC-S] Run live browser smoke (create → detail → edit → schedule → items → extra-items) against localhost stack before review.
3. [CODEX-S] `P5-REVIEW` adversarial pass on `saqlain/phase-5`.
4. [CC-S] Resolve P5-REVIEW findings; merge `saqlain/phase-5` once clean.
5. [CC-SH] Continue SH-P5 (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.
