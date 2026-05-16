"""Security hardening: index_observations write lock, pvc_runs immutability,
railway_zone NOT NULL

Revision ID: 011
Revises: 010
Create Date: 2026-05-16

Addresses three P3-PRE-REVIEW findings:

P3-PRE-02 — index_observations was writable by any authenticated user even
though it is shared global data.  Only SELECT is appropriate for ordinary
users; writes go through the service role (which bypasses RLS) or a trusted
backend call.  The INSERT and UPDATE policies added in 009 are dropped here.

P3-PRE-03 — pvc_runs had a broad tenant-wide UPDATE policy but the product
contract requires approved runs to be immutable.  A BEFORE UPDATE trigger now
raises an exception if the existing status is 'Approved', enforcing
immutability at the DB layer regardless of the calling path.

P3-PRE-04 — contracts.railway_zone was nullable, blocking zone-specific JPC
snapshot selection in P3-009.  Existing rows are backfilled to 'NR' as a
placeholder (real prod deployments must run a per-contract backfill before
applying this migration).  The column is then set NOT NULL.
"""

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    # ------------------------------------------------------------------
    # P3-PRE-02: lock down index_observations — SELECT only for auth users.
    # The INSERT and UPDATE policies granted in 009 are removed.  The service
    # role bypasses RLS so seed scripts / admin ops still work unimpeded.
    # ------------------------------------------------------------------
    op.execute(text("DROP POLICY IF EXISTS index_observations_insert ON index_observations"))
    op.execute(text("DROP POLICY IF EXISTS index_observations_update ON index_observations"))

    # ------------------------------------------------------------------
    # P3-PRE-03: enforce pvc_runs immutability at the DB layer.
    # The trigger fires BEFORE any UPDATE; if the stored status is 'Approved'
    # it raises an exception, preventing any mutation regardless of the caller.
    # The existing tenant-scoped UPDATE RLS policy remains for pre-approval
    # state transitions (Draft → Calculated → ExceptionFlagged → Approved).
    # ------------------------------------------------------------------
    op.execute(text("""
        CREATE OR REPLACE FUNCTION public.prevent_approved_run_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status = 'Approved' THEN
                RAISE EXCEPTION
                    'pvc_run % is Approved and cannot be modified', OLD.id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
    """))

    op.execute(text("""
        CREATE TRIGGER trg_pvc_runs_immutable_approved
        BEFORE UPDATE ON pvc_runs
        FOR EACH ROW EXECUTE FUNCTION public.prevent_approved_run_update()
    """))

    # ------------------------------------------------------------------
    # P3-PRE-04: railway_zone NOT NULL.
    # Backfill any pre-existing NULL rows to 'NR' as a safe placeholder.
    # Production deployments must audit and correct these values before
    # running PVC calculations.
    # ------------------------------------------------------------------
    op.execute(text("""
        UPDATE contracts SET railway_zone = 'NR' WHERE railway_zone IS NULL
    """))

    op.execute(text("""
        ALTER TABLE contracts ALTER COLUMN railway_zone SET NOT NULL
    """))


def downgrade():
    # Restore railway_zone to nullable
    op.execute(text("ALTER TABLE contracts ALTER COLUMN railway_zone DROP NOT NULL"))

    # Remove pvc_runs immutability trigger
    op.execute(text("DROP TRIGGER IF EXISTS trg_pvc_runs_immutable_approved ON pvc_runs"))
    op.execute(text("DROP FUNCTION IF EXISTS public.prevent_approved_run_update()"))

    # Restore index_observations write policies for authenticated users
    op.execute(text("""
        CREATE POLICY index_observations_insert ON index_observations FOR INSERT
        WITH CHECK (auth.uid() IS NOT NULL)
    """))
    op.execute(text("""
        CREATE POLICY index_observations_update ON index_observations FOR UPDATE
        USING (auth.uid() IS NOT NULL)
        WITH CHECK (auth.uid() IS NOT NULL)
    """))
