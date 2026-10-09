# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER MODEL
# نموذج عداد طلبات المطعم
# يدير ترقيم الطلبات المتسلسل لكل مطعم
# ==============================================

"""MoulAI operational module for restaurant order counter.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship

from .base import BaseModelWithoutId

# ==============================================
# 🧩 TYPES
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER
# ==============================================


class RestaurantOrderCounter(BaseModelWithoutId):
    """
    نموذج عداد طلبات المطعم - يتتبع آخر رقم طلب.

     يدير:
         - ترقيم الطلبات المتسلسل لكل مطعم
         - الحفاظ على آخر رقم طلب مستخدم
         - ضمان عدم تكرار أرقام الطلبات

     Attributes:
         restaurant_id: معرف المطعم (Primary Key, ForeignKey)
         last_number: آخر رقم طلب تم استخدامه
         restaurant: علاقة مع نموذج Restaurant
    """

    __tablename__ = "restaurant_order_counters"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        primary_key=True,
        comment="معرف المطعم (المفتاح الأساسي)",
    )
    last_number = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="آخر رقم طلب تم استخدامه",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurant = relationship(
        "Restaurant",
        back_populates="order_counter",
        lazy="selectin",
        # comment="المطعم المرتبط",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على معرف المطعم وآخر رقم
        """
        return (
            f"<RestaurantOrderCounter(restaurant_id={self.restaurant_id}, "
            f"last_number={self.last_number})>"
        )
