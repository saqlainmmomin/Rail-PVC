"""pvc_runs, pvc_components, revision_snapshots

Revision ID: 007
Revises: 006
Create Date: 2026-05-14
"""

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TYPE pvc_run_status AS ENUM (
            'Draft', 'Calculated', 'ExceptionFlagged',
            'Approved', 'Exported', 'Superseded'
        )
    """))

    op.execute(text("""
        CREATE TYPE pvc_category AS ENUM (
            'labour', 'plant', 'fuel', 'materials',
            'cement', 'steel_angles', 'steel_plates',
            'steel_other', 'steel_tmt'
        )
    """))

    op.execute(text("""
        CREATE TABLE pvc_runs (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id    UUID NOT NULL REFERENCES contracts(id),
            bill_id        UUID NOT NULL REFERENCES running_bills(id),
            rule_set_id    UUID NOT NULL REFERENCES pvc_rule_sets(id),
            index_snapshot JSONB NOT NULL,
            bill_snapshot  JSONB NOT NULL,
            w_derivation   JSONB NOT NULL,
            status         pvc_run_status NOT NULL DEFAULT 'Draft',
            superseded_by  UUID REFERENCES pvc_runs(id),
            approved_by    TEXT,
            approved_at    TIMESTAMPTZ,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    op.execute(text("CREATE INDEX pvc_runs_contract_id_idx ON pvc_runs(contract_id)"))
    op.execute(text("CREATE INDEX pvc_runs_bill_id_idx ON pvc_runs(bill_id)"))

    op.execute(text("""
        CREATE TABLE pvc_components (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id            UUID NOT NULL REFERENCES pvc_runs(id) ON DELETE CASCADE,
            category          pvc_category NOT NULL,
            eligible_amount   NUMERIC(15,4) NOT NULL,
            base_index        NUMERIC(15,4) NOT NULL,
            current_avg_index NUMERIC(15,4) NOT NULL,
            weight            NUMERIC(10,8) NOT NULL,
            pvc_value         NUMERIC(15,4) NOT NULL,
            UNIQUE(run_id, category)
        )
    """))

    op.execute(text("CREATE INDEX pvc_components_run_id_idx ON pvc_components(run_id)"))

    op.execute(text("""
        CREATE TABLE revision_snapshots (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id        UUID NOT NULL REFERENCES pvc_runs(id),
            snapshot_data JSONB NOT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    op.execute(text("CREATE INDEX revision_snapshots_run_id_idx ON revision_snapshots(run_id)"))


def downgrade():
    op.execute(text("DROP TABLE revision_snapshots"))
    op.execute(text("DROP TABLE pvc_components"))
    op.execute(text("DROP TABLE pvc_runs"))
    op.execute(text("DROP TYPE pvc_category"))
    op.execute(text("DROP TYPE pvc_run_status"))
