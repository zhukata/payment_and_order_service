"""initial schema and seed orders

Revision ID: 20260320_0001
Revises:
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260320_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("not_paid", "partially_paid", "paid", name="orderstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_amount > 0", name="ck_orders_total_amount_positive"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("cash", "acquiring", name="paymenttype", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "success", "failed", "refunded", name="paymentstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("bank_payment_id", sa.String(length=100), nullable=True, unique=True),
        sa.Column("bank_status_snapshot", sa.String(length=50), nullable=True),
        sa.Column("bank_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )

    op.create_index("idx_payments_order_id", "payments", ["order_id"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO orders (id, total_amount, status, created_at)
            VALUES
                (1, 1000, 'not_paid', NOW()),
                (2, 2500, 'not_paid', NOW())
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_table("orders")
