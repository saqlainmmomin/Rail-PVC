# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Phase 5 + SH-P5-1..4 + P5-FUP all merged to `main` (2026-05-30).** PRs #7 (GET bills endpoints), #8 (IDX gap docs), #9 (P5-FUP-L2 delete wording) merged. Route count now 35. All P5-REVIEW deferred findings closed.
- **Active workstream (Saqlain):** Phase 6 — Bill entry UI (C-1…C-3). **Blocked on IDX-2..3** (monthly entry endpoints) — seed data ends Dec-2025; bills dated Jan 2026+ have no index data. IDX-2..3 should be implemented before or alongside Phase 6.
- **Active workstream (Shubham):** SH-P5-5..6 — Excel/PDF export endpoints (pending).
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- **IDX-2..3** (monthly index entry endpoints): seed data ends Dec-2025; any PVC run on a Jan 2026+ bill will have no RBI/JPC data. Must be implemented before Phase 6 bill entry is meaningful.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **None open.** `P5-REVIEW` closed and merged 2026-05-20; all deferred L-findings closed by 2026-05-30 (PR #9). SH-P5-REVIEW completed (PR #7 merged clean).
- Suite state on `main`: backend tests include 12 new SH-P5 tests (route count 35); **99/99 engine tests**, **16/16 frontend vitest**, `next build` clean, `npm run lint` clean.

## Branch State

- `main` — fully up to date with origin. PRs #7, #8, #9 merged 2026-05-30.
- `saqlain/phase-5` — deletable (merged).
- `saqlain/test-p3p4` — deletable (merged).
- `shubham/phase-5-backend` — deletable (merged via PR #7).
- `shubham/idx-flag` — deletable (merged via PR #8).
- `shubham/p5-fup-l2` — deletable (merged via PR #9).

## What To Read

### If you are implementing fixes

1. [PRODUCT.md](PRODUCT.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
4. [TASKS.md](TASKS.md)
5. [REVIEW.md](REVIEW.md)
6. [SESSION_LOG.md](SESSION_LOG.md)

### If you are doing adversarial review

1. [PRODUCT.md](PRODUCT.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [TASKS.md](TASKS.md)
4. [REVIEW.md](REVIEW.md)
5. [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)

## Current Priorities

1. [CC-S] Implement IDX-2..3 (`POST /api/indices/{series}/months` + GET list/detail) — blocks Phase 6 meaningfully working past Dec-2025 data.
2. [CC-S] Begin Phase 6 — Bill entry UI (C-1…C-3) once IDX-2..3 are in.
3. [CC-SH] SH-P5-5..6 — Excel/PDF export endpoints (request `SH-P5-REVIEW` before merge).

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
