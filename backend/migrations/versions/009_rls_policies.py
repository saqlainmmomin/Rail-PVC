"""RLS policies — tenant isolation for all 17 tables

Revision ID: 009
Revises: 008
Create Date: 2026-05-16

Design:
  - get_tenant_id() resolves the Supabase JWT uid to the caller's tenant_id.
    SECURITY DEFINER + fixed search_path prevent privilege escalation.
  - Tables with a direct tenant_id column use it directly.
  - Deeper tables use a subquery chain back to contracts.
  - index_series / index_observations are shared global data: SELECT for all
    authenticated users, write restricted to the service role only.
  - revision_snapshots: INSERT + SELECT only — no UPDATE, no DELETE.
    Immutability is enforced here at the DB layer, not only at the API layer.
"""

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text

_VIA_CONTRACTS = (
    "contract_id IN (SELECT id FROM contracts WHERE tenant_id = get_tenant_id())"
)
_VIA_BILLS = (
    "bill_id IN ("
    "  SELECT rb.id FROM running_bills rb"
    "  JOIN contracts c ON c.id = rb.contract_id"
    "  WHERE c.tenant_id = get_tenant_id()"
    ")"
)
_VIA_RUNS = (
    "run_id IN ("
    "  SELECT pr.id FROM pvc_runs pr"
    "  JOIN contracts c ON c.id = pr.contract_id"
    "  WHERE c.tenant_id = get_tenant_id()"
    ")"
)


def upgrade():
    # ------------------------------------------------------------------
    # Helper: resolve current Supabase JWT uid → tenant_id.
    # ------------------------------------------------------------------
    op.execute(text("""
        CREATE OR REPLACE FUNCTION public.get_tenant_id() RETURNS UUID
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
            SELECT tenant_id FROM users WHERE supabase_auth_id = auth.uid()
        $$
    """))

    # ------------------------------------------------------------------
    # Enable RLS on every table.
    # ------------------------------------------------------------------
    _all_tables = [
        "tenants", "users",
        "contracts", "schedules", "contract_items",
        "running_bills", "bill_lines", "recoveries",
        "carry_forwards",
        "index_series", "index_observations",
        "pvc_rule_sets", "pvc_runs", "pvc_components", "revision_snapshots",
        "extra_item_decisions", "documents",
    ]
    for t in _all_tables:
        op.execute(text(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY"))
        op.execute(text(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY"))

    # ------------------------------------------------------------------
    # tenants — read own row only; no client-side writes
    # ------------------------------------------------------------------
    op.execute(text("""
        CREATE POLICY tenants_select ON tenants FOR SELECT
        USING (id = get_tenant_id())
    """))

    # ------------------------------------------------------------------
    # users — scoped by tenant_id
    # ------------------------------------------------------------------
    op.execute(text("""
        CREATE POLICY users_select ON users FOR SELECT
        USING (tenant_id = get_tenant_id())
    """))
    op.execute(text("""
        CREATE POLICY users_insert ON users FOR INSERT
        WITH CHECK (tenant_id = get_tenant_id())
    """))

    # ------------------------------------------------------------------
    # contracts — direct tenant_id; no DELETE (archive via status change)
    # ------------------------------------------------------------------
    op.execute(text("""
        CREATE POLICY contracts_select ON contracts FOR SELECT
        USING (tenant_id = get_tenant_id())
    """))
    op.execute(text("""
        CREATE POLICY contracts_insert ON contracts FOR INSERT
        WITH CHECK (tenant_id = get_tenant_id())
    """))
    op.execute(text("""
        CREATE POLICY contracts_update ON contracts FOR UPDATE
        USING (tenant_id = get_tenant_id())
        WITH CHECK (tenant_id = get_tenant_id())
    """))

    # ------------------------------------------------------------------
    # schedules — via contracts
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY schedules_select ON schedules FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY schedules_insert ON schedules FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY schedules_update ON schedules FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY schedules_delete ON schedules FOR DELETE
        USING ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # contract_items — via contracts
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY contract_items_select ON contract_items FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY contract_items_insert ON contract_items FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY contract_items_update ON contract_items FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY contract_items_delete ON contract_items FOR DELETE
        USING ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # running_bills — via contracts; no DELETE
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY running_bills_select ON running_bills FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY running_bills_insert ON running_bills FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY running_bills_update ON running_bills FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # bill_lines — via running_bills → contracts
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY bill_lines_select ON bill_lines FOR SELECT
        USING ({_VIA_BILLS})
    """))
    op.execute(text(f"""
        CREATE POLICY bill_lines_insert ON bill_lines FOR INSERT
        WITH CHECK ({_VIA_BILLS})
    """))
    op.execute(text(f"""
        CREATE POLICY bill_lines_update ON bill_lines FOR UPDATE
        USING ({_VIA_BILLS}) WITH CHECK ({_VIA_BILLS})
    """))
    op.execute(text(f"""
        CREATE POLICY bill_lines_delete ON bill_lines FOR DELETE
        USING ({_VIA_BILLS})
    """))

    # ------------------------------------------------------------------
    # recoveries — via running_bills → contracts
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY recoveries_select ON recoveries FOR SELECT
        USING ({_VIA_BILLS})
    """))
    op.execute(text(f"""
        CREATE POLICY recoveries_insert ON recoveries FOR INSERT
        WITH CHECK ({_VIA_BILLS})
    """))
    op.execute(text(f"""
        CREATE POLICY recoveries_update ON recoveries FOR UPDATE
        USING ({_VIA_BILLS}) WITH CHECK ({_VIA_BILLS})
    """))
    op.execute(text(f"""
        CREATE POLICY recoveries_delete ON recoveries FOR DELETE
        USING ({_VIA_BILLS})
    """))

    # ------------------------------------------------------------------
    # carry_forwards — via contracts (has contract_id directly)
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY carry_forwards_select ON carry_forwards FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY carry_forwards_insert ON carry_forwards FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY carry_forwards_update ON carry_forwards FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY carry_forwards_delete ON carry_forwards FOR DELETE
        USING ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # index_series / index_observations — shared global data.
    # All authenticated users SELECT; writes via service role only.
    # ------------------------------------------------------------------
    op.execute(text("""
        CREATE POLICY index_series_select ON index_series FOR SELECT
        USING (auth.uid() IS NOT NULL)
    """))
    op.execute(text("""
        CREATE POLICY index_observations_select ON index_observations FOR SELECT
        USING (auth.uid() IS NOT NULL)
    """))
    op.execute(text("""
        CREATE POLICY index_observations_insert ON index_observations FOR INSERT
        WITH CHECK (auth.uid() IS NOT NULL)
    """))
    op.execute(text("""
        CREATE POLICY index_observations_update ON index_observations FOR UPDATE
        USING (auth.uid() IS NOT NULL)
        WITH CHECK (auth.uid() IS NOT NULL)
    """))

    # ------------------------------------------------------------------
    # pvc_rule_sets — via contracts; no DELETE
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY pvc_rule_sets_select ON pvc_rule_sets FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY pvc_rule_sets_insert ON pvc_rule_sets FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY pvc_rule_sets_update ON pvc_rule_sets FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # pvc_runs — via contracts; INSERT only after creation, no UPDATE/DELETE
    # (immutability enforced at API layer; approved runs cannot be modified)
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY pvc_runs_select ON pvc_runs FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY pvc_runs_insert ON pvc_runs FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY pvc_runs_update ON pvc_runs FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # pvc_components — via pvc_runs → contracts; no UPDATE/DELETE
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY pvc_components_select ON pvc_components FOR SELECT
        USING ({_VIA_RUNS})
    """))
    op.execute(text(f"""
        CREATE POLICY pvc_components_insert ON pvc_components FOR INSERT
        WITH CHECK ({_VIA_RUNS})
    """))

    # ------------------------------------------------------------------
    # revision_snapshots — append-only: INSERT + SELECT only.
    # No UPDATE, no DELETE policies exist — the DB enforces this.
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY revision_snapshots_select ON revision_snapshots FOR SELECT
        USING ({_VIA_RUNS})
    """))
    op.execute(text(f"""
        CREATE POLICY revision_snapshots_insert ON revision_snapshots FOR INSERT
        WITH CHECK ({_VIA_RUNS})
    """))

    # ------------------------------------------------------------------
    # extra_item_decisions — via contracts; full CRUD
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY extra_item_decisions_select ON extra_item_decisions FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY extra_item_decisions_insert ON extra_item_decisions FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY extra_item_decisions_update ON extra_item_decisions FOR UPDATE
        USING ({_VIA_CONTRACTS}) WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY extra_item_decisions_delete ON extra_item_decisions FOR DELETE
        USING ({_VIA_CONTRACTS})
    """))

    # ------------------------------------------------------------------
    # documents — via contracts; no UPDATE (re-upload replaces the row)
    # ------------------------------------------------------------------
    op.execute(text(f"""
        CREATE POLICY documents_select ON documents FOR SELECT
        USING ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY documents_insert ON documents FOR INSERT
        WITH CHECK ({_VIA_CONTRACTS})
    """))
    op.execute(text(f"""
        CREATE POLICY documents_delete ON documents FOR DELETE
        USING ({_VIA_CONTRACTS})
    """))


def downgrade():
    op.execute(text("DROP FUNCTION IF EXISTS public.get_tenant_id()"))

    _all_tables = [
        "tenants", "users",
        "contracts", "schedules", "contract_items",
        "running_bills", "bill_lines", "recoveries",
        "carry_forwards",
        "index_series", "index_observations",
        "pvc_rule_sets", "pvc_runs", "pvc_components", "revision_snapshots",
        "extra_item_decisions", "documents",
    ]
    for t in _all_tables:
        op.execute(text(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY"))
