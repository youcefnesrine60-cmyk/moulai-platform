# ==============================================
# 🏪 OWNER DASHBOARD HANDLERS
# معالجات لوحة تحكم صاحب المحل
# ==============================================

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import get_state, set_state

# ✅ استيراد الـ Repositories الصحيحة
from app.repositories.restaurant.restaurant_repo import get_restaurant_by_id
from app.repositories.orders_repo import get_restaurant_orders
from app.repositories.products_repo import count_restaurant_products
from app.repositories.categories_repo import get_restaurant_categories

# ✅ استيراد واجهات الـ UI
from app.views.owner_dashboard_ui import owner_dashboard_ui
from app.views.ui import button


# ==============================================
# 🏪 OWNER DASHBOARD
# عرض لوحة تحكم صاحب المحل
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

    restaurant = await get_restaurant_by_id(
        restaurant_id=restaurant_id,
    )

    if not restaurant:
        logger.warning(
            "owner_dashboard_restaurant_not_found",
            extra={
                "chat_id": chat_id,
                "restaurant_id": restaurant_id,
            },
        )

        await UIManager.update(
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
    orders = await get_restaurant_orders(
        restaurant_id=restaurant_id,
    )
    orders_count = len(orders)

    # ⏳ عدد الطلبات المعلقة
    pending_orders = [
        o for o in orders
        if o.get("status") in ["received", "preparing", "ready", "delivering"]
    ]
    pending_count = len(pending_orders)

    # 🍔 عدد المنتجات
    products_count = await count_restaurant_products(
        restaurant_id=restaurant_id,
    )

    # 💰 حساب الإيرادات (مجموع الطلبات المكتملة)
    completed_orders = [
        o for o in orders
        if o.get("status") == "completed"
    ]
    revenue = sum(
        float(o.get("total_amount", 0))
        for o in completed_orders
    )

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

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=dashboard_ui.get("text", "🏪 لوحة تحكم المطعم"),
        reply_markup=dashboard_ui.get("inline_keyboard"),
    )


# ==============================================
# 📦 OWNER ORDERS MANAGEMENT
# إدارة طلبات المطعم
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
    orders = await get_restaurant_orders(
        restaurant_id=restaurant_id,
    )

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
            f"📦 **إدارة الطلبات**\n\n"
            f"{orders_text}\n"
            f"📊 إجمالي الطلبات: {len(orders)}"
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

    await UIManager.update(
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
    products_count = await count_restaurant_products(
        restaurant_id=restaurant_id,
    )

    # جلب الأقسام
    categories = await get_restaurant_categories(
        restaurant_id=restaurant_id,
    )

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

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup={
            "inline_keyboard": buttons,
        },
    )