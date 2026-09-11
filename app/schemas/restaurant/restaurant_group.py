# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUP SCHEMAS
# مخططات Pydantic لمجموعات المطاعم
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
    field_validator,
)


# ==============================================
# 🧩 TYPES
# ==============================================

RestaurantGroupData = Dict[str, Any]
RestaurantGroupUpdateData = Dict[str, Any]
RestaurantGroupListData = List[Dict[str, Any]]

RestaurantBranchData = Dict[str, Any]
RestaurantBranchUpdateData = Dict[str, Any]
RestaurantBranchListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA - RESTAURANT GROUP
# ==============================================

class RestaurantGroupBase(BaseModel):
    """
    المخطط الأساسي لمجموعة المطاعم.
    
    Attributes:
        owner_id: معرف المالك
        name: اسم المجموعة
        is_active: حالة النشاط
    """
    owner_id: int = Field(
        ...,
        description="معرف المالك",
        json_schema_extra={"example": 1},
        ge=1,
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم المجموعة",
        json_schema_extra={"example": "مطاعم البحر الأبيض المتوسط"},
        min_length=1,
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        التحقق من صحة اسم المجموعة.
        
        Args:
            value: اسم المجموعة
            
        Returns:
            str: اسم المجموعة المدقق
            
        Raises:
            ValueError: إذا كان الاسم غير صالح
        """
        if not value or not value.strip():
            raise ValueError("اسم المجموعة لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📥 CREATE SCHEMA - RESTAURANT GROUP
# ==============================================

class RestaurantGroupCreate(RestaurantGroupBase):
    """
    مخطط إنشاء مجموعة مطاعم جديدة.
    """
    pass


# ==============================================
# 📤 UPDATE SCHEMA - RESTAURANT GROUP
# ==============================================

class RestaurantGroupUpdate(BaseModel):
    """
    مخطط تحديث مجموعة المطاعم.
    
    Attributes:
        name: اسم المجموعة
        is_active: حالة النشاط
    """
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم المجموعة",
        json_schema_extra={"example": "مطاعم البحر الأبيض المتوسط"},
    )
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة اسم المجموعة.
        
        Args:
            value: اسم المجموعة
            
        Returns:
            Optional[str]: اسم المجموعة المدقق
            
        Raises:
            ValueError: إذا كان الاسم غير صالح
        """
        if value is not None:
            if not value or not value.strip():
                raise ValueError("اسم المجموعة لا يمكن أن يكون فارغاً")
            return value.strip()
        return value


# ==============================================
# 📤 RESPONSE SCHEMA - RESTAURANT GROUP
# ==============================================

class RestaurantGroupResponse(RestaurantGroupBase):
    """
    مخطط استجابة مجموعة المطاعم.
    
    Attributes:
        id: معرف المجموعة
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف المجموعة",
        json_schema_extra={"example": 1},
        ge=1,
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
# 📋 LIST RESPONSE - RESTAURANT GROUP
# ==============================================

class RestaurantGroupListResponse(BaseModel):
    """
    مخطط استجابة قائمة مجموعات المطاعم.
    
    Attributes:
        items: قائمة المجموعات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[RestaurantGroupResponse] = Field(
        ...,
        description="قائمة مجموعات المطاعم",
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
# 📊 STATISTICS SCHEMA - RESTAURANT GROUP
# ==============================================

class RestaurantGroupStatistics(BaseModel):
    """
    مخطط إحصائيات مجموعات المطاعم.
    
    Attributes:
        total_groups: إجمالي عدد المجموعات
        active_groups: عدد المجموعات النشطة
        inactive_groups: عدد المجموعات غير النشطة
    """
    model_config = ConfigDict(from_attributes=True)

    total_groups: int = Field(
        ...,
        description="إجمالي عدد المجموعات",
        json_schema_extra={"example": 5},
        ge=0,
    )
    active_groups: int = Field(
        ...,
        description="عدد المجموعات النشطة",
        json_schema_extra={"example": 3},
        ge=0,
    )
    inactive_groups: int = Field(
        ...,
        description="عدد المجموعات غير النشطة",
        json_schema_extra={"example": 2},
        ge=0,
    )


# ==============================================
# 📦 BASE SCHEMA - RESTAURANT BRANCH
# ==============================================

class RestaurantBranchBase(BaseModel):
    """
    المخطط الأساسي لفرع المطعم.
    
    Attributes:
        group_id: معرف المجموعة
        restaurant_id: معرف المطعم
    """
    group_id: int = Field(
        ...,
        description="معرف المجموعة",
        json_schema_extra={"example": 1},
        ge=1,
    )
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )


# ==============================================
# 📥 CREATE SCHEMA - RESTAURANT BRANCH
# ==============================================

class RestaurantBranchCreate(RestaurantBranchBase):
    """
    مخطط إنشاء فرع مطعم جديد.
    """
    pass


# ==============================================
# 📤 UPDATE SCHEMA - RESTAURANT BRANCH
# ==============================================

class RestaurantBranchUpdate(BaseModel):
    """
    مخطط تحديث فرع المطعم.
    
    Attributes:
        group_id: معرف المجموعة
        restaurant_id: معرف المطعم
    """
    group_id: Optional[int] = Field(
        None,
        description="معرف المجموعة",
        json_schema_extra={"example": 1},
        ge=1,
    )
    restaurant_id: Optional[int] = Field(
        None,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )


# ==============================================
# 📤 RESPONSE SCHEMA - RESTAURANT BRANCH
# ==============================================

class RestaurantBranchResponse(RestaurantBranchBase):
    """
    مخطط استجابة فرع المطعم.
    
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
        ge=1,
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
# 📋 LIST RESPONSE - RESTAURANT BRANCH
# ==============================================

class RestaurantBranchListResponse(BaseModel):
    """
    مخطط استجابة قائمة فروع المطاعم.
    
    Attributes:
        items: قائمة الفروع
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[RestaurantBranchResponse] = Field(
        ...,
        description="قائمة فروع المطاعم",
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
# 📦 BULK CREATE SCHEMA - RESTAURANT BRANCH
# ==============================================

class RestaurantBranchBulkCreate(BaseModel):
    """
    مخطط إنشاء فروع مطاعم متعددة دفعة واحدة.
    
    Attributes:
        group_id: معرف المجموعة
        restaurant_ids: قائمة معرفات المطاعم
    """
    group_id: int = Field(
        ...,
        description="معرف المجموعة",
        json_schema_extra={"example": 1},
        ge=1,
    )
    restaurant_ids: List[int] = Field(
        ...,
        description="قائمة معرفات المطاعم",
        json_schema_extra={"example": [1, 2, 3]},
        min_length=1,
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("restaurant_ids")
    @classmethod
    def validate_restaurant_ids(cls, value: List[int]) -> List[int]:
        """
        التحقق من صحة قائمة معرفات المطاعم.
        
        Args:
            value: قائمة معرفات المطاعم
            
        Returns:
            List[int]: قائمة معرفات المطاعم المدققة
            
        Raises:
            ValueError: إذا كانت القائمة فارغة أو تحتوي على قيم مكررة
        """
        if not value:
            raise ValueError("يجب تحديد معرفات المطاعم")

        # التحقق من عدم وجود قيم مكررة
        if len(value) != len(set(value)):
            raise ValueError("معرفات المطاعم يجب أن تكون فريدة")

        # التحقق من أن جميع القيم أكبر من الصفر
        for restaurant_id in value:
            if restaurant_id <= 0:
                raise ValueError("معرف المطعم يجب أن يكون أكبر من الصفر")

        return value


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [

    # Types
    "RestaurantGroupData",
    "RestaurantGroupUpdateData",
    "RestaurantGroupListData",
    "RestaurantBranchData",
    "RestaurantBranchUpdateData",
    "RestaurantBranchListData",

    # Restaurant Group
    "RestaurantGroupBase",
    "RestaurantGroupCreate",
    "RestaurantGroupUpdate",
    "RestaurantGroupResponse",
    "RestaurantGroupListResponse",
    "RestaurantGroupStatistics",

    # Restaurant Branch
    "RestaurantBranchBase",
    "RestaurantBranchCreate",
    "RestaurantBranchUpdate",
    "RestaurantBranchResponse",
    "RestaurantBranchListResponse",
    "RestaurantBranchBulkCreate",
]