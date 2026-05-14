"""tenants and users

Revision ID: 001
Revises:
Create Date: 2026-05-14
"""

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("""
        CREATE TABLE tenants (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE users (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id        UUID NOT NULL REFERENCES tenants(id),
            supabase_auth_id UUID NOT NULL UNIQUE,
            email            TEXT NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX users_tenant_id_idx ON users(tenant_id)")
    op.execute("CREATE INDEX users_supabase_auth_id_idx ON users(supabase_auth_id)")


def downgrade():
    op.execute("DROP TABLE users")
    op.execute("DROP TABLE tenants")
