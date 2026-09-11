# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDERS SERVICE - PACKAGE
# حزمة خدمات الطلبات
# ==============================================

# ==============================================
# 🚀 CREATE
# ==============================================

from app.services.business.orders.create import (
    create_restaurant_order,
    create_order_with_items,
)

# ==============================================
# 📖 READ
# ==============================================

from app.services.business.orders.read import (
    get_restaurant_order,
    get_order_by_number,
    get_orders,
    get_orders_by_status,
    get_order_with_details,
    count_orders_by_restaurant,
)

# ==============================================
# ✏️ UPDATE
# ==============================================

from app.services.business.orders.update import (
    change_order_status,
    update_order_totals,
    recalculate_order_totals,
    update_order,
)

# ==============================================
# 🗑️ DELETE
# ==============================================

from app.services.business.orders.delete import (
    remove_order,
)

# ==============================================
# 📦 ITEMS
# ==============================================

from app.services.business.orders.items import (
    add_item_to_order,
    remove_item_from_order,
    get_order_items_list,
    get_order_item_by_id,
    count_order_items,
    get_order_items_subtotal,
)

# ==============================================
# 💰 TOTALS
# ==============================================

from app.services.business.orders.totals import (
    calculate_order_totals,
    update_order_totals as update_totals,
    get_order_totals,
    recalculate_order_totals as recalculate,
)

# ==============================================
# 📜 STATUS HISTORY
# ==============================================

from app.services.business.orders.status_history import (
    get_status_history,
    get_order_timeline,
    get_last_status,
    get_status_history_count,
    get_orders_reached_status,
    get_status_distribution,
)

# ==============================================
# ✅ COMPLETE
# ==============================================

from app.services.business.orders.complete import (
    complete_order,
    complete_order_with_delivery_confirmation,
)

# ==============================================
# ❌ CANCEL
# ==============================================

from app.services.business.orders.cancel import (
    cancel_order,
    cancel_order_with_refund,
)

# ==============================================
# 💳 PAID
# ==============================================

from app.services.business.orders.paid import (
    mark_order_paid,
    is_order_paid,
    get_order_payment_status,
)

# ==============================================
# 🛠️ HELPERS
# ==============================================

from app.services.business.orders.helpers import (
    check_order_editable,
    check_order_editable_from_dict,
    check_order_editable_by_status,
    is_order_editable,
)

# ==============================================
# 📋 CONSTANTS
# ==============================================

from app.services.business.orders.constants import (
    ORDERS_FEATURE_ID,
    LOCKED_STATUSES,
    ALLOWED_TRANSITIONS,
    STATUS_DISPLAY_NAMES,
    STATUS_COLORS,
    STATUS_ORDER,
    STATUS_DESCRIPTIONS,
)


# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    
    # Create
    "create_restaurant_order",
    "create_order_with_items",
    
    # Read
    "get_restaurant_order",
    "get_order_by_number",
    "get_orders",
    "get_orders_by_status",
    "get_order_with_details",
    "count_orders_by_restaurant",
    
    # Update
    "change_order_status",
    "update_order_totals",
    "recalculate_order_totals",
    "update_order",
    
    # Delete
    "remove_order",
    
    # Items
    "add_item_to_order",
    "remove_item_from_order",
    "get_order_items_list",
    "get_order_item_by_id",
    "count_order_items",
    "get_order_items_subtotal",
    
    # Totals
    "calculate_order_totals",
    "update_totals",
    "get_order_totals",
    "recalculate",
    
    # Status History
    "get_status_history",
    "get_order_timeline",
    "get_last_status",
    "get_status_history_count",
    "get_orders_reached_status",
    "get_status_distribution",
    
    # Complete
    "complete_order",
    "complete_order_with_delivery_confirmation",
    
    # Cancel
    "cancel_order",
    "cancel_order_with_refund",
    
    # Paid
    "mark_order_paid",
    "is_order_paid",
    "get_order_payment_status",
    
    # Helpers
    "check_order_editable",
    "check_order_editable_from_dict",
    "check_order_editable_by_status",
    "is_order_editable",
    
    # Constants
    "ORDERS_FEATURE_ID",
    "LOCKED_STATUSES",
    "ALLOWED_TRANSITIONS",
    "STATUS_DISPLAY_NAMES",
    "STATUS_COLORS",
    "STATUS_ORDER",
    "STATUS_DESCRIPTIONS",
]