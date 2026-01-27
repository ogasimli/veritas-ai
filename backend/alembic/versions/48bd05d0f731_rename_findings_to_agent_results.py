"""rename_findings_to_agent_results

Revision ID: 48bd05d0f731
Revises: 1333a39d8e09
Create Date: 2026-01-26 16:49:13.011043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48bd05d0f731'
down_revision: Union[str, Sequence[str], None] = '1333a39d8e09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Rename table
    op.rename_table("findings", "agent_results")
    
    # Add new columns
    op.add_column("agent_results", sa.Column("error", sa.Text(), nullable=True))
    # We add server_default temporarily to populate existing rows, then remove it
    op.add_column("agent_results", sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))

    # Alter existing columns to be nullable
    op.alter_column("agent_results", "description", nullable=True)
    op.alter_column("agent_results", "severity", nullable=True)
    op.alter_column("agent_results", "source_refs", nullable=True)

    # Remove server_default for raw_data after adding it
    op.alter_column("agent_results", "raw_data", server_default=None)


def downgrade() -> None:
    # Reverse changes
    # Note: We need to handle potential nulls if we revert changes. 
    # In a real rollback, we might lose data or fail if columns are null.
    # For dev, we'll just try to revert.

    # Revert column nullability
    # This might fail if description/severity are null
    op.alter_column("agent_results", "source_refs", nullable=False)
    op.alter_column("agent_results", "severity", nullable=False)
    op.alter_column("agent_results", "description", nullable=False)
    
    # Drop new columns
    op.drop_column("agent_results", "raw_data")
    op.drop_column("agent_results", "error")
    
    # Rename table back
    op.rename_table("agent_results", "findings")
