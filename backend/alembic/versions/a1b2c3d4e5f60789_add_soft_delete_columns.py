"""add soft delete columns (is_deleted, deleted_at) to patient/medical_record/diagnosis_report

Revision ID: a1b2c3d4e5f60789
Revises: 8d5183160afc
Create Date: 2026-08-13 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f60789'
down_revision: Union[str, None] = '8d5183160afc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 三张业务表加软删除列：is_deleted 非空 + server_default='0'（存量行回填 0，裸 SQL 插入安全）
    for table in ('patient', 'medical_record', 'diagnosis_report'):
        op.add_column(table, sa.Column(
            'is_deleted', sa.SmallInteger(), nullable=False, server_default='0',
            comment='是否删除: 0正常 1已删除'))
        op.add_column(table, sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table in ('patient', 'medical_record', 'diagnosis_report'):
        op.drop_column(table, 'deleted_at')
        op.drop_column(table, 'is_deleted')
