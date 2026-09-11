# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎯 PRODUCT OPTION MODEL
# نموذج خيار المنتج الفردي
# يدير الخيارات الفردية للمنتجات مع الأسعار الإضافية
# ==============================================

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
# 🎯 PRODUCT OPTION
# ==============================================

class ProductOption(BaseModel):
    """
    نموذج خيار المنتج الفردي
    
    يدير:
        - اسم الخيار
        - السعر الإضافي
        - حالة التوفر
        - ترتيب العرض
        - العلاقة مع مجموعة الخيارات
    
    Attributes:
        group_id: معرف مجموعة الخيارات (ForeignKey)
        name: اسم الخيار
        extra_price: السعر الإضافي
        is_available: حالة التوفر
        sort_order: ترتيب العرض
        group: علاقة مع نموذج OptionGroup
    """
    __tablename__ = "product_options"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    group_id = Column(
        Integer,
        ForeignKey("option_groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف مجموعة الخيارات",
    )
    name = Column(
        Text,
        nullable=False,
        comment="اسم الخيار",
    )
    extra_price = Column(
        Float,
        default=0,
        comment="السعر الإضافي",
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
    
    group = relationship(
        "OptionGroup",
        back_populates="options",
        lazy="selectin",
        # comment="مجموعة الخيارات",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والاسم والسعر الإضافي
        """
        return f"<ProductOption(id={self.id}, name={self.name}, extra_price={self.extra_price})>"