# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💬 MESSAGE SCHEMAS
# مخططات Pydantic للرسائل
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

MessageData = Dict[str, Any]
MessageUpdateData = Dict[str, Any]
MessageListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class MessageBase(BaseModel):
    """
    المخطط الأساسي للرسالة.
    
    Attributes:
        conversation_id: معرف المحادثة
        role: دور المرسل (user, assistant, system)
        content: محتوى الرسالة
        content_type: نوع المحتوى (text, image, audio, video, file)
        intent: نية الرسالة
        confidence: درجة الثقة
        entities: الكيانات المستخرجة
        meta_data: بيانات وصفية
    """
    conversation_id: int = Field(
        ...,
        description="معرف المحادثة",
        json_schema_extra={"example": 1},
        ge=1,
    )
    role: str = Field(
        ...,
        max_length=20,
        description="دور المرسل: user, assistant, system",
        json_schema_extra={"example": "user"},
    )
    content: str = Field(
        ...,
        description="محتوى الرسالة",
        json_schema_extra={"example": "مرحباً، أريد طلب بيتزا"},
        min_length=1,
    )
    content_type: str = Field(
        "text",
        max_length=20,
        description="نوع المحتوى: text, image, audio, video, file",
        json_schema_extra={"example": "text"},
    )
    intent: Optional[str] = Field(
        None,
        max_length=100,
        description="نية الرسالة",
        json_schema_extra={"example": "order_food"},
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="درجة الثقة",
        json_schema_extra={"example": 0.95},
    )
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="الكيانات المستخرجة",
        json_schema_extra={"example": {"product_name": "بيتزا", "quantity": 2}},
    )
    meta_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="بيانات وصفية",
        json_schema_extra={"example": {"language": "ar", "channel": "telegram"}},
    )

    # ==============================================
    # 🔍 VALIDATORS
    # ==============================================

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        """
        التحقق من صحة دور المرسل.
        
        Args:
            value: دور المرسل
            
        Returns:
            str: دور المرسل المدقق
            
        Raises:
            ValueError: إذا كان الدور غير صالح
        """
        valid_roles = {"user", "assistant", "system"}
        if value.lower() not in valid_roles:
            raise ValueError(
                f"دور المرسل يجب أن يكون واحداً من: {', '.join(valid_roles)}"
            )
        return value.lower()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        """
        التحقق من صحة نوع المحتوى.
        
        Args:
            value: نوع المحتوى
            
        Returns:
            str: نوع المحتوى المدقق
            
        Raises:
            ValueError: إذا كان النوع غير صالح
        """
        valid_types = {"text", "image", "audio", "video", "file"}
        if value.lower() not in valid_types:
            raise ValueError(
                f"نوع المحتوى يجب أن يكون واحداً من: {', '.join(valid_types)}"
            )
        return value.lower()

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """
        التحقق من صحة محتوى الرسالة.
        
        Args:
            value: محتوى الرسالة
            
        Returns:
            str: محتوى الرسالة المدقق
            
        Raises:
            ValueError: إذا كان المحتوى فارغاً
        """
        if not value or not value.strip():
            raise ValueError("محتوى الرسالة لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class MessageCreate(MessageBase):
    """
    مخطط إنشاء رسالة جديدة.
    """
    pass


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class MessageUpdate(BaseModel):
    """
    مخطط تحديث الرسالة.
    
    Attributes:
        content: محتوى الرسالة
        intent: نية الرسالة
        confidence: درجة الثقة
        entities: الكيانات المستخرجة
        meta_data: بيانات وصفية
    """
    content: Optional[str] = Field(
        None,
        description="محتوى الرسالة",
        json_schema_extra={"example": "مرحباً، أريد طلب بيتزا"},
    )
    intent: Optional[str] = Field(
        None,
        max_length=100,
        description="نية الرسالة",
        json_schema_extra={"example": "order_food"},
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="درجة الثقة",
        json_schema_extra={"example": 0.95},
    )
    entities: Optional[Dict[str, Any]] = Field(
        None,
        description="الكيانات المستخرجة",
        json_schema_extra={"example": {"product_name": "بيتزا", "quantity": 2}},
    )
    meta_data: Optional[Dict[str, Any]] = Field(
        None,
        description="بيانات وصفية",
        json_schema_extra={"example": {"language": "ar", "channel": "telegram"}},
    )

    # ==============================================
    # 🔍 VALIDATORS
    # ==============================================

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة محتوى الرسالة.
        
        Args:
            value: محتوى الرسالة
            
        Returns:
            Optional[str]: محتوى الرسالة المدقق
            
        Raises:
            ValueError: إذا كان المحتوى فارغاً
        """
        if value is not None:
            if not value or not value.strip():
                raise ValueError("محتوى الرسالة لا يمكن أن يكون فارغاً")
            return value.strip()
        return value


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class MessageResponse(MessageBase):
    """
    مخطط استجابة الرسالة.
    
    Attributes:
        id: معرف الرسالة
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الرسالة",
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

class MessageListResponse(BaseModel):
    """
    مخطط استجابة قائمة الرسائل.
    
    Attributes:
        items: قائمة الرسائل
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[MessageResponse] = Field(
        ...,
        description="قائمة الرسائل",
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

class MessageStatistics(BaseModel):
    """
    مخطط إحصائيات الرسائل.
    
    Attributes:
        total_messages: إجمالي عدد الرسائل
        user_messages: عدد رسائل المستخدم
        assistant_messages: عدد رسائل المساعد
        system_messages: عدد رسائل النظام
        role_summary: ملخص أدوار الرسائل
    """
    model_config = ConfigDict(from_attributes=True)

    total_messages: int = Field(
        ...,
        description="إجمالي عدد الرسائل",
        json_schema_extra={"example": 100},
        ge=0,
    )
    user_messages: int = Field(
        ...,
        description="عدد رسائل المستخدم",
        json_schema_extra={"example": 50},
        ge=0,
    )
    assistant_messages: int = Field(
        ...,
        description="عدد رسائل المساعد",
        json_schema_extra={"example": 45},
        ge=0,
    )
    system_messages: int = Field(
        ...,
        description="عدد رسائل النظام",
        json_schema_extra={"example": 5},
        ge=0,
    )
    role_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="ملخص أدوار الرسائل",
        json_schema_extra={
            "example": [
                {"role": "user", "count": 50},
                {"role": "assistant", "count": 45},
                {"role": "system", "count": 5},
            ]
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "MessageBase",
    "MessageCreate",
    "MessageUpdate",
    "MessageResponse",
    "MessageListResponse",
    "MessageStatistics",
    "MessageData",
    "MessageUpdateData",
    "MessageListData",
]