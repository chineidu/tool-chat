"""[drop] Drop 'grade' from 'courses' table

Revision ID: 2b4913966484
Revises:
Create Date: 2025-10-30 21:33:42.561437

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b4913966484"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("courses", "grade")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("courses", sa.Column("grade", sa.Integer(), nullable=True))
    pass
