# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📡 CHANNEL SCHEMAS
# مخططات Pydantic للقنوات
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

ChannelData = Dict[str, Any]
ChannelUpdateData = Dict[str, Any]
ChannelListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class ChannelBase(BaseModel):
    """
    المخطط الأساسي للقناة.
    
    Attributes:
        agent_id: معرف الوكيل
        type: نوع القناة
        name: اسم القناة
        is_active: حالة النشاط
        config: إعدادات القناة
    """
    agent_id: int = Field(
        ...,
        description="معرف الوكيل",
        json_schema_extra={"example": 1},
        ge=1,
    )
    type: str = Field(
        ...,
        max_length=50,
        description="نوع القناة: telegram, whatsapp, web, messenger, api",
        json_schema_extra={"example": "telegram"},
    )
    name: str = Field(
        ...,
        max_length=100,
        description="اسم القناة",
        json_schema_extra={"example": "قناة تيليجرام"},
        min_length=1,
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="إعدادات القناة",
        json_schema_extra={
            "example": {
                "webhook_url": "https://example.com/webhook",
                "api_token": "123456789:ABC...",
            }
        },
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        """
        التحقق من صحة نوع القناة.
        
        Args:
            value: نوع القناة
            
        Returns:
            str: نوع القناة المدقق
            
        Raises:
            ValueError: إذا كان النوع غير صالح
        """
        valid_types = {"telegram", "whatsapp", "web", "messenger", "api"}
        if value.lower() not in valid_types:
            raise ValueError(
                f"نوع القناة يجب أن يكون واحداً من: {', '.join(valid_types)}"
            )
        return value.lower()

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        التحقق من صحة اسم القناة.
        
        Args:
            value: اسم القناة
            
        Returns:
            str: اسم القناة المدقق
            
        Raises:
            ValueError: إذا كان الاسم غير صالح
        """
        if not value or not value.strip():
            raise ValueError("اسم القناة لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class ChannelCreate(ChannelBase):
    """
    مخطط إنشاء قناة جديدة.
    """
    pass


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class ChannelUpdate(BaseModel):
    """
    مخطط تحديث القناة.
    
    Attributes:
        name: اسم القناة
        is_active: حالة النشاط
        config: إعدادات القناة
    """
    name: Optional[str] = Field(
        None,
        max_length=100,
        description="اسم القناة",
        json_schema_extra={"example": "قناة تيليجرام"},
    )
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="إعدادات القناة",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة اسم القناة.
        
        Args:
            value: اسم القناة
            
        Returns:
            Optional[str]: اسم القناة المدقق
            
        Raises:
            ValueError: إذا كان الاسم غير صالح
        """
        if value is not None:
            if not value or not value.strip():
                raise ValueError("اسم القناة لا يمكن أن يكون فارغاً")
            return value.strip()
        return value


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class ChannelResponse(ChannelBase):
    """
    مخطط استجابة القناة.
    
    Attributes:
        id: معرف القناة
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف القناة",
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
# 📋 LIST RESPONSE
# ==============================================

class ChannelListResponse(BaseModel):
    """
    مخطط استجابة قائمة القنوات.
    
    Attributes:
        items: قائمة القنوات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[ChannelResponse] = Field(
        ...,
        description="قائمة القنوات",
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
# 📊 STATISTICS SCHEMA
# ==============================================

class ChannelStatistics(BaseModel):
    """
    مخطط إحصائيات القنوات.
    
    Attributes:
        total_channels: إجمالي عدد القنوات
        active_channels: عدد القنوات النشطة
        inactive_channels: عدد القنوات غير النشطة
        types_summary: ملخص أنواع القنوات
    """
    model_config = ConfigDict(from_attributes=True)

    total_channels: int = Field(
        ...,
        description="إجمالي عدد القنوات",
        json_schema_extra={"example": 5},
        ge=0,
    )
    active_channels: int = Field(
        ...,
        description="عدد القنوات النشطة",
        json_schema_extra={"example": 3},
        ge=0,
    )
    inactive_channels: int = Field(
        ...,
        description="عدد القنوات غير النشطة",
        json_schema_extra={"example": 2},
        ge=0,
    )
    types_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="ملخص أنواع القنوات",
        json_schema_extra={
            "example": [
                {"type": "telegram", "count": 3},
                {"type": "whatsapp", "count": 2},
            ]
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "ChannelBase",
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelResponse",
    "ChannelListResponse",
    "ChannelStatistics",
    "ChannelData",
    "ChannelUpdateData",
    "ChannelListData",
]