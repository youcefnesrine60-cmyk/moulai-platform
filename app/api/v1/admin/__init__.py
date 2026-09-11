# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 👑 ADMIN API
# واجهات API للمديرين
# ==============================================

from app.api.v1.admin.admin import router as admin_router
from app.api.v1.admin.admin_log import router as admin_log_router
from app.api.v1.admin.admin_session import router as admin_session_router


# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [

    # Admin
    "admin_router",
    "admin_log_router",
    "admin_session_router",
]