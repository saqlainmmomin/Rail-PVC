"""extra_item_decisions and documents

Revision ID: 008
Revises: 007
Create Date: 2026-05-14
"""

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TYPE document_type AS ENUM (
            'agreement', 'mb', 'bill', 'recovery', 'workbook', 'other'
        )
    """))

    op.execute(text("""
        CREATE TABLE extra_item_decisions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            item_id     UUID NOT NULL REFERENCES contract_items(id) ON DELETE CASCADE,
            eligible    BOOLEAN,
            decided_by  TEXT,
            decided_at  TIMESTAMPTZ,
            notes       TEXT,
            UNIQUE(contract_id, item_id)
        )
    """))

    op.execute(text("CREATE INDEX extra_item_decisions_contract_id_idx ON extra_item_decisions(contract_id)"))

    op.execute(text("""
        CREATE TABLE documents (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contract_id       UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            file_type         document_type NOT NULL,
            storage_path      TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))

    op.execute(text("CREATE INDEX documents_contract_id_idx ON documents(contract_id)"))


def downgrade():
    op.execute(text("DROP TABLE documents"))
    op.execute(text("DROP TABLE extra_item_decisions"))
    op.execute(text("DROP TYPE document_type"))
