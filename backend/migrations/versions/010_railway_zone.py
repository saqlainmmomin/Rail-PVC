"""Add railway_zone to contracts

Revision ID: 010
Revises: 009
Create Date: 2026-05-16

GCC 46A.9(2) maps each Railway zone to a JPC city (Delhi / Kolkata / Mumbai /
Chennai). The API uses the contract's zone to select the right city's JPC rates
when building the IndexSnapshot for an engine call. Zone is stored on the
contract since it's fixed at award time and never changes.

City → zone mapping (for API lookups):
  Delhi:   NR, NCR, NER, NWR
  Kolkata: ER, ECR, ECOR, NFR, SER, SECR
  Mumbai:  CR, WR, WCR
  Chennai: SR, SCR, SWR
"""

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import text


def upgrade():
    op.execute(text("""
        CREATE TYPE railway_zone AS ENUM (
            'NR', 'NCR', 'NER', 'NWR',
            'ER', 'ECR', 'ECOR', 'NFR', 'SER', 'SECR',
            'CR', 'WR', 'WCR',
            'SR', 'SCR', 'SWR'
        )
    """))

    op.execute(text("""
        ALTER TABLE contracts ADD COLUMN railway_zone railway_zone
    """))


def downgrade():
    op.execute(text("ALTER TABLE contracts DROP COLUMN railway_zone"))
    op.execute(text("DROP TYPE railway_zone"))
