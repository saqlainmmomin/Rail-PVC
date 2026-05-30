"""Add is_admin flag to users table.

Revision ID: 013
Revises: 012
Create Date: 2026-05-30

Enables the admin role gate for index write endpoints (IDX-2). The
privileged DATABASE_URL bypasses RLS, so write access to the global
index_observations table is gated at the application layer by this flag
rather than relying on RLS policies.

Default FALSE — existing users remain ordinary users. Promotion is a
manual out-of-band operation (UPDATE users SET is_admin = TRUE WHERE ...).
"""

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("""
        ALTER TABLE users
        ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE
    """)


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN is_admin")
