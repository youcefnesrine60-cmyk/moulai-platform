# ==============================================
# 🍽️ RESTAURANT DETAILS
# عرض تفاصيل المطعم
# ==============================================

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager

from app.repositories.restaurant.restaurant_repo import get_restaurant_by_id
from app.repositories.branches_repo import get_restaurant_branches
from app.repositories.products_repo import count_restaurant_products

from app.views.ui import button


# ==============================================
# 🍽️ RESTAURANT DETAILS
# عرض تفاصيل المطعم
# ==============================================

@rate_limit(
    limit=10,
    window=30,
    key_prefix="restaurant_details",
)
async def restaurant_details_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض تفاصيل المطعم للزبون
    """
    try:
        restaurant_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "restaurant_details_invalid_restaurant_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "restaurant_details_callback",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant_id,
        },
    )

    # جلب بيانات المطعم
    restaurant = await get_restaurant_by_id(
        restaurant_id=restaurant_id,
    )

    if not restaurant:
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ المطعم غير موجود.",
            reply_markup=None,
        )
        return

    # جلب الفروع
    branches = await get_restaurant_branches(
        restaurant_id=restaurant_id,
    )

    # جلب عدد المنتجات
    products_count = await count_restaurant_products(
        restaurant_id=restaurant_id,
    )

    # بناء الرسالة
    branches_text = "\n".join(
        f"• {b.get('name', 'فرع')} - {b.get('wilaya', 'غير محدد')}"
        for b in branches[:3]
    ) if branches else "⚠️ لا توجد فروع."

    text = (
        f"🍽️ **{restaurant.get('name', 'مطعم')}**\n\n"
        f"📞 الهاتف: {restaurant.get('phone', 'غير محدد')}\n"
        f"📍 الولاية: {restaurant.get('wilaya', 'غير محدد')}\n"
        f"🍔 عدد المنتجات: {products_count}\n"
        f"🏢 الفروع:\n{branches_text}\n"
    )

    # أزرار
    buttons = [
        [
            await button(
                text="📋 عرض القائمة",
                callback=f"restaurant_menu_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="📍 عرض الموقع",
                callback=f"restaurant_location_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى المطاعم",
                callback="show_restaurants",
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