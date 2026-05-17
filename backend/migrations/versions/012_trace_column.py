"""Add trace JSONB column to pvc_runs (Phase 3 dependency)

Revision ID: 012
Revises: 011
Create Date: 2026-05-17

P3-009 must persist engine.TraceContract (schema_version="1.0") into
pvc_runs.trace JSONB — required by REVIEW.md HIGH-8.

This migration is authored by CC-SH (Phase 3 branch) because the column
is a hard dependency of P3-009 acceptance criteria. It is a non-breaking,
additive schema change that does not touch RLS policies or triggers.
"""

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("ALTER TABLE pvc_runs ADD COLUMN IF NOT EXISTS trace JSONB"))


def downgrade():
    op.execute(text("ALTER TABLE pvc_runs DROP COLUMN IF EXISTS trace"))
