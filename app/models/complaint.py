# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📣 COMPLAINT MODEL
# نموذج الشكوى - إدارة شكاوى العملاء
# يربط الشكوى بالمستخدم والمطعم والطلب المرتبط
# ==============================================

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from .base import BaseModel

# ==============================================
# 📣 COMPLAINT
# ==============================================

class Complaint(BaseModel):
    """
    نموذج الشكوى - إدارة شكاوى العملاء.

    يربط الشكوى بـ:
        - المستخدم صاحب الشكوى
        - المطعم المعني بالشكوى
        - الطلب المرتبط (اختياري)

    Attributes:
        user_id: معرف المستخدم صاحب الشكوى.
        restaurant_id: معرف المطعم المعني بالشكوى.
        order_id: معرف الطلب المرتبط بالشكوى (اختياري).
        description: وصف الشكوى.
        status: حالة الشكوى (open, in_progress, resolved, closed).
    """
    __tablename__ = "complaints"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المستخدم صاحب الشكوى",
    )
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم المعني بالشكوى",
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="معرف الطلب المرتبط بالشكوى",
    )
    description = Column(
        Text,
        nullable=False,
        comment="وصف الشكوى",
    )
    status = Column(
        String(30),
        nullable=False,
        default="open",
        server_default="open",
        comment="حالة الشكوى: open, in_progress, resolved, closed",
    )

    # ==========================================
    # 🔗 TABLE ARGS
    # ==========================================

    __table_args__ = (
        Index("idx_complaints_restaurant_status", "restaurant_id", "status"),
        Index("idx_complaints_user", "user_id"),
        Index("idx_complaints_order", "order_id"),
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج.

        Returns:
            سلسلة نصية تحتوي على المعرف والحالة ومعرف المطعم.
        """
        return (
            f"<Complaint(id={self.id}, "
            f"restaurant_id={self.restaurant_id}, "
            f"status={self.status})>"
        )