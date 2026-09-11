# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📂 CATEGORY SCHEMAS
# نماذج Pydantic للتصنيفات
# تدير التحقق من صحة البيانات وتسلسلها للتصنيفات
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

CategoryData = Dict[str, Any]
CategoryUpdateData = Dict[str, Any]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class CategoryBase(BaseModel):
    """
    المخطط الأساسي للتصنيف.
    
    يحتوي على الحقول المشتركة بين جميع مخططات التصنيف.
    
    Attributes:
        restaurant_id: معرف المطعم
        name: اسم التصنيف
        sort_order: ترتيب العرض
    """
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم التصنيف",
        json_schema_extra={"example": "بيتزا"},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class CategoryCreate(BaseModel):
    """
    مخطط إنشاء تصنيف جديد.
    
    Attributes:
        name: اسم التصنيف
        sort_order: ترتيب العرض (اختياري)
    """
    name: str = Field(
        ...,
        max_length=255,
        description="اسم التصنيف",
        json_schema_extra={"example": "بيتزا"},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class CategoryUpdate(BaseModel):
    """
    مخطط تحديث التصنيف - جميع الحقول اختيارية.
    
    Attributes:
        name: اسم التصنيف
        sort_order: ترتيب العرض
    """
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم التصنيف",
        json_schema_extra={"example": "بيتزا"},
    )
    sort_order: Optional[int] = Field(
        None,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class CategoryResponse(CategoryBase):
    """
    مخطط استجابة التصنيف - يحتوي على جميع الحقول بما فيها التواريخ.
    
    Attributes:
        id: معرف التصنيف
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف التصنيف",
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
# 📋 CATEGORY LIST RESPONSE
# ==============================================

class CategoryListResponse(BaseModel):
    """
    مخطط استجابة قائمة التصنيفات.
    
    يحتوي على قائمة التصنيفات مع معلومات الترقيم.
    
    Attributes:
        items: قائمة التصنيفات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[CategoryResponse] = Field(
        ...,
        description="قائمة التصنيفات",
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
# 📊 CATEGORY SUMMARY
# ==============================================

class CategorySummary(BaseModel):
    """
    مخطط ملخص التصنيفات.
    
    يحتوي على إحصائيات موجزة عن التصنيفات.
    
    Attributes:
        total_categories: إجمالي عدد التصنيفات
        categories_with_products: عدد التصنيفات التي تحتوي على منتجات
        empty_categories: عدد التصنيفات الفارغة
        total_products: إجمالي عدد المنتجات في جميع التصنيفات
        avg_products_per_category: متوسط عدد المنتجات لكل تصنيف
    """
    model_config = ConfigDict(from_attributes=True)

    total_categories: int = Field(
        ...,
        description="إجمالي عدد التصنيفات",
        json_schema_extra={"example": 10},
    )
    categories_with_products: int = Field(
        ...,
        description="عدد التصنيفات التي تحتوي على منتجات",
        json_schema_extra={"example": 8},
    )
    empty_categories: int = Field(
        ...,
        description="عدد التصنيفات الفارغة",
        json_schema_extra={"example": 2},
    )
    total_products: int = Field(
        ...,
        description="إجمالي عدد المنتجات في جميع التصنيفات",
        json_schema_extra={"example": 50},
    )
    avg_products_per_category: float = Field(
        ...,
        description="متوسط عدد المنتجات لكل تصنيف",
        json_schema_extra={"example": 5.0},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
    "CategorySummary",
    "CategoryData",
    "CategoryUpdateData",
]