"""migrate read_status from Chinese to English enum values

Revision ID: a1b2c3d4e5f6
Revises: da7b5d88d194
Create Date: 2026-03-08 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'da7b5d88d194'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Chinese → English mapping
STATUS_MAP = {
    '未读': 'unread',
    '在读': 'reading',
    '已读': 'read',
    '选读': 'want_to_read',
    '翻阅': 'skimmed',
    '搁置': 'shelved',
}

# Reverse mapping for downgrade
REVERSE_MAP = {v: k for k, v in STATUS_MAP.items()}


def upgrade() -> None:
    """Migrate read_status values from Chinese to English enum constants."""
    conn = op.get_bind()
    for old_val, new_val in STATUS_MAP.items():
        conn.execute(
            sa.text("UPDATE books SET read_status = :new WHERE read_status = :old"),
            {"new": new_val, "old": old_val},
        )
    # Update server default for new rows
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.alter_column(
            'read_status',
            server_default='unread',
            comment='阅读状态: unread, reading, read, want_to_read, skimmed, shelved',
        )


def downgrade() -> None:
    """Revert read_status values from English back to Chinese."""
    conn = op.get_bind()
    for eng_val, chn_val in REVERSE_MAP.items():
        conn.execute(
            sa.text("UPDATE books SET read_status = :old WHERE read_status = :new"),
            {"old": chn_val, "new": eng_val},
        )
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.alter_column(
            'read_status',
            server_default='未读',
            comment='阅读状态：已读, 在读, 未读, 选读, 翻阅, 搁置',
        )
