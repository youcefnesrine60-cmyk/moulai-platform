# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRIC MODEL
# نموذج مقاييس المطعم
# يدير الإحصائيات والمقاييس الخاصة بكل مطعم
# ==============================================

"""MoulAI operational module for restaurant metric.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship

from .base import BaseModelWithoutId

# ==============================================
# 📊 RESTAURANT METRIC
# ==============================================


class RestaurantMetric(BaseModelWithoutId):
    """
    نموذج مقاييس المطعم - إحصائيات وتحليلات المطعم.

     يدير:
         - عدد المنتجات والتصنيفات
         - عدد الطلبات الشهرية
         - متوسط قيمة الطلب
         - العلاقة مع المطعم

     Attributes:
         restaurant_id: معرف المطعم (Primary Key, ForeignKey)
         products_count: عدد المنتجات
         categories_count: عدد التصنيفات
         monthly_orders: عدد الطلبات الشهرية
         average_order_value: متوسط قيمة الطلب
         restaurant: علاقة مع نموذج Restaurant
    """

    __tablename__ = "restaurant_metrics"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        primary_key=True,
        comment="معرف المطعم (المفتاح الأساسي)",
    )
    products_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="عدد المنتجات",
    )
    categories_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="عدد التصنيفات",
    )
    monthly_orders = Column(
        Integer,
        nullable=False,
        default=0,
        comment="عدد الطلبات الشهرية",
    )
    average_order_value = Column(
        Float,
        nullable=False,
        default=0,
        comment="متوسط قيمة الطلب",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurant = relationship(
        "Restaurant",
        back_populates="metrics",
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
            سلسلة نصية تحتوي على معرف المطعم وعدد الطلبات
        """
        return (
            f"<RestaurantMetric(restaurant_id={self.restaurant_id}, "
            f"orders={self.monthly_orders})>"
        )
