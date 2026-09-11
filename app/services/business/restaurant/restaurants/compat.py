# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🔄 RESTAURANT COMPATIBILITY
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
)
from app.services.business.restaurant.restaurants.handlers import RestaurantEventHandlers
from app.services.business.restaurant.restaurants.service import RestaurantService


# ==============================================
# 📦 RESTAURANT OPERATIONS (COMPATIBILITY)
# ==============================================

# ==============================================
# CREATE RESTAURANT
# ==============================================

async def create_restaurant(
    *,
    owner_id: int,
    name: str,
    type: str,
    phone: str,
    wilaya: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    group_id: Optional[int] = None,
    is_active: bool = True,
    session: AsyncSession,
) -> int:
    """
    إنشاء مطعم جديد (دالة متوافقة مع الإصدار القديم).
    
    Returns:
        int: معرف المطعم
    """
    handlers = RestaurantEventHandlers(session=session)

    restaurant_data = RestaurantCreate(
        owner_id=owner_id,
        name=name,
        type=type,
        phone=phone,
        wilaya=wilaya,
        lat=lat,
        lng=lng,
        group_id=group_id,
        is_active=is_active,
    )

    restaurant = await handlers.create_restaurant(
        restaurant_data=restaurant_data,
    )

    return restaurant.id


# ==============================================
# GET RESTAURANT
# ==============================================

async def get_restaurant(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مطعم بالمعرف (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantService(session=session)

    try:
        restaurant = await service.get_restaurant(restaurant_id=restaurant_id)
        return restaurant.model_dump()
    except Exception:
        return None


# ==============================================
# GET RESTAURANTS
# ==============================================

async def get_restaurants(
    *,
    owner_id: int,
    session: AsyncSession,
    include_inactive: bool = False,
) -> List[Dict[str, Any]]:
    """
    الحصول على مطاعم المالك (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantService(session=session)

    restaurants = await service.get_owner_restaurants(
        owner_id=owner_id,
        include_inactive=include_inactive,
    )

    return [r.model_dump() for r in restaurants]


# ==============================================
# GET ALL RESTAURANTS
# ==============================================

async def get_all_restaurants(
    *,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع المطاعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantService(session=session)

    restaurants = await service.get_all_restaurants(
        skip=skip,
        limit=limit,
        only_active=only_active,
    )

    return [r.model_dump() for r in restaurants]


# ==============================================
# UPDATE RESTAURANT
# ==============================================

async def update_restaurant(
    *,
    restaurant_id: int,
    data: Dict[str, Any],
    session: AsyncSession,
) -> None:
    """
    تحديث مطعم (دالة متوافقة مع الإصدار القديم).
    """
    handlers = RestaurantEventHandlers(session=session)

    update_data = RestaurantUpdate(**data)

    await handlers.update_restaurant(
        restaurant_id=restaurant_id,
        update_data=update_data,
    )

    logger.info(
        "restaurant_updated",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# DELETE RESTAURANT
# ==============================================

async def delete_restaurant(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف مطعم (دالة متوافقة مع الإصدار القديم).
    """
    handlers = RestaurantEventHandlers(session=session)

    await handlers.delete_restaurant(restaurant_id=restaurant_id)

    logger.info(
        "restaurant_deleted",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# TOGGLE RESTAURANT STATUS
# ==============================================

async def toggle_restaurant_status(
    *,
    restaurant_id: int,
    is_active: bool,
    session: AsyncSession,
) -> None:
    """
    تفعيل/تعطيل مطعم (دالة متوافقة مع الإصدار القديم).
    """
    handlers = RestaurantEventHandlers(session=session)

    await handlers.toggle_restaurant_status(
        restaurant_id=restaurant_id,
        is_active=is_active,
    )

    logger.info(
        "restaurant_status_toggled",
        extra={
            "restaurant_id": restaurant_id,
            "is_active": is_active,
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "create_restaurant",
    "get_restaurant",
    "get_restaurants",
    "get_all_restaurants",
    "update_restaurant",
    "delete_restaurant",
    "toggle_restaurant_status",
]