"""fix user_roles charset

Revision ID: d3b83cd57489
Revises: cf8f7890319a
Create Date: 2026-04-30 21:19:51.999309

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3b83cd57489'
down_revision = 'cf8f7890319a'
branch_labels = None
depends_on = None


def upgrade():
    # Alembic autogenerate 不跟踪表级 charset 差异；此处手工补充，
    # 确保生产机（MySQL server 默认字符集不一定是 utf8mb4）也能正确建表。
    op.execute(
        'ALTER TABLE user_roles '
        'CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
    )


def downgrade():
    pass
