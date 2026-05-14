"""pvc_rule_sets

Revision ID: 006
Revises: 005
Create Date: 2026-05-14
"""

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TYPE quarter_mode AS ENUM (
            'measurement_date', 'bill_date', 'operator_override'
        )
    """))

    op.execute(text("""
        CREATE TYPE extra_item_policy AS ENUM (
            'exclude_by_default', 'include_by_default'
        )
    """))

    op.execute(text("""
        CREATE TYPE rounding_mode AS ENUM ('round_2', 'truncate_2')
    """))

    op.execute(text("""
        CREATE TYPE negative_pvc_policy AS ENUM ('allow', 'block', 'zero_floor')
    """))

    op.execute(text("""
        CREATE TABLE pvc_rule_sets (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id         UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            version             INTEGER NOT NULL DEFAULT 1,
            quarter_mode        quarter_mode NOT NULL DEFAULT 'measurement_date',
            component_weights   JSONB NOT NULL,
            extra_item_policy   extra_item_policy NOT NULL DEFAULT 'exclude_by_default',
            adjustable_fraction NUMERIC(5,4) NOT NULL DEFAULT 0.85,
            rounding_mode       rounding_mode NOT NULL DEFAULT 'round_2',
            negative_pvc_policy negative_pvc_policy NOT NULL DEFAULT 'allow',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(contract_id, version)
        )
    """))

    op.execute(text("CREATE INDEX pvc_rule_sets_contract_id_idx ON pvc_rule_sets(contract_id)"))


def downgrade():
    op.execute(text("DROP TABLE pvc_rule_sets"))
    op.execute(text("DROP TYPE negative_pvc_policy"))
    op.execute(text("DROP TYPE rounding_mode"))
    op.execute(text("DROP TYPE extra_item_policy"))
    op.execute(text("DROP TYPE quarter_mode"))
