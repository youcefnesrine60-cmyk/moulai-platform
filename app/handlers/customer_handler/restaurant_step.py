# ==============================================
# 🍽️ RESTAURANT STEP
# معالجة رسائل المستخدم أثناء اختيار المطعم
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from app.core.logger import logger
from app.core.database import get_db

from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import set_state
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.repositories.products_repo import ProductRepository

from app.states.customer_states import CustomerStates


# ==============================================
# 🧩 TYPES
# ==============================================

StateData = Dict[str, Any]


# ==============================================
# 🍽️ HANDLE RESTAURANT STEP
# ==============================================

async def handle_restaurant_step(
    *,
    chat_id: int,
    text: str,
    state: StateData,
) -> None:
    """
    معالجة رسائل المستخدم في مرحلة اختيار المطعم.
    
    يقوم المستخدم بإدخال رقم المطعم، ثم نقوم بـ:
    1. التحقق من صحة الرقم
    2. جلب بيانات المطعم من قاعدة البيانات
    3. جلب قائمة المنتجات الخاصة بالمطعم
    4. حفظ البيانات في الحالة
    5. عرض قائمة المنتجات للمستخدم
    
    Args:
        chat_id: معرف المستخدم
        text: النص المرسل (رقم المطعم)
        state: حالة المستخدم الحالية
    """
    logger.info(
        "customer_restaurant_step_started",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # ==========================================
    # 1️⃣ التحقق من صحة الإدخال
    # ==========================================

    restaurant_id = await _parse_restaurant_id(
        chat_id=chat_id,
        text=text,
    )

    if restaurant_id is None:
        return

    # ==========================================
    # 2️⃣ جلب بيانات المطعم والمنتجات
    # ==========================================

    async for session in get_db():
        restaurant_repo = RestaurantRepository(session)
        product_repo = ProductRepository(session)

        # جلب بيانات المطعم
        restaurant = await restaurant_repo.get_by_id(restaurant_id)

        if not restaurant:
            await _handle_restaurant_not_found(
                chat_id=chat_id,
                restaurant_id=restaurant_id,
            )
            return

        # جلب قائمة المنتجات
        products = await product_repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_available=True,
        )

        # ==========================================
        # 3️⃣ حفظ البيانات في الحالة
        # ==========================================

        await _save_restaurant_state(
            chat_id=chat_id,
            restaurant=restaurant,
            products=products,
            state=state,
        )

        # ==========================================
        # 4️⃣ عرض قائمة المنتجات للمستخدم
        # ==========================================

        await _show_products_list(
            chat_id=chat_id,
            restaurant=restaurant,
            products=products,
        )

        logger.info(
            "restaurant_selected_successfully",
            extra={
                "chat_id": chat_id,
                "restaurant_id": restaurant.id,
                "restaurant_name": restaurant.name,
                "products_count": len(products),
            },
        )
        break


# ==========================================
# 🛠️ PRIVATE HELPERS
# ==========================================

async def _parse_restaurant_id(
    *,
    chat_id: int,
    text: str,
) -> Optional[int]:
    """
    تحويل النص إلى رقم مطعم والتحقق من صحته.
    
    Args:
        chat_id: معرف المستخدم
        text: النص المرسل
        
    Returns:
        رقم المطعم أو None إذا كان غير صالح
    """
    try:
        restaurant_id = int(text.strip())
        return restaurant_id
    except ValueError:
        logger.warning(
            "invalid_restaurant_input",
            extra={
                "chat_id": chat_id,
                "text": text,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ الرجاء إدخال رقم المطعم الصحيح.",
            reply_markup=None,
        )
        return None


async def _handle_restaurant_not_found(
    *,
    chat_id: int,
    restaurant_id: int,
) -> None:
    """
    معالجة حالة عدم وجود المطعم.
    
    Args:
        chat_id: معرف المستخدم
        restaurant_id: رقم المطعم
    """
    logger.warning(
        "restaurant_not_found",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant_id,
        },
    )

    await UIManager.update(
        chat_id=chat_id,
        text="❌ المطعم غير موجود. الرجاء المحاولة مرة أخرى.",
        reply_markup=None,
    )


async def _save_restaurant_state(
    *,
    chat_id: int,
    restaurant: Any,
    products: List[Any],
    state: StateData,
) -> None:
    """
    حفظ بيانات المطعم والمنتجات في حالة المستخدم.
    
    Args:
        chat_id: معرف المستخدم
        restaurant: كائن المطعم
        products: قائمة المنتجات
        state: حالة المستخدم الحالية
    """
    # تحديث الحالة
    state["restaurant_id"] = restaurant.id
    state["restaurant_name"] = restaurant.name
    state["products"] = products
    state["step"] = CustomerStates.PRODUCT

    # حفظ الحالة في Redis
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    logger.info(
        "restaurant_state_saved",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "products_count": len(products),
        },
    )


async def _show_products_list(
    *,
    chat_id: int,
    restaurant: Any,
    products: List[Any],
) -> None:
    """
    عرض قائمة المنتجات للمستخدم.
    
    Args:
        chat_id: معرف المستخدم
        restaurant: كائن المطعم
        products: قائمة المنتجات
    """
    if not products:
        text_message = (
            f"🍔 {restaurant.name}\n\n"
            f"⚠️ لا توجد منتجات متاحة حالياً."
        )
    else:
        # بناء قائمة المنتجات بشكل منظم
        products_text = "\n".join(
            f"{idx}. {p.name} - {p.price} دج"
            for idx, p in enumerate(products, 1)
        )

        text_message = (
            f"🍔 {restaurant.name}\n\n"
            f"📋 اختر المنتج الذي تريده بإدخال رقمه:\n\n"
            f"{products_text}\n\n"
            f"💡 يمكنك اختيار عدة منتجات، ثم الذهاب إلى السلة."
        )

    await UIManager.update(
        chat_id=chat_id,
        text=text_message,
        reply_markup=None,
    )

    logger.info(
        "products_list_shown",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant.id,
            "products_count": len(products),
        },
    )