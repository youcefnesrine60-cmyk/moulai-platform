# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 PRODUCT MODEL
# نموذج المنتج
# يدير منتجات المطاعم وأسعارها وخياراتها
# ==============================================

"""MoulAI operational module for product.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 📦 PRODUCT
# ==============================================


class Product(BaseModel):
    """
    نموذج المنتج

    يدير:
        - البيانات الأساسية للمنتج (الاسم، الوصف، السعر)
        - صورة المنتج
        - حالة التوفر
        - ترتيب العرض
        - العلاقات مع المطعم والتصنيف ومجموعات الخيارات وبنود الطلب

    Attributes:
        restaurant_id: معرف المطعم (ForeignKey)
        category_id: معرف التصنيف (ForeignKey)
        name: اسم المنتج
        description: وصف المنتج
        price: سعر المنتج
        image_url: رابط صورة المنتج
        is_available: حالة التوفر
        sort_order: ترتيب العرض
        restaurant: علاقة مع نموذج Restaurant
        category: علاقة مع نموذج Category
        option_groups: قائمة مجموعات الخيارات
        order_items: قائمة بنود الطلب
    """

    __tablename__ = "products"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف التصنيف",
    )
    name = Column(
        Text,
        nullable=False,
        comment="اسم المنتج",
    )
    description = Column(
        Text,
        comment="وصف المنتج",
    )
    price = Column(
        Float,
        nullable=False,
        comment="سعر المنتج",
    )
    image_url = Column(
        Text,
        comment="رابط صورة المنتج",
    )
    is_available = Column(
        Boolean,
        default=True,
        comment="حالة التوفر",
    )
    sort_order = Column(
        Integer,
        default=0,
        comment="ترتيب العرض",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurant = relationship(
        "Restaurant",
        back_populates="products",
        lazy="selectin",
        # comment="المطعم",
    )
    category = relationship(
        "Category",
        back_populates="products",
        lazy="selectin",
        # comment="التصنيف",
    )
    option_groups = relationship(
        "OptionGroup",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة مجموعات الخيارات",
    )
    order_items = relationship(
        "OrderItem",
        back_populates="product",
        lazy="selectin",
        # comment="قائمة بنود الطلب",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف والاسم والسعر
        """
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"
