# RailPVC

Billing OS for Indian Railway contractors automating PVC calculations under GCC Clause 46A. Normalizes the document chain (agreement → MB → bill → recoveries → indices) into a deterministic, auditable PVC output. Displaces Excel workbooks and IRPVC SaaS.

## Key Files

| File | Purpose |
|---|---|
| `PRODUCT.md` | MVP scope, personas, 3 non-negotiables |
| `ARCHITECTURE.md` | Stack, data model, engine interface, API surface |
| `TASKS.md` | Build plan — CC owns `[CC]` tasks, Codex acts on `[CODEX]`/`[CODEX-REVIEW]` |
| `CODEX.md` | Codex role, review format, hard boundaries |
| `engine/` | Pure Python PVC calc package — no DB, no HTTP, deterministic |
| `seeds/` | Historical RBI/JPC index data |

## Stack

Next.js 14 (App Router) + TypeScript · FastAPI (Python) · Supabase (Postgres + Auth + Storage) · AG Grid tables · TanStack Query · openpyxl (Excel export)

## Critical Domain Rules

**W derivation (never default):**
`W = OnAccountBill − Cement − SteelAngles − SteelPlates − SteelOther − TechWithheld − ExcludedExtraItems`
Any missing eligibility decision must block the run — never assume included or excluded.

**Quarter mapping:** Bill measurement_date determines the quarter. Confirmed domain interpretation — but must be stored as immutable field on every PVC run, not re-derived.

**Immutability:** Approved PVC runs cannot be modified. Revisions create superseding runs. `revision_snapshots` is append-only.

## Architecture Decisions

- Single-user per org for MVP; multi-user RBAC (3 roles) is immediate post-MVP priority
- `engine/` is a pure function package — imported by FastAPI, never calls DB or HTTP
- Supabase Postgres with row-level tenancy (`tenant_id` on all tables)
- Excel-parity export from day one (openpyxl matching BCT-24-25-252 workbook layout)
- Manual index entry + seeded historical data; no PDF parsing in v1

## Known Unknowns (Require Saqlain Input)

- KU-001: Quarter mapping confirmed for WR zone — verify other zones before templating
- KU-002: Schedule C extra NS in BCT-24-25-252 bill 2 — intentional or error?
- KU-003: Negative PVC treatment — recover from next bill or immediate offset?

## Vault

Search Obsidian for `RailPVC` or `PVC calculation` for any updated session notes.
