"""drop_payments_user_id

Revision ID: 4c3017ab0067
Revises: 48b7a91adb30
Create Date: 2026-08-13 13:49:15.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '4c3017ab0067'
down_revision: Union[str, None] = '2d999b8ed18f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    تسجيل أن عمود user_id موجود بالفعل في payments.
    هذه الترحيلة فقط لتسجيل الحالة الحالية.
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # التحقق من وجود العمود
    columns = [col["name"] for col in inspector.get_columns("payments")]
    
    if "user_id" in columns:
        print("[OK] user_id column already exists in payments - skipping")
    else:
        # إذا لم يكن موجوداً (حالة نادرة)، قم بإضافته
        op.add_column("payments", sa.Column("user_id", sa.Integer(), nullable=True))
        print("[OK] Added user_id column to payments")
    
    #  التحقق من وجود المفتاح الخارجي
    fk_exists = False
    for fk in inspector.get_foreign_keys("payments"):
        if fk["name"] == "fk_payments_user":
            fk_exists = True
            break
    
    if not fk_exists:
        op.create_foreign_key(
            "fk_payments_user",
            "payments",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        print("[OK] Added foreign key fk_payments_user")
    
    #  التحقق من وجود الفهرس
    indexes = [idx["name"] for idx in inspector.get_indexes("payments")]
    
    if "idx_payments_user_id" not in indexes:
        op.create_index("idx_payments_user_id", "payments", ["user_id"])
        print("[OK] Added index idx_payments_user_id")


def downgrade() -> None:
    """
    حذف عمود user_id من payments (إذا كان موجوداً).
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    #  التحقق من وجود العمود قبل الحذف
    columns = [col["name"] for col in inspector.get_columns("payments")]
    
    if "user_id" in columns:
        # حذف الفهرس
        op.drop_index("idx_payments_user_id", table_name="payments")
        
        # حذف المفتاح الخارجي
        op.drop_constraint("fk_payments_user", "payments", type_="foreignkey")
        
        # حذف العمود
        op.drop_column("payments", "user_id")
        
        print("[OK] Dropped user_id column from payments")
    else:
        print("[INFO] user_id column does not exist in payments - skipping")