"""add enabled_agents to jobs

Revision ID: 16a982348b6f
Revises: 48bd05d0f731
Create Date: 2026-02-11 07:44:51.086534

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '16a982348b6f'
down_revision: str | Sequence[str] = '48bd05d0f731'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'jobs',
        sa.Column(
            'enabled_agents',
            postgresql.ARRAY(sa.String()),
            server_default='{numeric_validation,logic_consistency,disclosure_compliance,external_signal}',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('jobs', 'enabled_agents')
