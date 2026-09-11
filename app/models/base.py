# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 BASE MODEL
# النموذج الأساسي لجميع الجداول في قاعدة البيانات
# يوفر حقولاً مشتركة ودوال مساعدة
# ==============================================

from typing import Any, Dict

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    func,
)
from sqlalchemy.orm import DeclarativeBase

# ==============================================
# 🏗️ BASE - تعريف واحد فقط لجميع النماذج SQLAlchemy
# ==============================================

class Base(DeclarativeBase):
    """
    الفئة الأساسية لجميع نماذج SQLAlchemy.
    
    جميع النماذج الجديدة (SQLAlchemy) ترث من هذه الفئة.
    النماذج القديمة (psycopg) تستخدم ملف db.py مؤقتاً.
    """
    pass


# ==============================================
# 🧩 TYPES
# ==============================================

ModelDict = Dict[str, Any]


# ==============================================
# 📦 BASE MODEL (مع id)
# ==============================================

class BaseModel(Base):
    """
    النموذج الأساسي - للجداول التي تحتوي على عمود id.
    
    يوفر:
        - معرف تلقائي (id)
        - طابع زمني للإنشاء (created_at)
        - طابع زمني للتحديث (updated_at)
        - دالة تحويل إلى قاموس (to_dict)
    
    Attributes:
        id: المعرف الرئيسي (Primary Key)
        created_at: تاريخ ووقت الإنشاء
        updated_at: تاريخ ووقت آخر تحديث
    """
    __abstract__ = True
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="المعرف الرئيسي للنموذج",
    )
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="تاريخ ووقت الإنشاء",
    )
    updated_at = Column(
        DateTime,
        onupdate=func.now(),
        server_default=func.now(),
        comment="تاريخ ووقت آخر تحديث",
    )
    
    # ==========================================
    # 🔄 CONVERSION
    # ==========================================
    
    def to_dict(self) -> ModelDict:
        """
        تحويل النموذج إلى قاموس.
        
        Returns:
            قاموس يحتوي على جميع أعمدة النموذج
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


# ==============================================
# 📦 BASE MODEL (بدون id)
# ==============================================

class BaseModelWithoutId(Base):
    """
    النموذج الأساسي - للجداول التي تستخدم مفتاحاً أساسياً مخصصاً.
    
    يوفر:
        - طابع زمني للإنشاء (created_at)
        - طابع زمني للتحديث (updated_at)
        - دالة تحويل إلى قاموس (to_dict)

    Attributes:
        created_at: تاريخ ووقت الإنشاء
        updated_at: تاريخ ووقت آخر تحديث
    """
    __abstract__ = True

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="تاريخ ووقت الإنشاء",
    )
    updated_at = Column(
        DateTime,
        onupdate=func.now(),
        server_default=func.now(),
        comment="تاريخ ووقت آخر تحديث",
    )

    # ==========================================
    # 🔄 CONVERSION
    # ==========================================

    def to_dict(self) -> ModelDict:
        """
        تحويل النموذج إلى قاموس.
        
        Returns:
            قاموس يحتوي على جميع أعمدة النموذج
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "Base",
    "BaseModel",
    "BaseModelWithoutId",
    "ModelDict",
]