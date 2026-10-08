from app.services.business.orders.items import add_item_to_order
from app.services.business.orders.pricing import catalog_item, MAX_ITEMS_PER_ORDER
from app.services.business.orders.totals import compute_order_totals
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

from app.services.business.orders.transaction import transactional_order

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import NotFoundError, ValidationError

from app.core.logger import logger
from app.models.restaurant import Restaurant
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

@transactional_order
async def create_restaurant_order(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    user_id: Optional[int] = None,
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
    restaurant_result = await session.execute(
        select(Restaurant)
        .where(Restaurant.id == restaurant_id)
        .with_for_update(),
    )
    if not restaurant_result.scalar_one_or_none():
        raise NotFoundError(message=f"المطعم بـ ID '{restaurant_id}' غير موجود")

    await validate_branch(restaurant_id=restaurant_id, branch_id=branch_id, session=session)

    if not order_number or not order_number.strip():
        counters_repo = RestaurantOrderCountersRepository(session=session)
        if not await counters_repo.get_by_restaurant_id(restaurant_id=restaurant_id):
            await counters_repo.create_counter(restaurant_id=restaurant_id)
        order_number = await counters_repo.generate_next_order_number(
            restaurant_id=restaurant_id,
        )

    order_id = await _create_restaurant_order_in_transaction(
        restaurant_id=restaurant_id,
        branch_id=branch_id,
        table_id=table_id,
        employee_id=employee_id,
        user_id=user_id,
        order_number=order_number,
        order_type=order_type,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        customer_note=customer_note,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        delivery_amount=delivery_amount,
        total_amount=total_amount,
        session=session,
    )
    return order_id

async def _create_restaurant_order_in_transaction(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    user_id: Optional[int] = None,
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
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "branch_id": branch_id,
        "table_id": table_id,
        "employee_id": employee_id,
        "order_number": order_number,
        "order_type": order_type,
        "delivery_address": delivery_address,
        "customer_note": customer_note,
        "status": "pending",
        "subtotal_amount": subtotal_amount,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "delivery_amount": delivery_amount,
        "total_amount": total_amount,
    }

    order = await orders_repo.create(data=data)
    order_id = order.id

    # 3️⃣ إنشاء سجل الحالة الأولي
    history_repo = OrderStatusHistoryRepository(session=session)

    await history_repo.create(
        data={
            "order_id": order_id,
            "old_status": None,
            "new_status": "pending",
            "changed_by_employee_id": employee_id,
            "note": f"تم إنشاء الطلب #{order_number}",
        },
    )

    # 4️⃣ زيادة عداد استخدام الميزة
    await increase_usage(
        session=session,
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

@transactional_order
async def create_order_with_items(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    user_id: Optional[int] = None,
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
    order_id = await _create_order_with_items_in_transaction(
        restaurant_id=restaurant_id,
        branch_id=branch_id,
        table_id=table_id,
        employee_id=employee_id,
        user_id=user_id,
        order_type=order_type,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        customer_note=customer_note,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        delivery_amount=delivery_amount,
        total_amount=total_amount,
        items=items,
        session=session,
    )
    return order_id

async def _create_order_with_items_in_transaction(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    user_id: Optional[int] = None,
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

    restaurant = (
        await session.execute(
            select(Restaurant)
            .where(Restaurant.id == restaurant_id)
            .with_for_update(),
        )
    ).scalar_one_or_none()
    if not restaurant:
        raise NotFoundError(message=f"المطعم بـ ID '{restaurant_id}' غير موجود")

    # 2️⃣ إنشاء الطلب
    await validate_branch(restaurant_id=restaurant_id, branch_id=branch_id, session=session)

    if len(items) > MAX_ITEMS_PER_ORDER:
        raise ValidationError(message="Too many order items")
    items = [await catalog_item(restaurant_id=restaurant_id, payload=item, session=session)
             for item in items]
    subtotal_amount, discount_amount, tax_amount, delivery_amount, total_amount = compute_order_totals(
        subtotal=sum(item["total_price"] for item in items), discount=discount_amount,
        tax=tax_amount, delivery=delivery_amount)
    if min(discount_amount, tax_amount, delivery_amount, total_amount) < 0:
        raise ValidationError(message="Invalid order amounts")

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
    order_id = await _create_restaurant_order_in_transaction(
        restaurant_id=restaurant_id, branch_id=branch_id, table_id=table_id,
        employee_id=employee_id, user_id=user_id, order_number=order_number,
        order_type=order_type, customer_name=customer_name, customer_phone=customer_phone,
        delivery_address=delivery_address, customer_note=customer_note,
        subtotal_amount=subtotal_amount, discount_amount=discount_amount,
        tax_amount=tax_amount, delivery_amount=delivery_amount,
        total_amount=total_amount, session=session,
    )
    for item in items:
        await add_item_to_order(order_id=order_id, session=session, **item)

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

    except Exception:
        logger.exception(
            "restaurant_metrics_update_failed",
            extra={"restaurant_id": restaurant_id},
        )
        raise

async def validate_branch(*, restaurant_id, branch_id, session):
    if branch_id is None:
        return
    from app.models.branch import Branch
    branch = (await session.execute(select(Branch.id).where(
        Branch.id == branch_id, Branch.restaurant_id == restaurant_id))).scalar_one_or_none()
    if branch is None:
        raise NotFoundError(message="Branch not found in this restaurant")
