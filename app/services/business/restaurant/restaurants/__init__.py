# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANTS SERVICES - PACKAGE INIT
# ==============================================

from app.services.business.restaurant.restaurants.service import RestaurantService
from app.services.business.restaurant.restaurants.handlers import RestaurantEventHandlers
from app.services.business.restaurant.restaurants.validators import (
    MAX_RESTAURANTS_PER_OWNER,
    VALID_RESTAURANT_TYPES,
    validate_restaurant_type,
    validate_owner_limit,
)
from app.services.business.restaurant.restaurants.compat import (
    create_restaurant,
    get_restaurant,
    get_restaurants,
    get_all_restaurants,
    update_restaurant,
    delete_restaurant,
    toggle_restaurant_status,
)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantService",
    "RestaurantEventHandlers",
    "MAX_RESTAURANTS_PER_OWNER",
    "VALID_RESTAURANT_TYPES",
    "validate_restaurant_type",
    "validate_owner_limit",
    "create_restaurant",
    "get_restaurant",
    "get_restaurants",
    "get_all_restaurants",
    "update_restaurant",
    "delete_restaurant",
    "toggle_restaurant_status",
]