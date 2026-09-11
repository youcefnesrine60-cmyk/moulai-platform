# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 👑 ADMIN SERVICES
# خدمات المديرين
# ==============================================

# Admin Service - CRUD الأساسي
from app.services.business.admin.admin_service import (
    AdminService,
    is_admin,
    count_admins,
    get_admin_by_chat_id,
)

# Admin Log Service - سجل الأنشطة
from app.services.business.admin.admin_log_service import (
    AdminLogService,
    log_admin_action,
    audit_resource_access,
)

# Admin Session Service - جلسات المديرين
from app.services.business.admin.admin_session_service import (
    AdminSessionService,
    create_admin_session,
    logout_admin,
    logout_all_devices,
)


# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    # Admin Service
    "AdminService",
    "is_admin",
    "count_admins",
    "get_admin_by_chat_id",
    
    # Admin Log Service
    "AdminLogService",
    "log_admin_action",
    "audit_resource_access",
    
    # Admin Session Service
    "AdminSessionService",
    "create_admin_session",
    "logout_admin",
    "logout_all_devices",
]