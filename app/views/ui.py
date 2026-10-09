# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

# ==============================================
# 🌐 CONSTANTS
# ==============================================

MAP_URL = "https://youcefnesrine60-cmyk.github.io/dzeatery-map/map.html"

# ==============================================
# 🔘 BUTTON HELPER
# ==============================================


async def button(*, text: str, callback: str) -> dict:

    logger.debug("creating_button", extra={"callback": callback})

    return {"text": text, "callback_data": callback}


# ==============================================
# 🏠 MAIN MENU
# ==============================================


async def main_menu_ui() -> dict:

    logger.info("display_main_menu")

    return {
        "inline_keyboard": [
            [await button(text="🍽️ زبون مطعم", callback="customer")],
            [await button(text="🏪 صاحب محل", callback="owner")],
        ]
    }


# ==============================================
# ✅ CONSENT UI
# ==============================================


async def consent_ui(*, role: str) -> dict:

    logger.info("display_consent_ui", extra={"role": role})

    return {
        "inline_keyboard": [
            [await button(text="✅ أوافق", callback=f"consent_{role}")],
            [await button(text="❌ لا أوافق", callback="decline")],
        ]
    }


# ==============================================
# 📜 CONSENT TEXT
# ==============================================


async def consent_text() -> str:

    text = (
        "📢 <b>إشعار قانوني/خاص بالدولة الجزائرية</b>\n\n"
        "<b><u>سياسة حماية المعطيات ذات الطابع الشخصي</u></b>\n\n"
        "باستخدامك هذا البوت، فإنك توافق على معالجة بياناتك ذات الطابع الشخصي "
        "طبقاً لأحكام القانون رقم 18-07 المؤرخ في 10 يونيو 2018 "
        "المتعلق بحماية الأشخاص الطبيعيين في مجال معالجة المعطيات ذات الطابع الشخصي، "
        "المعدل والمتمم بالقانون 25-11 المؤرخ في 24 يوليو 2025.\n\n"
        "🔐 حقوقك:\n"
        "• الحق في الاطلاع على بياناتك\n"
        "• الحق في تصحيحها\n"
        "• الحق في حذفها\n"
        "• الحق في سحب الموافقة في أي وقت\n\n"
        "⚠️ بالضغط على (أوافق) فإنك تقبل هذه الشروط."
    )

    logger.info("display_consent_text", extra={"length": len(text)})

    return text


# ==============================================
# 🔙 BACK UI
# ==============================================


async def back_ui() -> dict:

    logger.info("display_back_ui")

    return {"inline_keyboard": [[await button(text="🔙 رجوع", callback="back_step")]]}


# ==============================================
# 📍 LOCATION WEBAPP UI
# ==============================================


async def location_webapp_ui() -> dict:

    logger.info("display_location_webapp_ui")

    return {
        "inline_keyboard": [
            [{"text": "📍 تحديد موقع المحل", "web_app": {"url": MAP_URL}}],
            [await button(text="🔙 رجوع", callback="back_step")],
        ]
    }


# ==============================================
# 🍽️ RESTAURANTS UI
# ==============================================


async def restaurants_ui(*, restaurants: list[dict]) -> dict:

    logger.info("display_restaurants_ui", extra={"count": len(restaurants)})

    # ==========================================
    # 🚫 EMPTY LIST
    # ==========================================

    if not restaurants:

        logger.warning("no_restaurants_found")

        return {
            "inline_keyboard": [
                [await button(text="❌ لا توجد مطاعم", callback="noop")],
                [await button(text="🔙 رجوع", callback="back_main")],
            ]
        }

    # ==========================================
    # 🍔 RESTAURANTS
    # ==========================================

    buttons = []

    for restaurant in restaurants:

        restaurant = restaurant.get("name", "Unknown")

        restaurant_id = restaurant.get("id", 0)

        logger.debug("processing_restaurant", extra={"restaurant_id": restaurant_id})

        buttons.append(
            [await button(text=f"🍔 {restaurant}", callback=f"rest_{restaurant_id}")]
        )

    # ==========================================
    # 🔙 BACK BUTTON
    # ==========================================

    buttons.append([await button(text="🔙 رجوع", callback="back_main")])

    return {"inline_keyboard": buttons}


# ==============================================
# 🍔 RESTAURANT ACTIONS UI
# ==============================================


async def restaurant_actions_ui(*, restaurant_id: int) -> dict:

    logger.info("display_restaurant_actions_ui", extra={"restaurant_id": restaurant_id})

    return {
        "inline_keyboard": [
            [await button(text="📦 طلب", callback=f"order_{restaurant_id}")],
            [await button(text="🔙 رجوع", callback="show_restaurants")],
        ]
    }


# ==============================================
# 🍽️ RESTAURANT TYPES UI
# ==============================================


async def types_ui() -> dict:

    logger.info("display_types_ui")

    return {
        "inline_keyboard": [
            [await button(text="1- مطعم تقليدي", callback="type_traditional")],
            [await button(text="2- Fast Food", callback="type_fastfood")],
            [await button(text="3- مشاوي", callback="type_grill")],
            [await button(text="4- مطعم فاخر", callback="type_luxury")],
            [await button(text="5- أكل شعبي", callback="type_popular")],
            [await button(text="6- مقهى 24 ساعة", callback="type_cafe")],
            [await button(text="7- حلويات", callback="type_sweets")],
            [await button(text="🔙 رجوع", callback="back_main")],
        ]
    }


# ==============================================
# ✅ CONFIRM UI
# ==============================================


async def confirm_ui() -> dict:

    logger.info("display_confirm_ui")

    return {
        "inline_keyboard": [
            [await button(text="✅ تأكيد التسجيل", callback="confirm")],
            [await button(text="🔙 رجوع", callback="back_main")],
        ]
    }
