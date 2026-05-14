"""contracts, schedules, contract_items

Revision ID: 002
Revises: 001
Create Date: 2026-05-14
"""

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("""
        CREATE TYPE contract_status AS ENUM (
            'Draft', 'Configured', 'Active', 'Completed', 'Archived'
        )
    """)

    op.execute("""
        CREATE TYPE gst_mode AS ENUM ('inclusive', 'exclusive')
    """)

    op.execute("""
        CREATE TYPE schedule_type AS ENUM ('DSR', 'NS', 'ExtraNS')
    """)

    op.execute("""
        CREATE TYPE steel_subtype AS ENUM (
            'angles', 'plates', 'other_sections', 'tmt'
        )
    """)

    op.execute("""
        CREATE TABLE contracts (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id        UUID NOT NULL REFERENCES tenants(id),
            tender_number    TEXT NOT NULL,
            agreement_number TEXT,
            loa_number       TEXT,
            loa_date         DATE,
            contractor_name  TEXT NOT NULL,
            work_description TEXT,
            contract_value   NUMERIC(15,4),
            bid_amount       NUMERIC(15,4),
            start_date       DATE,
            completion_date  DATE,
            base_month       DATE NOT NULL,
            gst_mode         gst_mode NOT NULL DEFAULT 'exclusive',
            pvc_applicable   BOOLEAN NOT NULL DEFAULT TRUE,
            overall_rebate   NUMERIC(5,4) NOT NULL DEFAULT 0,
            status           contract_status NOT NULL DEFAULT 'Draft',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX contracts_tenant_id_idx ON contracts(tenant_id)")

    op.execute("""
        CREATE TABLE schedules (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id      UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            name             TEXT NOT NULL,
            schedule_type    schedule_type NOT NULL,
            bid_discount_pct NUMERIC(5,4) NOT NULL DEFAULT 0,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX schedules_contract_id_idx ON schedules(contract_id)")

    op.execute("""
        CREATE TABLE contract_items (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id    UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            schedule_id    UUID NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
            item_code      TEXT NOT NULL,
            description    TEXT,
            unit           TEXT,
            original_qty   NUMERIC(15,4),
            revised_qty    NUMERIC(15,4),
            base_rate      NUMERIC(15,4),
            agreement_rate NUMERIC(15,4),
            is_cement_item BOOLEAN NOT NULL DEFAULT FALSE,
            steel_subtype  steel_subtype,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX contract_items_contract_id_idx ON contract_items(contract_id)")
    op.execute("CREATE INDEX contract_items_schedule_id_idx ON contract_items(schedule_id)")


def downgrade():
    op.execute("DROP TABLE contract_items")
    op.execute("DROP TABLE schedules")
    op.execute("DROP TABLE contracts")
    op.execute("DROP TYPE steel_subtype")
    op.execute("DROP TYPE schedule_type")
    op.execute("DROP TYPE gst_mode")
    op.execute("DROP TYPE contract_status")
