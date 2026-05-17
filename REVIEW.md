# REVIEW.md — Active Review Cycle

Use this file for the current live review state only.

## Canonical Links

- Current project state: [STATUS.md](STATUS.md)
- Coding/review rules: [ENGINEERING_GUIDELINES.md](ENGINEERING_GUIDELINES.md)
- Current task board: [TASKS.md](TASKS.md)
- Historical review pointer: [archive/REVIEW_ARCHIVE.md](archive/REVIEW_ARCHIVE.md)

## Active Cycle

No active cycle.

The previous cycle (Phase 3 remediation, `P3-01…P3-09`) closed when PR #3 merged to `main` on 2026-05-17. All findings carried `CC Response` resolution notes and pinning tests; the full record is preserved in git history at commit `739bc4f` and the merge commit `07838f4`.

## Next Expected Checkpoint

`P3-BF-REVIEW` — Codex-S adversarial review of the Phase 3 backfill PR (`[CC-SH]`: schedules, contract_items, recoveries, documents endpoints) once CC-SH opens it. Until then this file stays empty.

## Resolution Protocol

When a new cycle opens:

1. Record findings here with severity (CRITICAL / HIGH / MEDIUM / LOW), file path, issue, risk, suggested fix.
2. Fix owner adds a `CC Response` subsection under each finding stating what changed and which tests pin it.
3. Only close a finding when the code and tests both support the fix.
4. When the cycle merges, replace this file's content with a one-paragraph closure pointer (preserve detail via git history + archive pointer).
