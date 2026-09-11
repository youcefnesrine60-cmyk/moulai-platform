# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDERS SERVICE - CREATE
# إنشاء الطلب 
# (create_restaurant_order, create_order_with_items)
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import ValidationError

from app.core.logger import logger
from app.repositories.order_item_options_repo import (
    OrderItemOptionsRepository,
)
from app.repositories.order_items_repo import OrderItemsRepository
from app.repositories.orders_repo import OrdersRepository
from app.repositories.order_status_history_repo import (
    OrderStatusHistoryRepository,
)
from app.repositories.restaurant.restaurant_metrics_repo import (
    RestaurantMetricsRepository,
)
from app.repositories.restaurant.restaurant_order_counters_repo import (
    RestaurantOrderCountersRepository,
)
from app.services.business.feature_usage_counter_engine import increase_usage
from app.services.business.orders.constants import ORDERS_FEATURE_ID

# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemPayload = Dict[str, Any]
OrderItemOptionPayload = Dict[str, Any]


# ==============================================
# ➕ CREATE ORDER
# ==============================================

async def create_restaurant_order(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    order_number: str,
    order_type: str,
    customer_name: Optional[str],
    customer_phone: Optional[str],
    delivery_address: Optional[str],
    customer_note: Optional[str],
    subtotal_amount: float = 0,
    discount_amount: float = 0,
    tax_amount: float = 0,
    delivery_amount: float = 0,
    total_amount: float = 0,
    session: AsyncSession,
) -> int:
    """
    إنشاء طلب جديد.
    
    Args:
        restaurant_id: معرف المطعم
        branch_id: معرف الفرع (اختياري)
        table_id: معرف الطاولة (اختياري)
        employee_id: معرف الموظف (اختياري)
        order_number: رقم الطلب
        order_type: نوع الطلب (dine_in, delivery, takeaway)
        customer_name: اسم العميل (اختياري)
        customer_phone: هاتف العميل (اختياري)
        delivery_address: عنوان التوصيل (اختياري)
        customer_note: ملاحظة العميل (اختياري)
        subtotal_amount: المجموع الفرعي
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المجموع الكلي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف الطلب الجديد
        
    Raises:
        ValidationError: إذا كانت البيانات غير صالحة
    """
    # 1️⃣ التحقق من صحة البيانات
    if not order_number:
        raise ValidationError(
            message="رقم الطلب مطلوب",
        )

    if order_type not in ["dine_in", "delivery", "takeaway"]:
        raise ValidationError(
            message=f"نوع الطلب '{order_type}' غير صالح",
            details={
                "order_type": order_type,
                "valid_types": ["dine_in", "delivery", "takeaway"],
            },
        )

    if total_amount < 0:
        raise ValidationError(
            message="المبلغ الإجمالي لا يمكن أن يكون سالباً",
        )

    logger.info(
        "create_restaurant_order_started",
        extra={
            "restaurant_id": restaurant_id,
            "order_number": order_number,
            "order_type": order_type,
        },
    )

    # 2️⃣ إنشاء الطلب
    orders_repo = OrdersRepository(session=session)

    data: Dict[str, Any] = {
        "restaurant_id": restaurant_id,
        "branch_id": branch_id,
        "table_id": table_id,
        "employee_id": employee_id,
        "order_number": order_number,
        "order_type": order_type,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "delivery_address": delivery_address,
        "customer_note": customer_note,
        "status": "pending",
        "subtotal_amount": subtotal_amount,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "delivery_amount": delivery_amount,
        "total_amount": total_amount,
        "is_paid": False,
    }

    order = await orders_repo.create(data=data)
    order_id = order.id

    # 3️⃣ إنشاء سجل الحالة الأولي
    history_repo = OrderStatusHistoryRepository(session=session)

    await history_repo.create(
        data={
            "order_id": order_id,
            "status": "pending",
            "employee_id": employee_id,
            "note": f"تم إنشاء الطلب #{order_number}",
        },
    )

    # 4️⃣ زيادة عداد استخدام الميزة
    await increase_usage(
        restaurant_id=restaurant_id,
        feature_id=ORDERS_FEATURE_ID,
    )

    # 5️⃣ تحديث مقاييس المطعم
    await _update_restaurant_metrics(
        session=session,
        restaurant_id=restaurant_id,
        order_total=total_amount,
    )

    logger.info(
        "restaurant_order_created_successfully",
        extra={
            "order_id": order_id,
            "restaurant_id": restaurant_id,
            "order_number": order_number,
        },
    )

    return order_id


# ==============================================
# 🚀 CREATE ORDER WITH ITEMS
# ==============================================

async def create_order_with_items(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    order_type: str,
    customer_name: Optional[str],
    customer_phone: Optional[str],
    delivery_address: Optional[str],
    customer_note: Optional[str],
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    delivery_amount: float,
    total_amount: float,
    items: List[OrderItemPayload],
    session: AsyncSession,
) -> int:
    """
    إنشاء طلب مع عناصره في معاملة واحدة.
    
    Args:
        restaurant_id: معرف المطعم
        branch_id: معرف الفرع (اختياري)
        table_id: معرف الطاولة (اختياري)
        employee_id: معرف الموظف (اختياري)
        order_type: نوع الطلب
        customer_name: اسم العميل (اختياري)
        customer_phone: هاتف العميل (اختياري)
        delivery_address: عنوان التوصيل (اختياري)
        customer_note: ملاحظة العميل (اختياري)
        subtotal_amount: المجموع الفرعي
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المجموع الكلي
        items: قائمة عناصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف الطلب الجديد
        
    Raises:
        ValidationError: إذا كانت البيانات غير صالحة أو كانت قائمة العناصر فارغة
        NotFoundError: إذا لم يتم العثور على المطعم
    """
    # 1️⃣ التحقق من صحة البيانات
    if order_type not in ["dine_in", "delivery", "takeaway"]:
        raise ValidationError(
            message=f"نوع الطلب '{order_type}' غير صالح",
            details={
                "order_type": order_type,
                "valid_types": ["dine_in", "delivery", "takeaway"],
            },
        )

    if not items:
        raise ValidationError(
            message="الطلب يجب أن يحتوي على عنصر واحد على الأقل",
        )

    if total_amount < 0:
        raise ValidationError(
            message="المبلغ الإجمالي لا يمكن أن يكون سالباً",
        )

    logger.info(
        "create_order_with_items_started",
        extra={
            "restaurant_id": restaurant_id,
            "order_type": order_type,
            "items_count": len(items),
        },
    )

    # 2️⃣ إنشاء الطلب
    orders_repo = OrdersRepository(session=session)
    order_items_repo = OrderItemsRepository(session=session)
    options_repo = OrderItemOptionsRepository(session=session)
    history_repo = OrderStatusHistoryRepository(session=session)
    counters_repo = RestaurantOrderCountersRepository(session=session)

    # 3️⃣ توليد رقم الطلب
    # التحقق من وجود عداد الطلبات
    counter = await counters_repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
    )

    if not counter:
        # إنشاء عداد جديد إذا لم يكن موجوداً
        await counters_repo.create_counter(restaurant_id=restaurant_id)
        counter = await counters_repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

    order_number = await counters_repo.generate_next_order_number(
        restaurant_id=restaurant_id,
    )

    # 4️⃣ إنشاء الطلب
    order_data: Dict[str, Any] = {
        "restaurant_id": restaurant_id,
        "branch_id": branch_id,
        "table_id": table_id,
        "employee_id": employee_id,
        "order_number": order_number,
        "order_type": order_type,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "delivery_address": delivery_address,
        "customer_note": customer_note,
        "status": "pending",
        "subtotal_amount": subtotal_amount,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "delivery_amount": delivery_amount,
        "total_amount": total_amount,
        "is_paid": False,
    }

    order = await orders_repo.create(data=order_data)
    order_id = order.id

    # 5️⃣ إنشاء عناصر الطلب
    for item in items:
        # التحقق من صحة العنصر
        if not item.get("product_id"):
            raise ValidationError(
                message="معرف المنتج مطلوب لكل عنصر",
            )

        if item.get("quantity", 0) <= 0:
            raise ValidationError(
                message=f"الكمية يجب أن تكون أكبر من الصفر للمنتج {item.get('product_name', 'غير معروف')}",
            )

        item_data: Dict[str, Any] = {
            "order_id": order_id,
            "product_id": item["product_id"],
            "product_name": item.get("product_name", "منتج غير معروف"),
            "unit_price": item["unit_price"],
            "quantity": item["quantity"],
            "total_price": item["total_price"],
        }

        order_item = await order_items_repo.create(data=item_data)
        order_item_id = order_item.id

        # 6️⃣ إنشاء خيارات العنصر
        options = item.get("options", [])

        for option in options:
            if not option.get("option_group_name") or not option.get("option_name"):
                logger.warning(
                    "invalid_option_skipped",
                    extra={
                        "order_item_id": order_item_id,
                        "option": option,
                    },
                )
                continue

            option_data: Dict[str, Any] = {
                "order_item_id": order_item_id,
                "option_group_name": option["option_group_name"],
                "option_name": option["option_name"],
                "additional_price": option.get("additional_price", 0),
            }

            await options_repo.create(data=option_data)

    # 7️⃣ إنشاء سجل الحالة الأولي
    await history_repo.create(
        data={
            "order_id": order_id,
            "status": "pending",
            "employee_id": employee_id,
            "note": f"تم إنشاء الطلب #{order_number} مع {len(items)} عنصر",
        },
    )

    # 8️⃣ تحديث مقاييس المطعم
    await _update_restaurant_metrics(
        session=session,
        restaurant_id=restaurant_id,
        order_total=total_amount,
    )

    # 9️⃣ زيادة عداد استخدام الميزة
    await increase_usage(
        restaurant_id=restaurant_id,
        feature_id=ORDERS_FEATURE_ID,
    )

    logger.info(
        "order_with_items_created_successfully",
        extra={
            "order_id": order_id,
            "restaurant_id": restaurant_id,
            "order_number": order_number,
            "items_count": len(items),
        },
    )

    return order_id


# ==============================================
# 🛠️ PRIVATE HELPERS
# ==============================================

# ==============================================
# UPDATE RESTAURANT METRICS
# ==============================================

async def _update_restaurant_metrics(
    *,
    session: AsyncSession,
    restaurant_id: int,
    order_total: float,
) -> None:
    """
    تحديث مقاييس المطعم بعد إنشاء طلب.
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        order_total: إجمالي قيمة الطلب
    """
    try:
        metrics_repo = RestaurantMetricsRepository(session=session)

        # الحصول على المقاييس الحالية
        metrics = await metrics_repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

        if metrics:
            # تحديث المقاييس الموجودة
            new_monthly_orders = (metrics.monthly_orders or 0) + 1
            old_avg = metrics.average_order_value or 0
            total_orders = metrics.monthly_orders or 0

            # حساب متوسط جديد
            if total_orders > 0:
                new_avg = ((old_avg * total_orders) + order_total) / (total_orders + 1)
            else:
                new_avg = order_total

            await metrics_repo.update(
                id=metrics.restaurant_id,
                data={
                    "monthly_orders": new_monthly_orders,
                    "average_order_value": round(new_avg, 2),
                },
            )
        else:
            # إنشاء مقاييس جديدة
            await metrics_repo.create(
                data={
                    "restaurant_id": restaurant_id,
                    "products_count": 0,
                    "categories_count": 0,
                    "monthly_orders": 1,
                    "average_order_value": round(order_total, 2),
                },
            )

        logger.info(
            "restaurant_metrics_updated_after_order",
            extra={
                "restaurant_id": restaurant_id,
                "order_total": order_total,
            },
        )

    except Exception as e:
        logger.warning(
            "restaurant_metrics_update_failed",
            extra={
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )