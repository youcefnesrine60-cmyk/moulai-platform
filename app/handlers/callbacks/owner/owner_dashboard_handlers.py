# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / OWNER / OWNER DASHBOARD HANDLERS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for owner dashboard handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.database import get_session
from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit
from app.helpers.ui_manager import UIManager
from app.models.restaurant import Restaurant
from app.repositories.categories_repo import CategoriesRepository
from app.repositories.orders_repo import OrdersRepository
from app.repositories.owner_repo import OwnerRepository
from app.repositories.products_repo import ProductRepository

# ✅ استيراد الـ Repositories الصحيحة
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.repositories.state_repo import get_state, set_state

# ✅ استيراد واجهات الـ UI
from app.views.owner_dashboard_ui import owner_dashboard_ui
from app.views.ui import button


async def _owned_restaurant(
    *, session: AsyncSession, chat_id: int, restaurant_id: int
) -> Restaurant | None:
    """Resolve the owner's restaurant before reading its private dashboard data."""
    owners = OwnerRepository(session=session)
    owners.query_options = [raiseload("*")]
    owner = await owners.get_by_chat_id(chat_id=chat_id)
    if owner is None:
        return None
    restaurants = RestaurantRepository(session)
    restaurants.query_options = [raiseload("*")]
    restaurant = await restaurants.get_by_id(id=restaurant_id)
    if restaurant is None or restaurant.owner_id != owner.id:
        return None
    return restaurant


# ==============================================
# 🏪 OWNER DASHBOARD
# عرض لوحة تحكم صاحب المحل
# ==============================================


# ==============================================
# OWNER DASHBOARD CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="owner_dashboard",
)
async def owner_dashboard_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض لوحة تحكم صاحب المحل

    Args:
        chat_id: معرف المستخدم
        message_id: معرف الرسالة
        callback_data: بيانات الكولباك
        match: النمط المطابق
    """
    logger.info(
        "owner_dashboard_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # ==========================================
    # 1️⃣ استخراج معرف المطعم من callback_data
    # ==========================================

    try:
        restaurant_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "owner_dashboard_invalid_restaurant_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    # ==========================================
    # 2️⃣ جلب بيانات المطعم
    # ==========================================

    async with await get_session() as session:
        restaurant_model = await _owned_restaurant(
            session=session,
            chat_id=chat_id,
            restaurant_id=restaurant_id,
        )

    restaurant = (
        {"id": restaurant_model.id, "name": restaurant_model.name}
        if restaurant_model is not None
        else None
    )

    if not restaurant:
        logger.warning(
            "owner_dashboard_restaurant_not_found",
            extra={
                "chat_id": chat_id,
                "restaurant_id": restaurant_id,
            },
        )

        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ المطعم غير موجود.",
            reply_markup=None,
        )
        return

    # ==========================================
    # 3️⃣ جلب الإحصائيات
    # ==========================================

    # 📦 عدد الطلبات الكلي
    async with await get_session() as session:
        order_models = await OrdersRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )
    orders = [
        {
            "status": order.status,
            "total_amount": order.total_amount,
        }
        for order in order_models
    ]
    orders_count = len(orders)

    # ⏳ عدد الطلبات المعلقة
    pending_orders = [
        o
        for o in orders
        if o.get("status") in ["received", "preparing", "ready", "delivering"]
    ]
    pending_count = len(pending_orders)

    # 🍔 عدد المنتجات
    async with await get_session() as session:
        products_count = await ProductRepository(session).count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    # 💰 حساب الإيرادات (مجموع الطلبات المكتملة)
    completed_orders = [o for o in orders if o.get("status") == "completed"]
    revenue = sum(float(o.get("total_amount", 0)) for o in completed_orders)

    # ==========================================
    # 4️⃣ حفظ حالة المستخدم
    # ==========================================

    state = await get_state(chat_id=chat_id)

    if not state:
        state = {}

    state["restaurant_id"] = restaurant_id
    state["step"] = "owner_dashboard"

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # ==========================================
    # 5️⃣ عرض لوحة التحكم
    # ==========================================

    dashboard_ui = await owner_dashboard_ui(
        restaurant_id=restaurant_id,
        restaurant_name=restaurant.get("name", "مطعم"),
        orders_count=orders_count,
        pending_orders=pending_count,
        products_count=products_count,
        revenue=revenue,
    )

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=dashboard_ui.get("text", "🏪 لوحة تحكم المطعم"),
        reply_markup=dashboard_ui.get("inline_keyboard"),
    )


# ==============================================
# 📦 OWNER ORDERS MANAGEMENT
# إدارة طلبات المطعم
# ==============================================


# ==============================================
# OWNER ORDERS CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="owner_orders",
)
async def owner_orders_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض وإدارة طلبات المطعم

    Args:
        chat_id: معرف المستخدم
        message_id: معرف الرسالة
        callback_data: بيانات الكولباك
        match: النمط المطابق
    """
    logger.info(
        "owner_orders_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # استخراج معرف المطعم
    try:
        restaurant_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "owner_orders_invalid_restaurant_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    # جلب الطلبات
    async with await get_session() as session:
        if (
            await _owned_restaurant(
                session=session, chat_id=chat_id, restaurant_id=restaurant_id
            )
            is None
        ):
            await UIManager.edit(
                chat_id=chat_id,
                message_id=message_id,
                text="⛔ لا يمكنك الوصول إلى هذا المطعم.",
                reply_markup=None,
            )
            return
        order_models = await OrdersRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )
    orders = [
        {
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
        }
        for order in order_models
    ]

    if not orders:
        text = "📦 لا توجد طلبات حالياً."
    else:
        # بناء قائمة الطلبات
        orders_text = ""
        for order in orders[:10]:  # عرض آخر 10 طلبات فقط
            order_number = order.get("order_number", "N/A")
            status = order.get("status", "unknown")
            total = order.get("total_amount", 0)

            status_emoji = {
                "received": "📥",
                "preparing": "👨‍🍳",
                "ready": "✅",
                "delivering": "🛵",
                "completed": "📦",
                "cancelled": "❌",
            }.get(status, "❓")

            orders_text += f"{status_emoji} #{order_number} - {total:.2f} دج\n"

        text = (
            f"📦 **إدارة الطلبات**\n\n{orders_text}\n📊 إجمالي الطلبات: {len(orders)}"
        )

    buttons = [
        [
            await button(
                text="🔄 تحديث",
                callback=f"owner_orders_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى لوحة التحكم",
                callback=f"owner_dashboard_{restaurant_id}",
            ),
        ],
    ]

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup={
            "inline_keyboard": buttons,
        },
    )


# ==============================================
# 🍔 OWNER PRODUCTS MANAGEMENT
# إدارة منتجات المطعم
# ==============================================


# ==============================================
# OWNER PRODUCTS CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="owner_products",
)
async def owner_products_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض وإدارة منتجات المطعم

    Args:
        chat_id: معرف المستخدم
        message_id: معرف الرسالة
        callback_data: بيانات الكولباك
        match: النمط المطابق
    """
    logger.info(
        "owner_products_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # استخراج معرف المطعم
    try:
        restaurant_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "owner_products_invalid_restaurant_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    # جلب المنتجات
    async with await get_session() as session:
        if (
            await _owned_restaurant(
                session=session, chat_id=chat_id, restaurant_id=restaurant_id
            )
            is None
        ):
            await UIManager.edit(
                chat_id=chat_id,
                message_id=message_id,
                text="⛔ لا يمكنك الوصول إلى هذا المطعم.",
                reply_markup=None,
            )
            return
        products_count = await ProductRepository(session).count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    # جلب الأقسام
    async with await get_session() as session:
        category_models = await CategoriesRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

    categories = [{"name": category.name} for category in category_models]

    text = (
        f"🍔 **إدارة المنتجات**\n\n"
        f"📊 عدد المنتجات: {products_count}\n"
        f"📂 عدد الأقسام: {len(categories)}\n\n"
        f"📋 **الأقسام:**\n"
    )

    if categories:
        for cat in categories:
            text += f"• {cat.get('name', 'غير محدد')}\n"
    else:
        text += "⚠️ لا توجد أقسام بعد.\n"

    text += "\n💡 لإضافة منتج جديد، استخدم الأمر /add_product"

    buttons = [
        [
            await button(
                text="➕ إضافة منتج",
                callback=f"owner_add_product_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="📂 إضافة قسم",
                callback=f"owner_add_category_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى لوحة التحكم",
                callback=f"owner_dashboard_{restaurant_id}",
            ),
        ],
    ]

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup={
            "inline_keyboard": buttons,
        },
    )
