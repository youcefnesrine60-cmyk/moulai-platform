# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎯 OPTION GROUP MODEL
# نموذج مجموعة خيارات المنتج
# يدير مجموعات الخيارات للمنتجات مع إعداداتها
# ==============================================

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🎯 OPTION GROUP
# ==============================================

class OptionGroup(BaseModel):
    """
    نموذج مجموعة خيارات المنتج
    
    يدير:
        - اسم مجموعة الخيارات
        - إلزامية الاختيار
        - إمكانية اختيار عدة خيارات
        - ترتيب العرض
        - العلاقات مع المنتج والخيارات
    
    Attributes:
        product_id: معرف المنتج (ForeignKey)
        name: اسم مجموعة الخيارات
        required: هل الاختيار إلزامي
        multiple_choice: هل يمكن اختيار عدة خيارات
        sort_order: ترتيب العرض
        product: علاقة مع نموذج Product
        options: قائمة الخيارات التابعة للمجموعة
    """
    __tablename__ = "option_groups"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المنتج",
    )
    name = Column(
        Text,
        nullable=False,
        comment="اسم مجموعة الخيارات",
    )
    required = Column(
        Boolean,
        default=False,
        comment="هل الاختيار إلزامي",
    )
    multiple_choice = Column(
        Boolean,
        default=False,
        comment="هل يمكن اختيار عدة خيارات",
    )
    sort_order = Column(
        Integer,
        default=0,
        comment="ترتيب العرض",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    product = relationship(
        "Product",
        back_populates="option_groups",
        lazy="selectin",
        # comment="المنتج",
    )
    options = relationship(
        "ProductOption",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة الخيارات التابعة للمجموعة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والاسم ومعرف المنتج
        """
        return f"<OptionGroup(id={self.id}, name={self.name}, product_id={self.product_id})>"