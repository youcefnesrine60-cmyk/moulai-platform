# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📂 CATEGORY MODEL
# نموذج تصنيف المنتجات
# يدير تصنيفات المنتجات داخل المطاعم
# ==============================================

"""MoulAI operational module for category.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 📂 CATEGORY
# ==============================================


class Category(BaseModel):
    """
    نموذج تصنيف المنتجات

    يدير:
        - اسم التصنيف
        - ترتيب التصنيف
        - العلاقات مع المطعم والمنتجات

    Attributes:
        restaurant_id: معرف المطعم (ForeignKey)
        name: اسم التصنيف
        sort_order: ترتيب التصنيف
        restaurant: علاقة مع نموذج Restaurant
        products: قائمة المنتجات التابعة للتصنيف
    """

    __tablename__ = "categories"

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
        comment="اسم التصنيف",
    )
    sort_order = Column(
        Integer,
        default=0,
        comment="ترتيب التصنيف",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurant = relationship(
        "Restaurant",
        back_populates="categories",
        lazy="selectin",
        # comment="المطعم",
    )
    products = relationship(
        "Product",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة المنتجات التابعة للتصنيف",
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
        return f"<Category(id={self.id}, name={self.name}, restaurant_id={self.restaurant_id})>"
