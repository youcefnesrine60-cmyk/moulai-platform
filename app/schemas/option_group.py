# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎛 OPTION GROUP SCHEMAS
# نماذج Pydantic لمجموعات الخيارات
# تدير التحقق من صحة البيانات وتسلسلها لمجموعات الخيارات
# ==============================================

"""MoulAI operational module for option group.

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

OptionGroupData = Dict[str, Any]
OptionGroupUpdateData = Dict[str, Any]
OptionGroupListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class OptionGroupBase(BaseModel):
    """
    المخطط الأساسي لمجموعة الخيارات.

    Attributes:
        product_id: معرف المنتج
        name: اسم مجموعة الخيارات
        required: هل المجموعة إجبارية
        multiple_choice: هل يسمح باختيار متعدد
        sort_order: ترتيب العرض
    """

    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم مجموعة الخيارات",
        json_schema_extra={"example": "حجم البيتزا"},
    )
    required: bool = Field(
        False,
        description="هل المجموعة إجبارية",
        json_schema_extra={"example": True},
    )
    multiple_choice: bool = Field(
        False,
        description="هل يسمح باختيار متعدد",
        json_schema_extra={"example": False},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class OptionGroupCreate(BaseModel):
    """
    مخطط إنشاء مجموعة خيارات جديدة.

    Attributes:
        product_id: معرف المنتج
        name: اسم مجموعة الخيارات
        required: هل المجموعة إجبارية
        multiple_choice: هل يسمح باختيار متعدد
        sort_order: ترتيب العرض
    """

    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم مجموعة الخيارات",
        json_schema_extra={"example": "حجم البيتزا"},
    )
    required: bool = Field(
        False,
        description="هل المجموعة إجبارية",
        json_schema_extra={"example": True},
    )
    multiple_choice: bool = Field(
        False,
        description="هل يسمح باختيار متعدد",
        json_schema_extra={"example": False},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class OptionGroupUpdate(BaseModel):
    """
    مخطط تحديث مجموعة خيارات.

    Attributes:
        name: اسم مجموعة الخيارات الجديد
        required: هل المجموعة إجبارية
        multiple_choice: هل يسمح باختيار متعدد
        sort_order: ترتيب العرض الجديد
    """

    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم مجموعة الخيارات الجديد",
        json_schema_extra={"example": "حجم البيتزا"},
    )
    required: Optional[bool] = Field(
        None,
        description="هل المجموعة إجبارية",
        json_schema_extra={"example": False},
    )
    multiple_choice: Optional[bool] = Field(
        None,
        description="هل يسمح باختيار متعدد",
        json_schema_extra={"example": True},
    )
    sort_order: Optional[int] = Field(
        None,
        description="ترتيب العرض الجديد",
        json_schema_extra={"example": 2},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class OptionGroupResponse(OptionGroupBase):
    """
    مخطط استجابة مجموعة الخيارات.

    Attributes:
        id: معرف مجموعة الخيارات
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف مجموعة الخيارات",
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
# 🎯 OPTION GROUP WITH OPTIONS
# ==============================================


class ProductOptionResponse(BaseModel):
    """
    مخطط استجابة خيار المنتج.

    Attributes:
        id: معرف الخيار
        name: اسم الخيار
        extra_price: السعر الإضافي
        is_available: حالة التوفر
        sort_order: ترتيب العرض
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الخيار",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    extra_price: float = Field(
        ...,
        description="السعر الإضافي",
        json_schema_extra={"example": 200.00},
    )
    is_available: bool = Field(
        ...,
        description="حالة التوفر",
        json_schema_extra={"example": True},
    )
    sort_order: int = Field(
        ...,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


class OptionGroupWithOptionsResponse(OptionGroupResponse):
    """
    مخطط استجابة مجموعة الخيارات مع خياراتها.

    Attributes:
        options: قائمة خيارات المنتج
    """

    model_config = ConfigDict(from_attributes=True)

    options: List[ProductOptionResponse] = Field(
        default_factory=list,
        description="خيارات المنتج",
    )


# ==============================================
# 📋 LIST RESPONSE
# ==============================================


class OptionGroupListResponse(BaseModel):
    """
    مخطط استجابة قائمة مجموعات الخيارات.

    Attributes:
        items: قائمة مجموعات الخيارات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[OptionGroupResponse] = Field(
        ...,
        description="قائمة مجموعات الخيارات",
    )
    total: int = Field(
        ...,
        description="العدد الإجمالي",
        json_schema_extra={"example": 10},
        ge=0,
    )
    skip: int = Field(
        ...,
        description="عدد السجلات المتخطية",
        json_schema_extra={"example": 0},
        ge=0,
    )
    limit: int = Field(
        ...,
        description="الحد الأقصى للسجلات",
        json_schema_extra={"example": 100},
        ge=1,
    )


# ==============================================
# 📊 SUMMARY
# ==============================================


class OptionGroupSummary(BaseModel):
    """
    مخطط ملخص مجموعات الخيارات.

    Attributes:
        product_id: معرف المنتج
        total_groups: إجمالي عدد المجموعات
        required_groups: عدد المجموعات الإجبارية
        optional_groups: عدد المجموعات الاختيارية
        total_options: إجمالي عدد الخيارات
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    total_groups: int = Field(
        ...,
        description="إجمالي عدد المجموعات",
        json_schema_extra={"example": 5},
        ge=0,
    )
    required_groups: int = Field(
        ...,
        description="عدد المجموعات الإجبارية",
        json_schema_extra={"example": 3},
        ge=0,
    )
    optional_groups: int = Field(
        ...,
        description="عدد المجموعات الاختيارية",
        json_schema_extra={"example": 2},
        ge=0,
    )
    total_options: int = Field(
        ...,
        description="إجمالي عدد الخيارات",
        json_schema_extra={"example": 15},
        ge=0,
    )


# ==============================================
# ✅ VALIDATION
# ==============================================


class OptionGroupValidation(BaseModel):
    """
    مخطط التحقق من صحة مجموعة الخيارات.

    Attributes:
        product_id: معرف المنتج
        name: اسم مجموعة الخيارات
        required: هل المجموعة إجبارية
        multiple_choice: هل يسمح باختيار متعدد
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم مجموعة الخيارات",
        json_schema_extra={"example": "حجم البيتزا"},
    )
    required: bool = Field(
        False,
        description="هل المجموعة إجبارية",
        json_schema_extra={"example": True},
    )
    multiple_choice: bool = Field(
        False,
        description="هل يسمح باختيار متعدد",
        json_schema_extra={"example": False},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "OptionGroupBase",
    "OptionGroupCreate",
    "OptionGroupUpdate",
    "OptionGroupResponse",
    "ProductOptionResponse",
    "OptionGroupWithOptionsResponse",
    "OptionGroupListResponse",
    "OptionGroupSummary",
    "OptionGroupValidation",
    "OptionGroupData",
    "OptionGroupUpdateData",
    "OptionGroupListData",
]
