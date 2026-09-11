# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👑 ADMIN SCHEMAS
# نماذج Pydantic للمديرين
# تدير التحقق من صحة البيانات وتسلسلها للمديرين
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

AdminData = Dict[str, Any]
AdminUpdateData = Dict[str, Any]
AdminSessionData = Dict[str, Any]
RoleDistribution = Dict[str, int]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class AdminBase(BaseModel):
    """
    المخطط الأساسي للمدير.
    
    يحتوي على الحقول المشتركة بين جميع مخططات المدير.
    
    Attributes:
        chat_id: معرف الدردشة في Telegram
        username: اسم المستخدم
        full_name: الاسم الكامل
        role: دور المدير
        is_active: حالة النشاط
    """
    chat_id: int = Field(
        ...,
        description="معرف الدردشة في Telegram",
        json_schema_extra={"example": 123456789},
    )
    username: str = Field(
        ...,
        max_length=255,
        description="اسم المستخدم",
        json_schema_extra={"example": "admin_username"},
    )
    full_name: str = Field(
        ...,
        max_length=255,
        description="الاسم الكامل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    role: str = Field(
        "admin",
        max_length=50,
        description="دور المدير (admin, super_admin, manager)",
        json_schema_extra={"example": "admin"},
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class AdminCreate(BaseModel):
    """
    مخطط إنشاء مدير جديد.
    
    Attributes:
        chat_id: معرف الدردشة في Telegram
        username: اسم المستخدم
        full_name: الاسم الكامل
        password: كلمة المرور (اختياري)
        role: دور المدير (اختياري)
        is_active: حالة النشاط (اختياري)
    """
    chat_id: int = Field(
        ...,
        description="معرف الدردشة في Telegram",
        json_schema_extra={"example": 123456789},
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="اسم المستخدم",
        json_schema_extra={"example": "admin_username"},
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="الاسم الكامل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=255,
        description="كلمة المرور (اختياري)",
        json_schema_extra={"example": "SecurePassword123"},
    )
    role: str = Field(
        "admin",
        max_length=50,
        description="دور المدير (admin, super_admin, manager)",
        json_schema_extra={"example": "admin"},
    )
    is_active: Optional[bool] = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """
        التحقق من صحة اسم المستخدم.
        
        Args:
            value: اسم المستخدم
            
        Returns:
            str: اسم المستخدم المحقق
            
        Raises:
            ValueError: إذا كان اسم المستخدم غير صالح
        """
        if not value.strip():
            raise ValueError("اسم المستخدم لا يمكن أن يكون فارغاً")
        if " " in value:
            raise ValueError("اسم المستخدم لا يمكن أن يحتوي على مسافات")
        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        """
        التحقق من صحة الدور.
        
        Args:
            value: الدور
            
        Returns:
            str: الدور المحقق
            
        Raises:
            ValueError: إذا كان الدور غير صالح
        """
        valid_roles = ["admin", "super_admin", "manager"]
        if value not in valid_roles:
            raise ValueError(
                f"الدور يجب أن يكون أحد القيم: {', '.join(valid_roles)}"
            )
        return value


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class AdminUpdate(BaseModel):
    """
    مخطط تحديث المدير - جميع الحقول اختيارية.
    
    Attributes:
        username: اسم المستخدم
        full_name: الاسم الكامل
        password: كلمة المرور الجديدة
        role: دور المدير
        is_active: حالة النشاط
    """
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        description="اسم المستخدم",
        json_schema_extra={"example": "admin_username"},
    )
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="الاسم الكامل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=255,
        description="كلمة المرور الجديدة",
        json_schema_extra={"example": "NewSecurePassword123"},
    )
    role: Optional[str] = Field(
        None,
        max_length=50,
        description="دور المدير (admin, super_admin, manager)",
        json_schema_extra={"example": "super_admin"},
    )
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة اسم المستخدم.
        
        Args:
            value: اسم المستخدم
            
        Returns:
            Optional[str]: اسم المستخدم المحقق
            
        Raises:
            ValueError: إذا كان اسم المستخدم غير صالح
        """
        if value is not None:
            if not value.strip():
                raise ValueError("اسم المستخدم لا يمكن أن يكون فارغاً")
            if " " in value:
                raise ValueError("اسم المستخدم لا يمكن أن يحتوي على مسافات")
            return value.strip().lower()
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة الدور.
        
        Args:
            value: الدور
            
        Returns:
            Optional[str]: الدور المحقق
            
        Raises:
            ValueError: إذا كان الدور غير صالح
        """
        if value is not None:
            valid_roles = ["admin", "super_admin", "manager"]
            if value not in valid_roles:
                raise ValueError(
                    f"الدور يجب أن يكون أحد القيم: {', '.join(valid_roles)}"
                )
        return value


# ==============================================
# 🔐 LOGIN SCHEMA
# ==============================================

class AdminLogin(BaseModel):
    """
    مخطط تسجيل دخول المدير.
    
    Attributes:
        username: اسم المستخدم
        password: كلمة المرور
    """
    username: str = Field(
        ...,
        description="اسم المستخدم",
        json_schema_extra={"example": "admin_username"},
    )
    password: str = Field(
        ...,
        min_length=1,
        description="كلمة المرور",
        json_schema_extra={"example": "SecurePassword123"},
    )


# ==============================================
# 🔐 SESSION SCHEMAS
# ==============================================

class AdminSessionBase(BaseModel):
    """
    المخطط الأساسي لجلسة المدير.
    
    Attributes:
        admin_id: معرف المدير
        session_token: رمز الجلسة
        ip_address: عنوان IP
        user_agent: متصفح المستخدم
        expires_at: تاريخ انتهاء الجلسة
        is_active: حالة النشاط
    """
    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
    )
    session_token: str = Field(
        ...,
        description="رمز الجلسة",
        json_schema_extra={"example": "abc123def456"},
    )
    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="عنوان IP",
        json_schema_extra={"example": "192.168.1.1"},
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="متصفح المستخدم",
        json_schema_extra={"example": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    expires_at: datetime = Field(
        ...,
        description="تاريخ انتهاء الجلسة",
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )


class AdminSessionCreate(BaseModel):
    """
    مخطط إنشاء جلسة مدير جديدة.
    
    Attributes:
        admin_id: معرف المدير
        session_token: رمز الجلسة
        expires_at: تاريخ انتهاء الجلسة
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المستخدم (اختياري)
    """
    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
    )
    session_token: str = Field(
        ...,
        description="رمز الجلسة",
        json_schema_extra={"example": "abc123def456"},
    )
    expires_at: datetime = Field(
        ...,
        description="تاريخ انتهاء الجلسة",
    )
    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="عنوان IP",
        json_schema_extra={"example": "192.168.1.1"},
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="متصفح المستخدم",
        json_schema_extra={"example": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )


class AdminSessionUpdate(BaseModel):
    """
    مخطط تحديث جلسة المدير.
    
    Attributes:
        is_active: حالة النشاط
        expires_at: تاريخ انتهاء الجلسة
        last_activity: تاريخ آخر نشاط
    """
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": False},
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="تاريخ انتهاء الجلسة",
    )
    last_activity: Optional[datetime] = Field(
        None,
        description="تاريخ آخر نشاط",
    )


class AdminSessionResponse(AdminSessionBase):
    """
    مخطط استجابة جلسة المدير.
    
    Attributes:
        id: معرف الجلسة
        last_activity: تاريخ آخر نشاط
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الجلسة",
        json_schema_extra={"example": 1},
    )
    last_activity: datetime = Field(
        ...,
        description="تاريخ آخر نشاط",
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
# 📤 RESPONSE SCHEMA
# ==============================================

class AdminResponse(AdminBase):
    """
    مخطط استجابة المدير - يحتوي على جميع الحقول بما فيها التواريخ.
    
    Attributes:
        id: معرف المدير
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف المدير",
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
# 📋 ADMIN LIST RESPONSE
# ==============================================

class AdminListResponse(BaseModel):
    """
    مخطط استجابة قائمة المديرين.
    
    يحتوي على قائمة المديرين مع معلومات الترقيم.
    
    Attributes:
        items: قائمة المديرين
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[AdminResponse] = Field(
        ...,
        description="قائمة المديرين",
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
# 🔐 LOGIN RESPONSE
# ==============================================

class AdminLoginResponse(BaseModel):
    """
    مخطط استجابة تسجيل الدخول.
    
    يحتوي على بيانات المدير وبيانات الجلسة.
    
    Attributes:
        admin: بيانات المدير
        session: بيانات الجلسة
    """
    model_config = ConfigDict(from_attributes=True)

    admin: AdminResponse = Field(
        ...,
        description="بيانات المدير",
    )
    session: AdminSessionResponse = Field(
        ...,
        description="بيانات الجلسة",
    )


# ==============================================
# 📊 ADMIN STATISTICS
# ==============================================

class AdminStatistics(BaseModel):
    """
    مخطط إحصائيات المديرين.
    
    يحتوي على إحصائيات موجزة عن المديرين.
    
    Attributes:
        total: إجمالي عدد المديرين
        active: عدد المديرين النشطين
        inactive: عدد المديرين غير النشطين
        roles: توزيع الأدوار
    """
    model_config = ConfigDict(from_attributes=True)

    total: int = Field(
        ...,
        description="إجمالي عدد المديرين",
        json_schema_extra={"example": 10},
    )
    active: int = Field(
        ...,
        description="عدد المديرين النشطين",
        json_schema_extra={"example": 8},
    )
    inactive: int = Field(
        ...,
        description="عدد المديرين غير النشطين",
        json_schema_extra={"example": 2},
    )
    roles: RoleDistribution = Field(
        ...,
        description="توزيع الأدوار",
        json_schema_extra={
            "example": {
                "super_admin": 1,
                "admin": 5,
                "manager": 4,
            }
        },
    )


# ==============================================
# 🔐 AUTH RESPONSE
# ==============================================

class AdminAuthResponse(BaseModel):
    """
    مخطط استجابة المصادقة.
    
    يحتوي على بيانات المدير ورمز الجلسة.
    
    Attributes:
        admin: بيانات المدير
        session_token: رمز الجلسة
        expires_at: تاريخ انتهاء الجلسة
    """
    model_config = ConfigDict(from_attributes=True)

    admin: AdminResponse = Field(
        ...,
        description="بيانات المدير",
    )
    session_token: str = Field(
        ...,
        description="رمز الجلسة",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    expires_at: datetime = Field(
        ...,
        description="تاريخ انتهاء الجلسة",
    )


# ==============================================
# 🔄 TOKEN RESPONSE
# ==============================================

class TokenResponse(BaseModel):
    """
    مخطط استجابة رمز المصادقة (JWT).
    
    Attributes:
        access_token: رمز الوصول
        token_type: نوع الرمز
        expires_in: مدة الصلاحية بالثواني
    """
    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(
        ...,
        description="رمز الوصول",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    token_type: str = Field(
        "bearer",
        description="نوع الرمز",
        json_schema_extra={"example": "bearer"},
    )
    expires_in: int = Field(
        ...,
        description="مدة الصلاحية بالثواني",
        json_schema_extra={"example": 604800},
        ge=1,
    )


# ==============================================
# 🔍 ADMIN SEARCH
# ==============================================

class AdminSearch(BaseModel):
    """
    مخطط البحث عن المديرين.
    
    Attributes:
        query: نص البحث
        only_active: البحث في النشطين فقط
        role: تصفية حسب الدور
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="نص البحث",
        json_schema_extra={"example": "أحمد"},
    )
    only_active: bool = Field(
        True,
        description="البحث في النشطين فقط",
        json_schema_extra={"example": True},
    )
    role: Optional[str] = Field(
        None,
        max_length=50,
        description="تصفية حسب الدور",
        json_schema_extra={"example": "admin"},
    )
    skip: int = Field(
        0,
        description="عدد السجلات المتخطية",
        json_schema_extra={"example": 0},
        ge=0,
    )
    limit: int = Field(
        100,
        description="الحد الأقصى للسجلات",
        json_schema_extra={"example": 100},
        ge=1,
        le=1000,
    )


# ==============================================
# 🔐 PERMISSION CHECK
# ==============================================

class AdminPermissionCheck(BaseModel):
    """
    مخطط التحقق من صلاحيات المدير.
    
    Attributes:
        admin_id: معرف المدير
        required_role: الدور المطلوب
        required_permission: الصلاحية المطلوبة
    """
    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
        ge=1,
    )
    required_role: Optional[str] = Field(
        None,
        max_length=50,
        description="الدور المطلوب",
        json_schema_extra={"example": "super_admin"},
    )
    required_permission: Optional[str] = Field(
        None,
        max_length=100,
        description="الصلاحية المطلوبة",
        json_schema_extra={"example": "manage_admins"},
    )


class AdminPermissionResponse(BaseModel):
    """
    مخطط استجابة التحقق من الصلاحيات.
    
    Attributes:
        has_permission: وجود الصلاحية
        admin_id: معرف المدير
        role: دور المدير
        is_active: حالة النشاط
        message: رسالة توضيحية
    """
    model_config = ConfigDict(from_attributes=True)

    has_permission: bool = Field(
        ...,
        description="وجود الصلاحية",
        json_schema_extra={"example": True},
    )
    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
    )
    role: str = Field(
        ...,
        description="دور المدير",
        json_schema_extra={"example": "super_admin"},
    )
    is_active: bool = Field(
        ...,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    message: Optional[str] = Field(
        None,
        description="رسالة توضيحية",
        json_schema_extra={"example": "المدير لديه الصلاحية المطلوبة"},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "AdminBase",
    "AdminCreate",
    "AdminResponse",
    "AdminUpdate",
    "AdminLogin",
    "AdminLoginResponse",
    "AdminAuthResponse",
    "AdminSessionBase",
    "AdminSessionCreate",
    "AdminSessionUpdate",
    "AdminSessionResponse",
    "AdminListResponse",
    "AdminStatistics",
    "AdminSearch",
    "AdminPermissionCheck",
    "AdminPermissionResponse",
    "TokenResponse",
    "RoleDistribution",
    "AdminData",
    "AdminUpdateData",
    "AdminSessionData",
]