# Track B — Phase 4 Design Decisions (retrospective)

**Date:** 2026-05-16 (Session 5)
**Branch:** `saqlain/phase-4`
**Status:** captured retrospectively — the original brief asked for an `AskUserQuestion` log up front; the working session locked decisions inline and the log wasn't captured live. Reconstructed below from files on disk so the rationale survives the session.

---

## 1. Typeface

**Decision:** Geist Sans + Geist Mono via `next/font/google`, with `font-variant-numeric: tabular-nums` enabled globally on `body` and Geist feature flag `cv11` on (single-storey `a` for small-size clarity).

**Where:** `frontend/app/layout.tsx`, `frontend/app/globals.css`.

**Why:**
- Geist is editorial-feeling without being precious — fits "polished, not dated" without slipping into novelty.
- Tabular numerals on by default means every column with a Decimal lines up even before we reach mono territory. PVC totals run to crores; numbers misaligning by 1px would erode the trustworthy-first feel.
- `cv11` keeps the `a` legible at 10–11px (used in badge labels, kbd hints, table headers).

**Mono usage discipline:**
- `.num-mono` helper class for any Decimal cell or formula expression.
- `.num-sans` for inline numbers that need tabular alignment but should stay sans.
- Sonner toast descriptions render in mono (set globally in `globals.css`) so notifications like "Approved run #14 · ₹76,959.55" land with the same number treatment as the grid.

## 2. Palette

**Decision:** Slate scale for neutrals + amber-600 as the lone accent. Hardcoded CSS variables in `globals.css` under `@theme inline`.

**Tokens:**

| Role | Value |
|---|---|
| `--color-surface` | `#ffffff` |
| `--color-surface-muted` | `#f8fafc` (slate-50, body bg) |
| `--color-surface-rail` | `#0f172a` (slate-900, sidebar) |
| `--color-border` | `#e2e8f0` (slate-200) |
| `--color-fg` | `#0f172a` (slate-900) |
| `--color-fg-muted` | `#475569` (slate-600) |
| `--color-accent` | `#d97706` (amber-600) |
| `--color-success` / `--color-danger` | `#16a34a` / `#dc2626` |

**Why:**
- Slate is sober without being grey-dead. Engineers and finance staff using this product won't trust pastels.
- Amber-600 (not amber-500) as the lone accent — used for the brand square, the sidebar active-state rail, and the focus ring. Single-accent discipline keeps the surface from competing with the data.
- Status colours (success/danger) are reserved for PVC approval state and validation errors, never decoration.

## 3. Sidebar shape

**Decision (Option C):** Responsive auto-collapse, with manual override. Default = auto (tracks viewport via `matchMedia(max-width: 1279px)`). `⌘\` flips into manual mode and pins the user's choice.

**Where:** `frontend/components/shell/ShellState.tsx`, `frontend/components/shell/Sidebar.tsx`.

**Widths:** 220 px expanded, 52 px collapsed (icon-only).

**Why:**
- The product is going to be used on 13" laptops in site offices and 27" monitors in HQ. Auto-collapse means the same build feels right in both contexts without setting up.
- Manual override is required: power users will pin the collapse state after a few sessions and resent the viewport rule overriding them.
- 220 px gives enough room for the three nav labels + org chip without crowding; 52 px is wide enough that the lucide `1.75`-stroke icons remain legible.

**Visual treatment:**
- Slate-900 surface — the sidebar reads as a separate "rail" not a sibling panel.
- Active state: slate-800 background + 2px amber-500 rail anchored to the left edge of the item (not a full underline; not a chevron).
- Brand: amber-600 `R` square + RailPVC wordmark, 14 px row.
- Footer: user initials + org name + collapse toggle showing `⌘\` hint.

## 4. Command palette + keyboard shortcuts

**Decision:** Yes, in Phase 4. Use `cmdk` (Radix-stack, well-behaved with React Server Components). `⌘K` opens it; `⌘\` toggles sidebar; `g`-prefix Vim-style jumps (`g c` → /contracts, `g i` → /indices, `g d` → /documents).

**Where:** `frontend/components/shell/CommandPalette.tsx`, `frontend/components/shell/ShellState.tsx`.

**Why introduce it now (not defer):**
- Keyboard navigation is part of the "polished, not dated" bar — a 2026 product without `⌘K` reads as a 2018 one.
- Building palette infrastructure into the shell now means Phase 5 (Recent runs) and Phase 6 (jump to a specific bill cell) can append groups without restructuring.
- Power-user keyboard nav reinforces the Excel-replacement positioning: muscle memory for the keyboard is what those users have, and we honour it.

**Phase 4 contents:**
- "Navigate" group — three nav items with `g <key>` hints + ⏎ to enter.
- "Recent runs" group — placeholder stub. Phase 5 wires this.

**Suppression rule:** `g`-prefix listener disabled when typing in `<input>` / `<textarea>` / `contenteditable`. Modifier-key presses (`Cmd/Ctrl/Alt`) also bypass it so existing shortcuts don't conflict.

## 5. Toast library

**Decision:** Sonner. Mounted in `app/layout.tsx`, position `bottom-right`, `closeButton` on, `richColors` off.

**Why over alternatives:**
- Custom Radix-based stack would mean writing portal + stacking + dismissal logic that Sonner already nails. Time not well spent before any real feature ships.
- `react-hot-toast` is fine but Sonner's animation defaults and stacking feel calmer — better fit for a trust-first product than springy bouncing.
- `richColors` disabled because amber-on-amber success toasts undermine the single-accent discipline. We override the Sonner CSS in `globals.css` so toasts render on `--color-surface` with our border + shadow tokens.

**Description treatment:** mono + tabular-nums + 12px, so the `description` slot is where the numeric proof goes: "Approved run #14 · ₹76,959.55 · Q2-FY2025-26".

## 6. Page density / numeric typography

**Decision:**
- Body text 13 px, line-height 1.5 — denser than typical web defaults, closer to native-app or Excel feel without going so dense the eye strains.
- Page heading 22 px / semibold / `tracking-tight`.
- Table header labels: 10.5 px uppercase / tracking-wider / slate-500 — small typographic muscle that says "data, not marketing".
- Every rupee column: mono + tabular-nums + right-aligned.
- Formula expressions: mono, slate-700 numerals, slate-400 operators — operators recede so the variable names read first.

**`formatINR`:** Intl with `en-IN` locale so amounts group as `1,23,45,678.90` (lakh/crore), not Western `1,234,567.89`. The product is for Indian contractors — using the wrong grouping would be a serious tell.

## 7. AG Grid placeholder

**Decision:** Deferred to Phase 5. **Confirmed by user via `AskUserQuestion` in Session 5.**

**Rationale:**
- The contracts page already carries a hand-rolled "Visual smoke-test" panel that demonstrates the design language working with tabular data (header row, tabular-num right-aligned amounts, formula bar at the bottom). This is the lightweight placeholder the brief asked for.
- `ag-grid-community` + `ag-grid-react` is ~250 KB; pulling it in for a placeholder doesn't earn its weight before P5/P6 know the column shape they actually need.
- De-risking AG Grid + Tailwind v4 + Geist will happen in P5 when the first real `ContractItem` grid is built — at which point we'll write the AG Grid theme tokens against the same CSS variables as the rest of the app.

**Trade-off accepted:** no early visual proof that AG Grid will mesh cleanly with the palette. If theming turns out to fight us in P5, that's a Phase 5 cost — not a Phase 4 risk.

## 8. Error handling

**Decision (two tiers):**
- **Component / render errors** → caught by `app/error.tsx` (route-level) and `app/global-error.tsx` (last-resort root). Branded fallback card; in dev, the error message is shown verbatim; in prod, only the friendly copy.
- **API errors** → surfaced as Sonner toasts from `lib/api/client.ts`. `4xx`/`5xx` produce `${status} · ${friendly(status)}` with the server's `detail` in the description. Network errors → `Network error` toast + `ApiError(status=0)`.
- **TanStack Query retry policy:** auth/validation/not-found/conflict (`401/403/404/409/422`) → never retry; other failures retry up to 2.
- **Silent option:** `apiFetch(path, { silent: true })` suppresses the toast so callers can render inline UI for expected failures (e.g., empty-state on 404).

**Where:** `frontend/app/error.tsx`, `frontend/app/global-error.tsx`, `frontend/app/not-found.tsx`, `frontend/lib/api/client.ts`, `frontend/lib/providers.tsx`.

## 9. TanStack Query setup

**Decision:** Client-component `Providers` wrapper. One `QueryClient` per mount (via `useState(buildQueryClient)`) so StrictMode double-render doesn't churn the cache. `ReactQueryDevtools` mounted only when `NODE_ENV === "development"`, button anchored bottom-left so it doesn't fight the toasts in bottom-right.

**Defaults:**
- `staleTime: 30s` — index data and contract metadata don't change every keystroke.
- `gcTime: 5min`
- `refetchOnWindowFocus: false` — felt too jumpy for a deliberative billing UI.
- `retry`: 2 unless the error is `ApiError` with status in `[401, 403, 404, 409, 422]`.

## 10. OpenAPI codegen

**Decision:** `openapi-typescript` (not `openapi-fetch`, not Orval). Schema target: `frontend/lib/api/schema.ts`.

**Why:** schema-only, no client runtime. Lets us keep the `apiFetch` primitive we control and layer typed paths on top later. Avoids two layers of network abstraction.

**Wire-up:** `npm run gen:api` in `frontend/package.json` reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`). Runs the moment Shubham's FastAPI exposes `/openapi.json`.

---

## What this Phase 4 deliberately does NOT decide

- **AG Grid theme tokens** — punted to P5 with the placeholder.
- **Auth UI** (P4-001 / P4-002) — blocked on P3-001 merge and CC-SH ownership respectively.
- **Per-route breadcrumb depth** — the header has a section-only crumb; deeper crumbs land per-route when those routes get content.
- **Header context-pill content** — the slot (`#header-context-slot`) exists so per-route children can portal contract/bill/quarter context in. Phase 5+ fills it.
- **Phase 6 formula bar binding** — `contracts/page.tsx` shows the visual treatment so the pattern is locked in for when actual bill-line editing arrives.
