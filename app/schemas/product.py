# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍔 PRODUCT SCHEMAS
# نماذج Pydantic للمنتجات
# تدير التحقق من صحة البيانات وتسلسلها للمنتجات
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

ProductData = Dict[str, Any]
ProductUpdateData = Dict[str, Any]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class ProductBase(BaseModel):
    """
    المخطط الأساسي للمنتج.
    
    يحتوي على الحقول المشتركة بين جميع مخططات المنتج.
    
    Attributes:
        restaurant_id: معرف المطعم
        category_id: معرف التصنيف
        name: اسم المنتج
        description: وصف المنتج
        price: السعر
        image_url: رابط الصورة
        is_available: حالة التوفر
        sort_order: ترتيب العرض
    """
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    category_id: int = Field(
        ...,
        description="معرف التصنيف",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
    )
    description: Optional[str] = Field(
        None,
        description="وصف المنتج",
        json_schema_extra={"example": "بيتزا كلاسيكية مع صلصة الطماطم والموزاريلا"},
    )
    price: float = Field(
        ...,
        gt=0,
        description="السعر",
        json_schema_extra={"example": 25.00},
    )
    image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="رابط الصورة",
        json_schema_extra={"example": "https://example.com/pizza.jpg"},
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

class ProductCreate(BaseModel):
    """
    مخطط إنشاء منتج جديد.
    
    Attributes:
        category_id: معرف التصنيف
        name: اسم المنتج
        description: وصف المنتج
        price: السعر
        image_url: رابط الصورة (اختياري)
        sort_order: ترتيب العرض (اختياري)
    """
    category_id: int = Field(
        ...,
        description="معرف التصنيف",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
    )
    description: Optional[str] = Field(
        None,
        description="وصف المنتج",
        json_schema_extra={"example": "بيتزا كلاسيكية مع صلصة الطماطم والموزاريلا"},
    )
    price: float = Field(
        ...,
        gt=0,
        description="السعر",
        json_schema_extra={"example": 25.00},
    )
    image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="رابط الصورة",
        json_schema_extra={"example": "https://example.com/pizza.jpg"},
    )
    sort_order: int = Field(
        0,
        description="ترتيب العرض",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class ProductUpdate(BaseModel):
    """
    مخطط تحديث المنتج - جميع الحقول اختيارية.
    
    Attributes:
        category_id: معرف التصنيف
        name: اسم المنتج
        description: وصف المنتج
        price: السعر
        image_url: رابط الصورة
        is_available: حالة التوفر
        sort_order: ترتيب العرض
    """
    category_id: Optional[int] = Field(
        None,
        description="معرف التصنيف",
        json_schema_extra={"example": 1},
    )
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
    )
    description: Optional[str] = Field(
        None,
        description="وصف المنتج",
        json_schema_extra={"example": "بيتزا كلاسيكية مع صلصة الطماطم والموزاريلا"},
    )
    price: Optional[float] = Field(
        None,
        gt=0,
        description="السعر",
        json_schema_extra={"example": 25.00},
    )
    image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="رابط الصورة",
        json_schema_extra={"example": "https://example.com/pizza.jpg"},
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

class ProductAvailabilityUpdate(BaseModel):
    """
    مخطط تحديث حالة توفر المنتج.
    
    Attributes:
        is_available: حالة التوفر الجديدة
    """
    is_available: bool = Field(
        ...,
        description="حالة التوفر الجديدة",
        json_schema_extra={"example": True},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class ProductResponse(ProductBase):
    """
    مخطط استجابة المنتج - يحتوي على جميع الحقول بما فيها التواريخ.
    
    Attributes:
        id: معرف المنتج
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف المنتج",
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
# 📋 PRODUCT LIST RESPONSE
# ==============================================

class ProductListResponse(BaseModel):
    """
    مخطط استجابة قائمة المنتجات.
    
    يحتوي على قائمة المنتجات مع معلومات الترقيم.
    
    Attributes:
        items: قائمة المنتجات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[ProductResponse] = Field(
        ...,
        description="قائمة المنتجات",
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
# 📊 PRODUCT SUMMARY
# ==============================================

class ProductSummary(BaseModel):
    """
    مخطط ملخص المنتجات.
    
    يحتوي على إحصائيات موجزة عن المنتجات.
    
    Attributes:
        total_products: إجمالي عدد المنتجات
        available_products: عدد المنتجات المتاحة
        unavailable_products: عدد المنتجات غير المتاحة
        total_price: إجمالي أسعار المنتجات
        avg_price: متوسط السعر
        min_price: أقل سعر
        max_price: أعلى سعر
    """
    model_config = ConfigDict(from_attributes=True)

    total_products: int = Field(
        ...,
        description="إجمالي عدد المنتجات",
        json_schema_extra={"example": 10},
    )
    available_products: int = Field(
        ...,
        description="عدد المنتجات المتاحة",
        json_schema_extra={"example": 8},
    )
    unavailable_products: int = Field(
        ...,
        description="عدد المنتجات غير المتاحة",
        json_schema_extra={"example": 2},
    )
    total_price: float = Field(
        ...,
        description="إجمالي أسعار المنتجات",
        json_schema_extra={"example": 250.00},
    )
    avg_price: float = Field(
        ...,
        description="متوسط السعر",
        json_schema_extra={"example": 25.00},
    )
    min_price: float = Field(
        ...,
        description="أقل سعر",
        json_schema_extra={"example": 10.00},
    )
    max_price: float = Field(
        ...,
        description="أعلى سعر",
        json_schema_extra={"example": 50.00},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductAvailabilityUpdate",
    "ProductResponse",
    "ProductListResponse",
    "ProductSummary",
    "ProductData",
    "ProductUpdateData",
]