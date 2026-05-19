# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

No active cycle.

Last closed: TEST-P3P4 — M-1 (missing recovery_type test) and M-2 (untyped 500 on storage error) both closed via TEST-01/TEST-02. Full record in git history at commits `48d4769` / `0d8539a`. PR #4 (Phase 3 backfill) reviewed by CC-S; no CRITICAL/HIGH.

## Next Expected Checkpoint

`P5-REVIEW` — Codex-S adversarial pass after Phase 5 UI (B-1…B-5, branch `saqlain/phase-5`) lands. Until then this file stays empty.

`SH-P5-REVIEW` — CC-S review of Shubham's GET bill endpoints + export routes (`shubham/phase-5-backend`) before merge.

## Resolution Protocol

When a new cycle opens:

1. Record findings here with severity (CRITICAL / HIGH / MEDIUM / LOW), file path, issue, risk, suggested fix.
2. Fix owner adds a `CC Response` subsection under each finding stating what changed and which tests pin it.
3. Only close a finding when the code and tests both support the fix.
4. When the cycle merges, replace this file's content with a one-paragraph closure pointer (preserve detail via git history + archive pointer).
