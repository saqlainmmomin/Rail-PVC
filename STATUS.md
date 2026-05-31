# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Phase 5 + SH-P5-1..4 + P5-FUP + IDX-2..3 all on `main` (2026-05-30).** PRs #7/#8/#9 merged. Route count 38.
- **Active workstream (Saqlain):** Phase 6 — Bill entry UI. **C-1 + C-2 implemented on `saqlain/phase-6` (2026-05-31)** — awaiting smoke + P6-REVIEW. C-3 (bill/recovery edit + computed net) pending.
- **Active workstream (Shubham):** SH-P5-5..6 — Excel/PDF export endpoints (pending).
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- **None blocking Phase 6.** IDX-2..3 (index write endpoints) are on `main`; seed Jan–May 2026 index months before running PVC on 2026 bills (Phase 7 concern).
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- **None open.** `P5-REVIEW` closed and merged 2026-05-20; all deferred L-findings closed by 2026-05-30 (PR #9). SH-P5-REVIEW completed (PR #7 merged clean).
- Suite state: **106/106 backend** (103 prior + 3 new C-1 tests), **99/99 engine**, **16/16 frontend vitest**, `next build` clean, `npm run lint` clean. Route count 38 (C-1 hardened the existing POST bills route — no new route).

## Branch State

- `main` — fully up to date with origin. PRs #7, #8, #9 merged 2026-05-30.
- `saqlain/phase-6` — **active.** Phase 6 C-1 + C-2 (bill entry UI + POST-bill 409 hardening). Awaiting smoke + P6-REVIEW.
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

1. [CC-S] Smoke C-1/C-2 in a browser, then open `P6-REVIEW`; on pass, merge `saqlain/phase-6` and proceed to C-3 (bill/recovery edit + computed net_amount).
2. [CC-SH] SH-P5-5..6 — Excel/PDF export endpoints (request `SH-P5-REVIEW` before merge).

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
