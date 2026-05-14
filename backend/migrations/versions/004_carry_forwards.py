"""carry_forwards

Revision ID: 004
Revises: 003
Create Date: 2026-05-14
"""

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("""
        CREATE TABLE carry_forwards (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id     UUID NOT NULL REFERENCES contracts(id),
            item_id         UUID NOT NULL REFERENCES contract_items(id),
            source_bill_id  UUID NOT NULL REFERENCES running_bills(id),
            target_bill_id  UUID REFERENCES running_bills(id),
            recorded_qty    NUMERIC(15,4) NOT NULL,
            paid_qty_source NUMERIC(15,4) NOT NULL,
            paid_ratio      NUMERIC(10,8) NOT NULL,
            carry_qty       NUMERIC(15,4) NOT NULL,
            steel_subtype   steel_subtype,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT carry_forwards_paid_ratio_range CHECK (paid_ratio >= 0 AND paid_ratio <= 1)
        )
    """)

    op.execute("CREATE INDEX carry_forwards_contract_id_idx ON carry_forwards(contract_id)")
    op.execute("CREATE INDEX carry_forwards_item_id_idx ON carry_forwards(item_id)")
    op.execute("CREATE INDEX carry_forwards_source_bill_id_idx ON carry_forwards(source_bill_id)")


def downgrade():
    op.execute("DROP TABLE carry_forwards")
