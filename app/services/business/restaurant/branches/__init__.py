# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCHES SERVICES - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.restaurant.branches.service import RestaurantBranchService
from app.services.business.restaurant.branches.compat import (
    create_branch,
    get_branch,
    get_branches_by_group,
    get_branches_by_restaurant,
    delete_branch,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantBranchService",
    "create_branch",
    "get_branch",
    "get_branches_by_group",
    "get_branches_by_restaurant",
    "delete_branch",
]
