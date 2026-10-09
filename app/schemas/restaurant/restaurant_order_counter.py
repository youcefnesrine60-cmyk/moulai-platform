# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER SCHEMAS
# نماذج Pydantic لعداد طلبات المطعم
# تدير التحقق من صحة البيانات وتسلسلها لعداد طلبات المطعم
# ==============================================

"""MoulAI operational module for restaurant order counter.

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

OrderCounterData = Dict[str, Any]
OrderCounterUpdateData = Dict[str, Any]
OrderCounterListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class RestaurantOrderCounterBase(BaseModel):
    """
    المخطط الأساسي لعداد طلبات المطعم.

    يحتوي على الحقول المشتركة بين جميع مخططات عداد طلبات المطعم.

    Attributes:
        restaurant_id: معرف المطعم
        last_number: آخر رقم طلب
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    last_number: int = Field(
        0,
        ge=0,
        description="آخر رقم طلب",
        json_schema_extra={"example": 42},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class RestaurantOrderCounterCreate(BaseModel):
    """
    مخطط إنشاء عداد طلبات مطعم جديد.

    Attributes:
        restaurant_id: معرف المطعم
        last_number: آخر رقم طلب (اختياري)
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    last_number: Optional[int] = Field(
        0,
        ge=0,
        description="آخر رقم طلب (افتراضي: 0)",
        json_schema_extra={"example": 0},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class RestaurantOrderCounterUpdate(BaseModel):
    """
    مخطط تحديث عداد طلبات المطعم.

    Attributes:
        last_number: آخر رقم طلب
    """

    last_number: Optional[int] = Field(
        None,
        ge=0,
        description="آخر رقم طلب",
        json_schema_extra={"example": 42},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class RestaurantOrderCounterResponse(RestaurantOrderCounterBase):
    """
    مخطط استجابة عداد طلبات المطعم - يحتوي على جميع الحقول بما فيها التواريخ.

    Attributes:
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )
    updated_at: datetime = Field(
        ...,
        description="تاريخ آخر تحديث",
    )


# ==============================================
# 📋 LIST RESPONSE
# ==============================================


class RestaurantOrderCounterListResponse(BaseModel):
    """
    مخطط استجابة قائمة عدادات طلبات المطعم.

    يحتوي على قائمة عدادات طلبات المطعم مع معلومات الترقيم.

    Attributes:
        items: قائمة عدادات طلبات المطعم
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[RestaurantOrderCounterResponse] = Field(
        ...,
        description="قائمة عدادات طلبات المطعم",
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
# 🔢 NEXT ORDER NUMBER RESPONSE
# ==============================================


class NextOrderNumberResponse(BaseModel):
    """
    مخطط استجابة رقم الطلب التالي.

    Attributes:
        restaurant_id: معرف المطعم
        order_number: رقم الطلب الجديد
        sequence: رقم التسلسل
        previous_number: الرقم السابق
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    order_number: str = Field(
        ...,
        description="رقم الطلب الجديد",
        json_schema_extra={"example": "RST1-000043"},
    )
    sequence: int = Field(
        ...,
        description="رقم التسلسل",
        json_schema_extra={"example": 43},
        ge=0,
    )
    previous_number: int = Field(
        ...,
        description="الرقم السابق",
        json_schema_extra={"example": 42},
        ge=0,
    )


# ==============================================
# 📊 ORDER COUNTER SUMMARY
# ==============================================


class OrderCounterSummary(BaseModel):
    """
    مخطط ملخص عداد طلبات المطعم.

    Attributes:
        restaurant_id: معرف المطعم
        total_orders: إجمالي عدد الطلبات
        last_order_number: آخر رقم طلب
        next_order_number: رقم الطلب التالي
        orders_today: عدد الطلبات اليوم
        orders_this_month: عدد الطلبات هذا الشهر
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    total_orders: int = Field(
        ...,
        description="إجمالي عدد الطلبات",
        json_schema_extra={"example": 43},
        ge=0,
    )
    last_order_number: str = Field(
        ...,
        description="آخر رقم طلب",
        json_schema_extra={"example": "RST1-000043"},
    )
    next_order_number: str = Field(
        ...,
        description="رقم الطلب التالي",
        json_schema_extra={"example": "RST1-000044"},
    )
    orders_today: int = Field(
        0,
        description="عدد الطلبات اليوم",
        json_schema_extra={"example": 5},
        ge=0,
    )
    orders_this_month: int = Field(
        0,
        description="عدد الطلبات هذا الشهر",
        json_schema_extra={"example": 30},
        ge=0,
    )


# ==============================================
# 📈 ORDER NUMBER FORMAT
# ==============================================


class OrderNumberFormat(BaseModel):
    """
    مخطط تنسيق رقم الطلب.

    Attributes:
        restaurant_id: معرف المطعم
        prefix: بادئة رقم الطلب
        sequence: رقم التسلسل
        format: تنسيق رقم الطلب
        example: مثال على رقم الطلب
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    prefix: str = Field(
        ...,
        description="بادئة رقم الطلب",
        json_schema_extra={"example": "RST1-"},
    )
    sequence: int = Field(
        ...,
        description="رقم التسلسل",
        json_schema_extra={"example": 43},
        ge=0,
    )
    format: str = Field(
        ...,
        description="تنسيق رقم الطلب",
        json_schema_extra={"example": "RST{restaurant_id}-{sequence:06d}"},
    )
    example: str = Field(
        ...,
        description="مثال على رقم الطلب",
        json_schema_extra={"example": "RST1-000043"},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Restaurant Order Counter
    "RestaurantOrderCounterBase",
    "RestaurantOrderCounterCreate",
    "RestaurantOrderCounterUpdate",
    "RestaurantOrderCounterResponse",
    "RestaurantOrderCounterListResponse",
    # Next Order Number Response
    "NextOrderNumberResponse",
    # Order Counter Summary
    "OrderCounterSummary",
    # Order Number Format
    "OrderNumberFormat",
    # Types
    "OrderCounterData",
    "OrderCounterUpdateData",
    "OrderCounterListData",
]
