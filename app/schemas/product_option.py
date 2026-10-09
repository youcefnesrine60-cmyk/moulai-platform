# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎯 PRODUCT OPTION SCHEMAS
# نماذج Pydantic لخيارات المنتج
# تدير التحقق من صحة البيانات وتسلسلها لخيارات المنتج
# ==============================================

"""MoulAI operational module for product option.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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

ProductOptionData = Dict[str, Any]
ProductOptionUpdateData = Dict[str, Any]
ProductOptionList = List["ProductOptionResponse"]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class ProductOptionBase(BaseModel):
    """
    المخطط الأساسي لخيار المنتج.

    يحتوي على الحقول المشتركة بين جميع مخططات خيار المنتج.

    Attributes:
        group_id: معرف مجموعة الخيارات
        name: اسم الخيار
        extra_price: السعر الإضافي
        is_available: حالة التوفر
        sort_order: ترتيب العرض
    """

    group_id: int = Field(
        ...,
        description="معرف مجموعة الخيارات",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    extra_price: float = Field(
        0,
        ge=0,
        description="السعر الإضافي",
        json_schema_extra={"example": 5.00},
    )
    is_available: bool = Field(
        True,
        description="حالة التوفر",
        json_schema_extra={"example": True},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class ProductOptionCreate(BaseModel):
    """
    مخطط إنشاء خيار منتج جديد.

    Attributes:
        name: اسم الخيار
        extra_price: السعر الإضافي (اختياري)
        is_available: حالة التوفر (اختياري)
        sort_order: ترتيب العرض (اختياري)
    """

    name: str = Field(
        ...,
        max_length=255,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    extra_price: float = Field(
        0,
        ge=0,
        description="السعر الإضافي",
        json_schema_extra={"example": 5.00},
    )
    is_available: bool = Field(
        True,
        description="حالة التوفر",
        json_schema_extra={"example": True},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class ProductOptionUpdate(BaseModel):
    """
    مخطط تحديث خيار المنتج - جميع الحقول اختيارية.

    Attributes:
        name: اسم الخيار
        extra_price: السعر الإضافي
        is_available: حالة التوفر
        sort_order: ترتيب العرض
    """

    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    extra_price: Optional[float] = Field(
        None,
        ge=0,
        description="السعر الإضافي",
        json_schema_extra={"example": 5.00},
    )
    is_available: Optional[bool] = Field(
        None,
        description="حالة التوفر",
        json_schema_extra={"example": True},
    )
    sort_order: Optional[int] = Field(
        None,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📤 AVAILABILITY UPDATE SCHEMA
# ==============================================


class ProductOptionAvailabilityUpdate(BaseModel):
    """
    مخطط تحديث حالة توفر خيار المنتج.

    Attributes:
        is_available: حالة التوفر الجديدة
    """

    is_available: bool = Field(
        ...,
        description="حالة التوفر الجديدة",
        json_schema_extra={"example": False},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class ProductOptionResponse(ProductOptionBase):
    """
    مخطط استجابة خيار المنتج - يحتوي على جميع الحقول بما فيها التواريخ.

    Attributes:
        id: معرف الخيار
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الخيار",
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
# 📋 PRODUCT OPTION LIST RESPONSE
# ==============================================


class ProductOptionListResponse(BaseModel):
    """
    مخطط استجابة قائمة خيارات المنتج.

    Attributes:
        items: قائمة الخيارات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: ProductOptionList = Field(
        ...,
        description="قائمة الخيارات",
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
# 📊 PRODUCT OPTION SUMMARY
# ==============================================


class ProductOptionSummary(BaseModel):
    """
    مخطط ملخص خيارات المنتج.

    Attributes:
        group_id: معرف مجموعة الخيارات
        total_options: إجمالي عدد الخيارات
        available_options: عدد الخيارات المتاحة
        unavailable_options: عدد الخيارات غير المتاحة
        total_extra_price: إجمالي السعر الإضافي
        avg_extra_price: متوسط السعر الإضافي
        min_extra_price: أقل سعر إضافي
        max_extra_price: أعلى سعر إضافي
    """

    model_config = ConfigDict(from_attributes=True)

    group_id: int = Field(
        ...,
        description="معرف مجموعة الخيارات",
        json_schema_extra={"example": 1},
    )
    total_options: int = Field(
        ...,
        description="إجمالي عدد الخيارات",
        json_schema_extra={"example": 5},
    )
    available_options: int = Field(
        ...,
        description="عدد الخيارات المتاحة",
        json_schema_extra={"example": 4},
    )
    unavailable_options: int = Field(
        ...,
        description="عدد الخيارات غير المتاحة",
        json_schema_extra={"example": 1},
    )
    total_extra_price: float = Field(
        ...,
        description="إجمالي السعر الإضافي",
        json_schema_extra={"example": 15.00},
    )
    avg_extra_price: float = Field(
        ...,
        description="متوسط السعر الإضافي",
        json_schema_extra={"example": 3.00},
    )
    min_extra_price: float = Field(
        ...,
        description="أقل سعر إضافي",
        json_schema_extra={"example": 0},
    )
    max_extra_price: float = Field(
        ...,
        description="أعلى سعر إضافي",
        json_schema_extra={"example": 5.00},
    )


# ==============================================
# ✅ PRODUCT OPTION VALIDATION
# ==============================================


class ProductOptionValidation(BaseModel):
    """
    مخطط التحقق من صحة خيار المنتج.

    Attributes:
        is_valid: هل الخيار صالح
        errors: قائمة الأخطاء
        warnings: قائمة التحذيرات
    """

    model_config = ConfigDict(from_attributes=True)

    is_valid: bool = Field(
        ...,
        description="هل الخيار صالح",
        json_schema_extra={"example": True},
    )
    errors: List[str] = Field(
        default_factory=list,
        description="قائمة الأخطاء",
        json_schema_extra={"example": ["الاسم مطلوب"]},
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="قائمة التحذيرات",
        json_schema_extra={"example": ["السعر الإضافي مرتفع مقارنة بالمنتجات الأخرى"]},
    )


# ==============================================
# 📊 BULK PRODUCT OPTION CREATE
# ==============================================


class ProductOptionBulkCreate(BaseModel):
    """
    مخطط إنشاء عدة خيارات دفعة واحدة.

    Attributes:
        group_id: معرف مجموعة الخيارات
        options: قائمة الخيارات
    """

    group_id: int = Field(
        ...,
        description="معرف مجموعة الخيارات",
        json_schema_extra={"example": 1},
    )
    options: List[ProductOptionCreate] = Field(
        ...,
        description="قائمة الخيارات",
        min_length=1,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "ProductOptionBase",
    "ProductOptionCreate",
    "ProductOptionUpdate",
    "ProductOptionAvailabilityUpdate",
    "ProductOptionResponse",
    "ProductOptionListResponse",
    "ProductOptionSummary",
    "ProductOptionValidation",
    "ProductOptionBulkCreate",
    "ProductOptionData",
    "ProductOptionUpdateData",
    "ProductOptionList",
]
