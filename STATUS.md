# STATUS.md — RailPVC Current State

Start here.

This file is the shortest path to current branch state, blockers, and next actions.

## Current Phase

- **Active workstream (Saqlain):** Phase 5 — contract setup UI (P5-001…P5-008) **implementation complete** on `saqlain/phase-5` (2026-05-19); awaiting `P5-REVIEW` (Codex-S) before merge to `main`.
- **Active workstream (Shubham):** SH-P5 — GET bill endpoints + export backend (parallel to Phase 5 UI).
- TEST-P3P4 complete: TEST-01…07 all merged to `main` (fast-forwarded from `saqlain/test-p3p4`, 2026-05-19).
- Phase 3 backfill + Phase 4 complete: all on `main`.

## Current Blockers

- None. No open CRITICAL/HIGH findings.
- Out-of-band: credential hygiene — DB password and JWT secret are in `backend/.env` (git-ignored). Keep `.env` out of version control.

## Active Review Cycle

- `P5-REVIEW` pending: Codex-S adversarial pass on `saqlain/phase-5` (P5-001…P5-008). Branch is local + uncommitted at the time of writing; commit + push before kicking off review.
- Suite state on branch: **61/61 backend tests passing** (55 prior + 5 new for PUT + 1 route count bump), **99/99 engine tests** unchanged, `next build` clean (3 new routes: `/contracts/new`, `/contracts/[id]`, `/contracts/[id]/extra-items`).

## Branch State

- `main` — last commit `22ba97c` (docs sync 2026-05-19).
- `saqlain/phase-5` — **Phase 5 implementation complete, uncommitted**. Contains: backend PUT `/api/contracts/{id}` + expanded GET; frontend zod schema + zones; ContractForm + ZoneSelect + ScheduleForm + ItemsGrid + ExtraItemDecisionList; `/contracts/new`, `/contracts/[id]`, `/contracts/[id]/extra-items` pages.
- `shubham/phase-5-backend` — Shubham's parallel track (GET bills + exports), in progress.
- Deletable: `saqlain/test-p3p4` (already merged).

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

1. [CC-S] Commit + push `saqlain/phase-5`, open PR, run live browser smoke (the 4 flows in WORKPLAN "Manual Smoke Plan"), then kick off `P5-REVIEW`.
2. [CC-S] Resolve any findings from `P5-REVIEW`; merge `saqlain/phase-5` once clean.
3. [CC-SH] Continue SH-P5 backend (G-1 → G-2 → G-3); request `SH-P5-REVIEW` before merge.
4. Credential hygiene — DB password + JWT secret are in `backend/.env` only (git-ignored). Document in onboarding.

## File Classification

- Startup/status: [STATUS.md](STATUS.md)
- Stable truth: [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Active state: [TASKS.md](TASKS.md), [REVIEW.md](REVIEW.md), [SESSION_LOG.md](SESSION_LOG.md)
- Instructions: [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md)
- Archive pointers: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md), [archive/SESSION_LOG_ARCHIVE.md](archive/SESSION_LOG_ARCHIVE.md)
