# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUPS SERVICES - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.restaurant.groups.service import RestaurantGroupService
from app.services.business.restaurant.groups.handlers import (
    RestaurantGroupEventHandlers,
)
from app.services.business.restaurant.groups.branch_handlers import (
    RestaurantBranchEventHandlers,
)
from app.services.business.restaurant.groups.compat import (
    create_group,
    get_group,
    get_groups_by_owner,
    update_group,
    delete_group,
    toggle_group_active,
    add_branches_to_group,
    remove_branch_from_group,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantGroupService",
    "RestaurantGroupEventHandlers",
    "RestaurantBranchEventHandlers",
    "create_group",
    "get_group",
    "get_groups_by_owner",
    "update_group",
    "delete_group",
    "toggle_group_active",
    "add_branches_to_group",
    "remove_branch_from_group",
]
