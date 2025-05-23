"""chat user id + streamer name

Revision ID: 06988deef2e4
Revises: 04b137d1f753
Create Date: 2024-10-14 01:51:20.171343

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06988deef2e4"
down_revision: Union[str, None] = "04b137d1f753"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()

    op.add_column(
        "chats",
        sa.Column("user_id", sa.BIGINT(), nullable=True),
        schema="tntb",
    )
    conn.execute(sa.text("UPDATE tntb.chats SET user_id=owner_id;"))
    op.alter_column(
        "chats",
        "user_id",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema="tntb",
    )
    op.drop_column("chats", "owner_id", schema="tntb")

    op.add_column(
        "streamers",
        sa.Column("name", sa.String(), nullable=True),
        schema="tntb",
    )
    conn.execute(sa.text("UPDATE tntb.streamers SET name='-';"))
    op.alter_column(
        "streamers",
        "name",
        existing_type=sa.String(),
        nullable=False,
        schema="tntb",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()

    op.add_column(
        "chats",
        sa.Column("owner_id", sa.BIGINT(), nullable=True),
        schema="tntb",
    )
    conn.execute(sa.text("UPDATE tntb.chats SET owner_id=user_id;"))
    op.alter_column(
        "chats",
        "owner_id",
        existing_type=sa.BIGINT(),
        nullable=False,
        schema="tntb",
    )
    op.drop_column("chats", "user_id", schema="tntb")

    op.drop_column("streamers", "name", schema="tntb")
    # ### end Alembic commands ###
