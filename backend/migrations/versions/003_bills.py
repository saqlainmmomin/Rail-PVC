"""running_bills, bill_lines, recoveries

Revision ID: 003
Revises: 002
Create Date: 2026-05-14
"""

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("""
        CREATE TYPE bill_status AS ENUM (
            'Draft', 'Imported', 'Reconciled', 'Approved',
            'Submitted', 'Revised', 'Locked'
        )
    """)

    op.execute("""
        CREATE TYPE recovery_type AS ENUM (
            'security_deposit', 'income_tax', 'labour_cess', 'water', 'other'
        )
    """)

    op.execute("""
        CREATE TABLE running_bills (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id      UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            bill_number      INTEGER NOT NULL,
            bill_date        DATE,
            measurement_date DATE NOT NULL,
            gross_amount     NUMERIC(15,4),
            net_amount       NUMERIC(15,4),
            status           bill_status NOT NULL DEFAULT 'Draft',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(contract_id, bill_number)
        )
    """)

    op.execute("CREATE INDEX running_bills_contract_id_idx ON running_bills(contract_id)")

    op.execute("""
        CREATE TABLE bill_lines (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bill_id                  UUID NOT NULL REFERENCES running_bills(id) ON DELETE CASCADE,
            item_id                  UUID NOT NULL REFERENCES contract_items(id),
            qty_up_to_last           NUMERIC(15,4) NOT NULL DEFAULT 0,
            qty_since_last           NUMERIC(15,4) NOT NULL DEFAULT 0,
            qty_up_to_date           NUMERIC(15,4) NOT NULL DEFAULT 0,
            amount_up_to_last        NUMERIC(15,4) NOT NULL DEFAULT 0,
            amount_since_last        NUMERIC(15,4) NOT NULL DEFAULT 0,
            amount_up_to_date        NUMERIC(15,4) NOT NULL DEFAULT 0,
            special_condition_amount NUMERIC(15,4) NOT NULL DEFAULT 0,
            UNIQUE(bill_id, item_id)
        )
    """)

    op.execute("CREATE INDEX bill_lines_bill_id_idx ON bill_lines(bill_id)")
    op.execute("CREATE INDEX bill_lines_item_id_idx ON bill_lines(item_id)")

    op.execute("""
        CREATE TABLE recoveries (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bill_id          UUID NOT NULL REFERENCES running_bills(id) ON DELETE CASCADE,
            recovery_type    recovery_type NOT NULL,
            amount           NUMERIC(15,4) NOT NULL,
            affects_pvc_base BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    op.execute("CREATE INDEX recoveries_bill_id_idx ON recoveries(bill_id)")


def downgrade():
    op.execute("DROP TABLE recoveries")
    op.execute("DROP TABLE bill_lines")
    op.execute("DROP TABLE running_bills")
    op.execute("DROP TYPE recovery_type")
    op.execute("DROP TYPE bill_status")
