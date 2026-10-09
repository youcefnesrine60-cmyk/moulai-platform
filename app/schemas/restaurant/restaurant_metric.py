# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRIC SCHEMAS
# نماذج Pydantic لمقاييس المطعم
# تدير التحقق من صحة البيانات وتسلسلها لمقاييس المطعم
# ==============================================

"""MoulAI operational module for restaurant metric.

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

RestaurantMetricData = Dict[str, Any]
RestaurantMetricUpdateData = Dict[str, Any]
RestaurantMetricListData = List[Dict[str, Any]]
MetricsTrendList = List["MetricsTrendPoint"]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class RestaurantMetricBase(BaseModel):
    """
    المخطط الأساسي لمقاييس المطعم.

    يحتوي على الحقول المشتركة بين جميع مخططات مقاييس المطعم.

    Attributes:
        restaurant_id: معرف المطعم
        products_count: عدد المنتجات
        categories_count: عدد التصنيفات
        monthly_orders: عدد الطلبات الشهرية
        average_order_value: متوسط قيمة الطلب
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    products_count: int = Field(
        0,
        ge=0,
        description="عدد المنتجات",
        json_schema_extra={"example": 10},
    )
    categories_count: int = Field(
        0,
        ge=0,
        description="عدد التصنيفات",
        json_schema_extra={"example": 5},
    )
    monthly_orders: int = Field(
        0,
        ge=0,
        description="عدد الطلبات الشهرية",
        json_schema_extra={"example": 50},
    )
    average_order_value: float = Field(
        0,
        ge=0,
        description="متوسط قيمة الطلب",
        json_schema_extra={"example": 100.00},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class RestaurantMetricCreate(BaseModel):
    """
    مخطط إنشاء مقاييس مطعم جديدة.

    Attributes:
        restaurant_id: معرف المطعم
        products_count: عدد المنتجات (اختياري)
        categories_count: عدد التصنيفات (اختياري)
        monthly_orders: عدد الطلبات الشهرية (اختياري)
        average_order_value: متوسط قيمة الطلب (اختياري)
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    products_count: Optional[int] = Field(
        0,
        ge=0,
        description="عدد المنتجات",
        json_schema_extra={"example": 0},
    )
    categories_count: Optional[int] = Field(
        0,
        ge=0,
        description="عدد التصنيفات",
        json_schema_extra={"example": 0},
    )
    monthly_orders: Optional[int] = Field(
        0,
        ge=0,
        description="عدد الطلبات الشهرية",
        json_schema_extra={"example": 0},
    )
    average_order_value: Optional[float] = Field(
        0,
        ge=0,
        description="متوسط قيمة الطلب",
        json_schema_extra={"example": 0.0},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class RestaurantMetricUpdate(BaseModel):
    """
    مخطط تحديث مقاييس المطعم - جميع الحقول اختيارية.

    Attributes:
        products_count: عدد المنتجات
        categories_count: عدد التصنيفات
        monthly_orders: عدد الطلبات الشهرية
        average_order_value: متوسط قيمة الطلب
    """

    products_count: Optional[int] = Field(
        None,
        ge=0,
        description="عدد المنتجات",
        json_schema_extra={"example": 10},
    )
    categories_count: Optional[int] = Field(
        None,
        ge=0,
        description="عدد التصنيفات",
        json_schema_extra={"example": 5},
    )
    monthly_orders: Optional[int] = Field(
        None,
        ge=0,
        description="عدد الطلبات الشهرية",
        json_schema_extra={"example": 50},
    )
    average_order_value: Optional[float] = Field(
        None,
        ge=0,
        description="متوسط قيمة الطلب",
        json_schema_extra={"example": 100.00},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class RestaurantMetricResponse(RestaurantMetricBase):
    """
    مخطط استجابة مقاييس المطعم - يحتوي على جميع الحقول بما فيها التواريخ.

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


class RestaurantMetricListResponse(BaseModel):
    """
    مخطط استجابة قائمة مقاييس المطعم.

    يحتوي على قائمة مقاييس المطعم مع معلومات الترقيم.

    Attributes:
        items: قائمة مقاييس المطعم
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[RestaurantMetricResponse] = Field(
        ...,
        description="قائمة مقاييس المطعم",
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
# 📊 METRICS SUMMARY
# ==============================================


class RestaurantMetricSummary(BaseModel):
    """
    مخطط ملخص مقاييس المطعم.

    Attributes:
        restaurant_id: معرف المطعم
        total_products: إجمالي عدد المنتجات
        total_categories: إجمالي عدد التصنيفات
        total_orders: إجمالي عدد الطلبات
        avg_order_value: متوسط قيمة الطلب
        monthly_growth: معدل النمو الشهري (بالنسبة المئوية)
        products_per_category: متوسط عدد المنتجات لكل تصنيف
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    total_products: int = Field(
        ...,
        description="إجمالي عدد المنتجات",
        json_schema_extra={"example": 10},
        ge=0,
    )
    total_categories: int = Field(
        ...,
        description="إجمالي عدد التصنيفات",
        json_schema_extra={"example": 5},
        ge=0,
    )
    total_orders: int = Field(
        ...,
        description="إجمالي عدد الطلبات",
        json_schema_extra={"example": 50},
        ge=0,
    )
    avg_order_value: float = Field(
        ...,
        description="متوسط قيمة الطلب",
        json_schema_extra={"example": 100.00},
        ge=0,
    )
    monthly_growth: Optional[float] = Field(
        None,
        description="معدل النمو الشهري (بالنسبة المئوية)",
        json_schema_extra={"example": 10.5},
    )
    products_per_category: float = Field(
        ...,
        description="متوسط عدد المنتجات لكل تصنيف",
        json_schema_extra={"example": 2.0},
        ge=0,
    )


# ==============================================
# 📈 METRICS TREND
# ==============================================


class MetricsTrendPoint(BaseModel):
    """
    مخطط نقطة اتجاه المقاييس.

    Attributes:
        period: الفترة (شهر/أسبوع/يوم)
        orders_count: عدد الطلبات
        revenue: الإيرادات
        avg_order_value: متوسط قيمة الطلب
    """

    model_config = ConfigDict(from_attributes=True)

    period: str = Field(
        ...,
        description="الفترة",
        json_schema_extra={"example": "2026-08"},
    )
    orders_count: int = Field(
        ...,
        description="عدد الطلبات",
        json_schema_extra={"example": 50},
        ge=0,
    )
    revenue: float = Field(
        ...,
        description="الإيرادات",
        json_schema_extra={"example": 5000.00},
        ge=0,
    )
    avg_order_value: float = Field(
        ...,
        description="متوسط قيمة الطلب",
        json_schema_extra={"example": 100.00},
        ge=0,
    )


class MetricsTrend(BaseModel):
    """
    مخطط اتجاه المقاييس.

    Attributes:
        restaurant_id: معرف المطعم
        trend: قائمة نقاط الاتجاه
        total_orders: إجمالي عدد الطلبات
        total_revenue: إجمالي الإيرادات
        overall_avg: المتوسط العام
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    trend: MetricsTrendList = Field(
        default_factory=list,
        description="قائمة نقاط الاتجاه",
    )
    total_orders: int = Field(
        ...,
        description="إجمالي عدد الطلبات",
        json_schema_extra={"example": 50},
        ge=0,
    )
    total_revenue: float = Field(
        ...,
        description="إجمالي الإيرادات",
        json_schema_extra={"example": 5000.00},
        ge=0,
    )
    overall_avg: float = Field(
        ...,
        description="المتوسط العام",
        json_schema_extra={"example": 100.00},
        ge=0,
    )


# ==============================================
# 📊 PRODUCT METRICS
# ==============================================


class ProductMetrics(BaseModel):
    """
    مخطط مقاييس المنتجات.

    Attributes:
        restaurant_id: معرف المطعم
        total_products: إجمالي عدد المنتجات
        available_products: عدد المنتجات المتاحة
        unavailable_products: عدد المنتجات غير المتاحة
        most_expensive: أعلى سعر منتج
        least_expensive: أقل سعر منتج
        avg_price: متوسط السعر
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    total_products: int = Field(
        ...,
        description="إجمالي عدد المنتجات",
        json_schema_extra={"example": 10},
        ge=0,
    )
    available_products: int = Field(
        ...,
        description="عدد المنتجات المتاحة",
        json_schema_extra={"example": 8},
        ge=0,
    )
    unavailable_products: int = Field(
        ...,
        description="عدد المنتجات غير المتاحة",
        json_schema_extra={"example": 2},
        ge=0,
    )
    most_expensive: float = Field(
        ...,
        description="أعلى سعر منتج",
        json_schema_extra={"example": 50.00},
        ge=0,
    )
    least_expensive: float = Field(
        ...,
        description="أقل سعر منتج",
        json_schema_extra={"example": 10.00},
        ge=0,
    )
    avg_price: float = Field(
        ...,
        description="متوسط السعر",
        json_schema_extra={"example": 25.00},
        ge=0,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Restaurant Metric
    "RestaurantMetricBase",
    "RestaurantMetricCreate",
    "RestaurantMetricUpdate",
    "RestaurantMetricResponse",
    "RestaurantMetricListResponse",
    "RestaurantMetricSummary",
    # Metrics Trend
    "MetricsTrendPoint",
    "MetricsTrend",
    # Product Metrics
    "ProductMetrics",
    # Types
    "RestaurantMetricData",
    "RestaurantMetricUpdateData",
    "RestaurantMetricListData",
]
