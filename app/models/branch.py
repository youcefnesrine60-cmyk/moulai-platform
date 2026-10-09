# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 BRANCH MODEL
# نموذج فرع المطعم
# يدير فروع المطاعم ومواقعها وبياناتها
# ==============================================

"""MoulAI operational module for branch.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🧩 TYPES
# ==============================================

# ==============================================
# 🏢 BRANCH
# ==============================================


class Branch(BaseModel):
    """
    نموذج فرع المطعم

    يدير:
        - البيانات الأساسية للفرع (الاسم، الهاتف)
        - الموقع الجغرافي (wilaya, lat, lng)
        - حالة النشاط
        - العلاقات مع المطعم والطلبات

    Attributes:
        restaurant_id: معرف المطعم (ForeignKey)
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض (الإحداثي)
        lng: خط الطول (الإحداثي)
        is_active: حالة النشاط
        restaurant: علاقة مع نموذج Restaurant
        orders: قائمة الطلبات التابعة للفرع
    """

    __tablename__ = "branches"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )
    name = Column(
        Text,
        nullable=False,
        comment="اسم الفرع",
    )
    phone = Column(
        String(20),
        comment="رقم الهاتف",
    )
    wilaya = Column(
        String(100),
        comment="الولاية",
    )
    lat = Column(
        Float,
        comment="خط العرض (الإحداثي)",
    )
    lng = Column(
        Float,
        comment="خط الطول (الإحداثي)",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )

    # ==========================================
    # 🔒 CONSTRAINTS
    # ==========================================

    __table_args__ = (
        Index(
            "idx_branches_restaurant",
            "restaurant_id",
            # comment="مؤشر لتحسين أداء البحث عن فروع مطعم معين",
        ),
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurant = relationship(
        "Restaurant",
        back_populates="branches",
        lazy="selectin",
        # comment="المطعم",
    )
    orders = relationship(
        "Order",
        back_populates="branch",
        lazy="selectin",
        # comment="قائمة الطلبات التابعة للفرع",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف والاسم ومعرف المطعم
        """
        return f"<Branch(id={self.id}, name={self.name}, restaurant_id={self.restaurant_id})>"
