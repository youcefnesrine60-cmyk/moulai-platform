# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDER SCHEMAS
# نماذج Pydantic للطلبات
# تدير التحقق من صحة البيانات وتسلسلها للطلبات
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

OrderData = Dict[str, Any]
OrderUpdateData = Dict[str, Any]
OrderListData = List[Dict[str, Any]]

# ==============================================
# 📦 OPTION PAYLOAD
# ==============================================

class OrderOptionPayload(BaseModel):
    """
    مخطط خيار عنصر الطلب (Payload).

    يُستخدم داخل `OrderItemPayload` عند إنشاء طلب مع عناصره.

    Attributes:
        option_group_name: اسم مجموعة الخيارات
        option_name: اسم الخيار
        additional_price: السعر الإضافي
    """
    option_group_name: str = Field(
        ...,
        max_length=255,
        description="اسم مجموعة الخيارات",
        json_schema_extra={"example": "حجم"},
    )
    option_name: str = Field(
        ...,
        max_length=255,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    additional_price: float = Field(
        0,
        ge=0,
        description="السعر الإضافي",
        json_schema_extra={"example": 5.00},
    )


# ==============================================
# 📦 ITEM PAYLOAD
# ==============================================

class OrderItemPayload(BaseModel):
    """
    مخطط عنصر الطلب (Payload).

    يُستخدم داخل `OrderCreate` عند إنشاء طلب مع عناصره.

    Attributes:
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        options: قائمة الخيارات (اختياري)
    """
    product_id: int = Field(
        ...,
        ge=1,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    product_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
    )
    unit_price: float = Field(
        ...,
        gt=0,
        description="سعر الوحدة",
        json_schema_extra={"example": 25.00},
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="الكمية",
        json_schema_extra={"example": 2},
    )
    total_price: float = Field(
        ...,
        gt=0,
        description="السعر الإجمالي",
        json_schema_extra={"example": 50.00},
    )
    options: Optional[List[OrderOptionPayload]] = Field(
        None,
        description="قائمة خيارات العنصر",
    )


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class OrderBase(BaseModel):
    """
    المخطط الأساسي للطلب.

    يحتوي على الحقول المشتركة بين جميع مخططات الطلب.

    Attributes:
        restaurant_id: معرف المطعم
        branch_id: معرف الفرع
        table_id: معرف الطاولة
        employee_id: معرف الموظف
        order_number: رقم الطلب
        order_type: نوع الطلب (dine_in, takeaway, delivery)
        customer_name: اسم العميل
        customer_phone: رقم هاتف العميل
        delivery_address: عنوان التوصيل
        customer_note: ملاحظات العميل
        status: حالة الطلب
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
        is_paid: هل الطلب مدفوع؟
        payment_status: حالة الدفع
    """
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    branch_id: Optional[int] = Field(
        None,
        description="معرف الفرع",
        json_schema_extra={"example": 1},
    )
    table_id: Optional[int] = Field(
        None,
        description="معرف الطاولة",
        json_schema_extra={"example": 1},
    )
    employee_id: Optional[int] = Field(
        None,
        description="معرف الموظف",
        json_schema_extra={"example": 1},
    )
    order_number: str = Field(
        ...,
        max_length=50,
        description="رقم الطلب",
        json_schema_extra={"example": "RST1-000001"},
    )
    order_type: str = Field(
        ...,
        max_length=30,
        description="نوع الطلب: dine_in, takeaway, delivery",
        json_schema_extra={"example": "dine_in"},
    )
    customer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم العميل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    customer_phone: Optional[str] = Field(
        None,
        max_length=50,
        description="رقم هاتف العميل",
        json_schema_extra={"example": "0555123456"},
    )
    delivery_address: Optional[str] = Field(
        None,
        description="عنوان التوصيل",
        json_schema_extra={"example": "شارع الأندلس، الجزائر"},
    )
    customer_note: Optional[str] = Field(
        None,
        description="ملاحظات العميل",
        json_schema_extra={"example": "الرجاء إضافة صوص إضافي"},
    )
    status: str = Field(
        "pending",
        max_length=50,
        description=(
            "حالة الطلب: pending, confirmed, preparing, ready, "
            "delivering, delivered, completed, cancelled"
        ),
        json_schema_extra={"example": "pending"},
    )
    subtotal_amount: float = Field(
        0,
        description="المبلغ الإجمالي قبل الخصم",
        json_schema_extra={"example": 100.00},
        ge=0,
    )
    discount_amount: float = Field(
        0,
        description="مبلغ الخصم",
        json_schema_extra={"example": 10.00},
        ge=0,
    )
    tax_amount: float = Field(
        0,
        description="مبلغ الضريبة",
        json_schema_extra={"example": 15.00},
        ge=0,
    )
    delivery_amount: float = Field(
        0,
        description="مبلغ التوصيل",
        json_schema_extra={"example": 5.00},
        ge=0,
    )
    total_amount: float = Field(
        0,
        description="المبلغ النهائي",
        json_schema_extra={"example": 110.00},
        ge=0,
    )
    is_paid: bool = Field(
        False,
        description="هل الطلب مدفوع؟",
        json_schema_extra={"example": False},
    )
    payment_status: Optional[str] = Field(
        None,
        max_length=50,
        description="حالة الدفع",
        json_schema_extra={"example": "pending"},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        """
        التحقق من صحة نوع الطلب.

        Args:
            value: نوع الطلب

        Returns:
            str: نوع الطلب المدقق

        Raises:
            ValueError: إذا كان النوع غير صالح
        """
        valid_types = {"dine_in", "takeaway", "delivery"}
        if value.lower() not in valid_types:
            raise ValueError(
                f"نوع الطلب يجب أن يكون واحداً من: {', '.join(valid_types)}"
            )
        return value.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """
        التحقق من صحة حالة الطلب.

        Args:
            value: حالة الطلب

        Returns:
            str: حالة الطلب المدققة

        Raises:
            ValueError: إذا كانت الحالة غير صالحة
        """
        valid_statuses = {
            "pending",
            "confirmed",
            "preparing",
            "ready",
            "delivering",
            "delivered",
            "completed",
            "cancelled",
        }
        if value.lower() not in valid_statuses:
            raise ValueError(
                f"حالة الطلب يجب أن تكون واحدة من: {', '.join(valid_statuses)}"
            )
        return value.lower()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class OrderCreate(BaseModel):
    """
    مخطط إنشاء طلب جديد.

    Attributes:
        restaurant_id: معرف المطعم
        branch_id: معرف الفرع (اختياري)
        table_id: معرف الطاولة (اختياري)
        employee_id: معرف الموظف (اختياري)
        order_type: نوع الطلب
        customer_name: اسم العميل (اختياري)
        customer_phone: رقم هاتف العميل (اختياري)
        delivery_address: عنوان التوصيل (اختياري)
        customer_note: ملاحظات العميل (اختياري)
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
        items: قائمة عناصر الطلب (اختياري)
    """
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    branch_id: Optional[int] = Field(
        None,
        description="معرف الفرع",
        json_schema_extra={"example": 1},
    )
    table_id: Optional[int] = Field(
        None,
        description="معرف الطاولة",
        json_schema_extra={"example": 1},
    )
    employee_id: Optional[int] = Field(
        None,
        description="معرف الموظف",
        json_schema_extra={"example": 1},
    )
    order_type: str = Field(
        ...,
        max_length=30,
        description="نوع الطلب: dine_in, takeaway, delivery",
        json_schema_extra={"example": "dine_in"},
    )
    customer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم العميل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    customer_phone: Optional[str] = Field(
        None,
        max_length=50,
        description="رقم هاتف العميل",
        json_schema_extra={"example": "0555123456"},
    )
    delivery_address: Optional[str] = Field(
        None,
        description="عنوان التوصيل",
        json_schema_extra={"example": "شارع الأندلس، الجزائر"},
    )
    customer_note: Optional[str] = Field(
        None,
        description="ملاحظات العميل",
        json_schema_extra={"example": "الرجاء إضافة صوص إضافي"},
    )
    subtotal_amount: float = Field(
        0,
        description="المبلغ الإجمالي قبل الخصم",
        json_schema_extra={"example": 100.00},
        ge=0,
    )
    discount_amount: float = Field(
        0,
        description="مبلغ الخصم",
        json_schema_extra={"example": 10.00},
        ge=0,
    )
    tax_amount: float = Field(
        0,
        description="مبلغ الضريبة",
        json_schema_extra={"example": 15.00},
        ge=0,
    )
    delivery_amount: float = Field(
        0,
        description="مبلغ التوصيل",
        json_schema_extra={"example": 5.00},
        ge=0,
    )
    total_amount: float = Field(
        0,
        description="المبلغ النهائي",
        json_schema_extra={"example": 110.00},
        ge=0,
    )
    items: Optional[List[OrderItemPayload]] = Field(
        None,
        description="قائمة عناصر الطلب",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        """
        التحقق من صحة نوع الطلب.

        Args:
            value: نوع الطلب

        Returns:
            str: نوع الطلب المدقق

        Raises:
            ValueError: إذا كان النوع غير صالح
        """
        valid_types = {"dine_in", "takeaway", "delivery"}
        if value.lower() not in valid_types:
            raise ValueError(
                f"نوع الطلب يجب أن يكون واحداً من: {', '.join(valid_types)}"
            )
        return value.lower()


# ==============================================
# 📥 CREATE ORDER ITEM SCHEMA 
# ==============================================

class OrderItemCreate(BaseModel):
    """
    مخطط إنشاء عنصر طلب.

    Attributes:
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        options: قائمة الخيارات (اختياري)
    """
    order_id: int = Field(  # ← ← ← أضفنا هذا
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
        ge=1,
    )
    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
        ge=1,
    )
    product_name: str = Field(
        ...,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
        min_length=1,
    )
    unit_price: float = Field(
        ...,
        gt=0,
        description="سعر الوحدة",
        json_schema_extra={"example": 25.00},
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="الكمية",
        json_schema_extra={"example": 2},
    )
    total_price: float = Field(
        ...,
        gt=0,
        description="السعر الإجمالي",
        json_schema_extra={"example": 50.00},
    )
    options: Optional[List[OrderOptionPayload]] = Field(
        None,
        description="قائمة الخيارات",
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class OrderUpdate(BaseModel):
    """
    مخطط تحديث الطلب - جميع الحقول اختيارية.

    Attributes:
        branch_id: معرف الفرع
        table_id: معرف الطاولة
        employee_id: معرف الموظف
        customer_name: اسم العميل
        customer_phone: رقم هاتف العميل
        delivery_address: عنوان التوصيل
        customer_note: ملاحظات العميل
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
    """
    branch_id: Optional[int] = Field(
        None,
        description="معرف الفرع",
        json_schema_extra={"example": 1},
    )
    table_id: Optional[int] = Field(
        None,
        description="معرف الطاولة",
        json_schema_extra={"example": 1},
    )
    employee_id: Optional[int] = Field(
        None,
        description="معرف الموظف",
        json_schema_extra={"example": 1},
    )
    customer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم العميل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    customer_phone: Optional[str] = Field(
        None,
        max_length=50,
        description="رقم هاتف العميل",
        json_schema_extra={"example": "0555123456"},
    )
    delivery_address: Optional[str] = Field(
        None,
        description="عنوان التوصيل",
        json_schema_extra={"example": "شارع الأندلس، الجزائر"},
    )
    customer_note: Optional[str] = Field(
        None,
        description="ملاحظات العميل",
        json_schema_extra={"example": "الرجاء إضافة صوص إضافي"},
    )
    subtotal_amount: Optional[float] = Field(
        None,
        ge=0,
        description="المبلغ الإجمالي قبل الخصم",
        json_schema_extra={"example": 100.00},
    )
    discount_amount: Optional[float] = Field(
        None,
        ge=0,
        description="مبلغ الخصم",
        json_schema_extra={"example": 10.00},
    )
    tax_amount: Optional[float] = Field(
        None,
        ge=0,
        description="مبلغ الضريبة",
        json_schema_extra={"example": 15.00},
    )
    delivery_amount: Optional[float] = Field(
        None,
        ge=0,
        description="مبلغ التوصيل",
        json_schema_extra={"example": 5.00},
    )
    total_amount: Optional[float] = Field(
        None,
        ge=0,
        description="المبلغ النهائي",
        json_schema_extra={"example": 110.00},
    )


# ==============================================
# 📤 STATUS UPDATE SCHEMA
# ==============================================

class OrderStatusUpdate(BaseModel):
    """
    مخطط تحديث حالة الطلب.

    Attributes:
        status: الحالة الجديدة
        note: ملاحظة إضافية
        employee_id: معرف الموظف
    """
    status: str = Field(
        ...,
        max_length=50,
        description="الحالة الجديدة",
        json_schema_extra={"example": "confirmed"},
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="ملاحظة إضافية",
        json_schema_extra={"example": "تم تأكيد الطلب"},
    )
    employee_id: Optional[int] = Field(
        None,
        description="معرف الموظف",
        json_schema_extra={"example": 1},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """
        التحقق من صحة حالة الطلب.

        Args:
            value: حالة الطلب

        Returns:
            str: حالة الطلب المدققة

        Raises:
            ValueError: إذا كانت الحالة غير صالحة
        """
        valid_statuses = {
            "pending",
            "confirmed",
            "preparing",
            "ready",
            "delivering",
            "delivered",
            "completed",
            "cancelled",
        }
        if value.lower() not in valid_statuses:
            raise ValueError(
                f"حالة الطلب يجب أن تكون واحدة من: {', '.join(valid_statuses)}"
            )
        return value.lower()


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class OrderResponse(OrderBase):
    """
    مخطط استجابة الطلب - يحتوي على جميع الحقول بما فيها التواريخ.

    Attributes:
        id: معرف الطلب
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الطلب",
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

class OrderListResponse(BaseModel):
    """
    مخطط استجابة قائمة الطلبات.

    Attributes:
        items: قائمة الطلبات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[OrderResponse] = Field(
        ...,
        description="قائمة الطلبات",
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
# 📋 ORDER WITH ITEMS RESPONSE
# ==============================================

class OrderWithItemsResponse(OrderResponse):
    """
    مخطط استجابة الطلب مع عناصره.

    Attributes:
        items: قائمة عناصر الطلب
        payments: قائمة مدفوعات الطلب
        status_history: قائمة تاريخ الحالات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="قائمة عناصر الطلب",
    )
    payments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="قائمة مدفوعات الطلب",
    )
    status_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="قائمة تاريخ الحالات",
    )


# ==============================================
# 📊 ORDER SUMMARY
# ==============================================

class OrderSummary(BaseModel):
    """
    مخطط ملخص الطلبات.

    Attributes:
        total_orders: إجمالي عدد الطلبات
        pending_orders: عدد الطلبات المعلقة
        confirmed_orders: عدد الطلبات المؤكدة
        preparing_orders: عدد الطلبات قيد التحضير
        ready_orders: عدد الطلبات الجاهزة
        delivering_orders: عدد الطلبات قيد التوصيل
        delivered_orders: عدد الطلبات الموصلة
        completed_orders: عدد الطلبات المكتملة
        cancelled_orders: عدد الطلبات الملغاة
        total_revenue: إجمالي الإيرادات
        avg_order_value: متوسط قيمة الطلب
    """
    model_config = ConfigDict(from_attributes=True)

    total_orders: int = Field(
        ...,
        description="إجمالي عدد الطلبات",
        json_schema_extra={"example": 100},
        ge=0,
    )
    pending_orders: int = Field(
        ...,
        description="عدد الطلبات المعلقة",
        json_schema_extra={"example": 10},
        ge=0,
    )
    confirmed_orders: int = Field(
        ...,
        description="عدد الطلبات المؤكدة",
        json_schema_extra={"example": 15},
        ge=0,
    )
    preparing_orders: int = Field(
        ...,
        description="عدد الطلبات قيد التحضير",
        json_schema_extra={"example": 20},
        ge=0,
    )
    ready_orders: int = Field(
        ...,
        description="عدد الطلبات الجاهزة",
        json_schema_extra={"example": 5},
        ge=0,
    )
    delivering_orders: int = Field(
        ...,
        description="عدد الطلبات قيد التوصيل",
        json_schema_extra={"example": 8},
        ge=0,
    )
    delivered_orders: int = Field(
        ...,
        description="عدد الطلبات الموصلة",
        json_schema_extra={"example": 12},
        ge=0,
    )
    completed_orders: int = Field(
        ...,
        description="عدد الطلبات المكتملة",
        json_schema_extra={"example": 25},
        ge=0,
    )
    cancelled_orders: int = Field(
        ...,
        description="عدد الطلبات الملغاة",
        json_schema_extra={"example": 5},
        ge=0,
    )
    total_revenue: float = Field(
        ...,
        description="إجمالي الإيرادات",
        json_schema_extra={"example": 10000.00},
        ge=0,
    )
    avg_order_value: float = Field(
        ...,
        description="متوسط قيمة الطلب",
        json_schema_extra={"example": 100.00},
        ge=0,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Payloads
    "OrderOptionPayload",
    "OrderItemPayload",

    # Order
    "OrderBase",
    "OrderCreate",
    "OrderItemCreate",
    "OrderUpdate",
    "OrderStatusUpdate",
    "OrderResponse",
    "OrderListResponse",
    "OrderWithItemsResponse",
    "OrderSummary",

    # Types
    "OrderData",
    "OrderUpdateData",
    "OrderListData",
]