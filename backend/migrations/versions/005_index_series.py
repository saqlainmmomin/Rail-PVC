"""index_series and index_observations

Revision ID: 005
Revises: 004
Create Date: 2026-05-14
"""

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.execute("""
        CREATE TYPE index_source AS ENUM ('RBI', 'JPC')
    """)

    op.execute("""
        CREATE TABLE index_series (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name               TEXT NOT NULL UNIQUE,
            source_publication index_source NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE index_observations (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            series_id     UUID NOT NULL REFERENCES index_series(id),
            month         DATE NOT NULL,
            value         NUMERIC(15,4) NOT NULL,
            source_ref    TEXT,
            revision_flag BOOLEAN NOT NULL DEFAULT FALSE,
            revised_at    TIMESTAMPTZ,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(series_id, month)
        )
    """)

    op.execute("CREATE INDEX index_observations_series_id_idx ON index_observations(series_id)")
    op.execute("CREATE INDEX index_observations_month_idx ON index_observations(month)")


def downgrade():
    op.execute("DROP TABLE index_observations")
    op.execute("DROP TABLE index_series")
    op.execute("DROP TYPE index_source")
