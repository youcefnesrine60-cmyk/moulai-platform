# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT PLATFORM AUTHORITY
# Reuse stored administrator permissions without role inference or tenant-to-platform escalation.
# ==============================================

"""Caller-owned transaction; current administrator, role and exact association are locked."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.platform_permissions import PLATFORM_PERMISSION_REFERENCE
from app.models.admin import Admin
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.repositories.subscription_queries import base_select

# ==============================================
# EXACT STORED PERMISSION CHECK
# The shared vocabulary validates the requested operation but never supplies a grant.
# ==============================================


async def require_platform_permission(
    *, session: AsyncSession, principal: OIDCPrincipal, permission: str
) -> int:
    """Return the active administrator ID or deny; caller must own the request transaction."""
    if permission not in PLATFORM_PERMISSION_REFERENCE:
        raise ValueError("platform_permission_unknown")
    record = (
        await session.execute(
            base_select(Admin)
            .with_only_columns(Admin.id, Admin.role_id)
            .join(Role, Role.id == Admin.role_id)
            .where(
                Admin.auth_subject == principal.subject,
                Admin.is_active.is_(True),
                Role.is_active.is_(True),
            )
            .with_for_update(read=True, of=(Admin, Role))
        )
    ).one_or_none()
    if record is None:
        raise HTTPException(
            status_code=403, detail="Explicit platform permission required"
        )
    grant = await session.scalar(
        select(role_permissions.c.permission_id)
        .join(Permission, Permission.id == role_permissions.c.permission_id)
        .where(
            role_permissions.c.role_id == record.role_id, Permission.code == permission
        )
        .with_for_update(read=True, of=role_permissions)
    )
    if grant is None:
        raise HTTPException(
            status_code=403, detail="Explicit platform permission required"
        )
    return record.id
