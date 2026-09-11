# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 BRANCH SCHEMAS
# نماذج Pydantic للفروع
# تدير التحقق من صحة البيانات وتسلسلها للفروع
# ==============================================

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# ==============================================
# 🧩 TYPES
# ==============================================

BranchData = Dict[str, Any]
BranchUpdateData = Dict[str, Any]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class BranchBase(BaseModel):
    """
    المخطط الأساسي للفرع.
    
    يحتوي على الحقول المشتركة بين جميع مخططات الفرع.
    
    Attributes:
        restaurant_id: معرف المطعم
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        is_active: حالة النشاط
    """
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم الفرع",
        json_schema_extra={"example": "الفرع الرئيسي"},
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم الهاتف",
        json_schema_extra={"example": "0555123456"},
    )
    wilaya: Optional[str] = Field(
        None,
        max_length=100,
        description="الولاية",
        json_schema_extra={"example": "Alger"},
    )
    lat: Optional[float] = Field(
        None,
        description="خط العرض",
        json_schema_extra={"example": 36.7538},
    )
    lng: Optional[float] = Field(
        None,
        description="خط الطول",
        json_schema_extra={"example": 3.0588},
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class BranchCreate(BaseModel):
    """
    مخطط إنشاء فرع جديد.
    
    Attributes:
        name: اسم الفرع
        phone: رقم الهاتف (اختياري)
        wilaya: الولاية (اختياري)
        lat: خط العرض (اختياري)
        lng: خط الطول (اختياري)
    """
    name: str = Field(
        ...,
        max_length=255,
        description="اسم الفرع",
        json_schema_extra={"example": "الفرع الرئيسي"},
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم الهاتف",
        json_schema_extra={"example": "0555123456"},
    )
    wilaya: Optional[str] = Field(
        None,
        max_length=100,
        description="الولاية",
        json_schema_extra={"example": "Alger"},
    )
    lat: Optional[float] = Field(
        None,
        description="خط العرض",
        json_schema_extra={"example": 36.7538},
    )
    lng: Optional[float] = Field(
        None,
        description="خط الطول",
        json_schema_extra={"example": 3.0588},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class BranchUpdate(BaseModel):
    """
    مخطط تحديث الفرع - جميع الحقول اختيارية.
    
    Attributes:
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        is_active: حالة النشاط
    """
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم الفرع",
        json_schema_extra={"example": "الفرع الرئيسي"},
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم الهاتف",
        json_schema_extra={"example": "0555123456"},
    )
    wilaya: Optional[str] = Field(
        None,
        max_length=100,
        description="الولاية",
        json_schema_extra={"example": "Alger"},
    )
    lat: Optional[float] = Field(
        None,
        description="خط العرض",
        json_schema_extra={"example": 36.7538},
    )
    lng: Optional[float] = Field(
        None,
        description="خط الطول",
        json_schema_extra={"example": 3.0588},
    )
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )


# ==============================================
# 📤 STATUS UPDATE SCHEMA
# ==============================================

class BranchStatusUpdate(BaseModel):
    """
    مخطط تحديث حالة الفرع.
    
    Attributes:
        is_active: حالة النشاط الجديدة
    """
    is_active: bool = Field(
        ...,
        description="حالة النشاط الجديدة",
        json_schema_extra={"example": False},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class BranchResponse(BranchBase):
    """
    مخطط استجابة الفرع - يحتوي على جميع الحقول بما فيها التواريخ.
    
    Attributes:
        id: معرف الفرع
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الفرع",
        json_schema_extra={"example": 1},
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )
    updated_at: datetime = Field(
        ...,
        description="تاريخ آخر تحديث",
    )


# ==============================================
# 📋 BRANCH LIST RESPONSE
# ==============================================

class BranchListResponse(BaseModel):
    """
    مخطط استجابة قائمة الفروع.
    
    يحتوي على قائمة الفروع مع معلومات الترقيم.
    
    Attributes:
        items: قائمة الفروع
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[BranchResponse] = Field(
        ...,
        description="قائمة الفروع",
    )
    total: int = Field(
        ...,
        description="العدد الإجمالي",
        json_schema_extra={"example": 10},
    )
    skip: int = Field(
        ...,
        description="عدد السجلات المتخطية",
        json_schema_extra={"example": 0},
    )
    limit: int = Field(
        ...,
        description="الحد الأقصى للسجلات",
        json_schema_extra={"example": 100},
    )


# ==============================================
# 📊 BRANCH SUMMARY
# ==============================================

class BranchSummary(BaseModel):
    """
    مخطط ملخص الفروع.
    
    يحتوي على إحصائيات موجزة عن الفروع.
    
    Attributes:
        total_branches: إجمالي عدد الفروع
        active_branches: عدد الفروع النشطة
        inactive_branches: عدد الفروع غير النشطة
        total_cost: التكلفة الإجمالية للفروع
        branches_per_wilaya: توزيع الفروع حسب الولاية
    """
    model_config = ConfigDict(from_attributes=True)

    total_branches: int = Field(
        ...,
        description="إجمالي عدد الفروع",
        json_schema_extra={"example": 10},
    )
    active_branches: int = Field(
        ...,
        description="عدد الفروع النشطة",
        json_schema_extra={"example": 8},
    )
    inactive_branches: int = Field(
        ...,
        description="عدد الفروع غير النشطة",
        json_schema_extra={"example": 2},
    )
    total_cost: float = Field(
        ...,
        description="التكلفة الإجمالية للفروع",
        json_schema_extra={"example": 500.00},
    )
    branches_per_wilaya: Dict[str, int] = Field(
        default_factory=dict,
        description="توزيع الفروع حسب الولاية",
        json_schema_extra={"example": {"Alger": 5, "Oran": 3, "Constantine": 2}},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "BranchBase",
    "BranchCreate",
    "BranchUpdate",
    "BranchStatusUpdate",
    "BranchResponse",
    "BranchListResponse",
    "BranchSummary",
    "BranchData",
    "BranchUpdateData",
]