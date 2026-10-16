# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👑 ADMIN SERVICES
# خدمات المديرين
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# Admin Service - CRUD الأساسي
# Admin Log Service - سجل الأنشطة
from app.services.business.admin.admin_log_service import (
    AdminLogService,
)
from app.services.business.admin.admin_service import (
    AdminService,
)

# Admin Session Service - جلسات المديرين
from app.services.business.admin.admin_session_service import (
    AdminSessionService,
)

# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    # Admin Service
    "AdminService",
    # Admin Log Service
    "AdminLogService",
    # Admin Session Service
    "AdminSessionService",
]
