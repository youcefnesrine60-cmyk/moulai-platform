# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ADMIN RBAC PERMISSIONS
# التحقق من تفويض مديري المنصة حسب الدور والصلاحيات
# ==============================================

"""Unit tests for normalized RBAC authorization in ``AdminService``."""

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security.platform_permissions import SUBSCRIPTION_PRICING_MANAGE
from app.services.business.admin.admin_service import AdminService

# ==============================================
# 🧩 TEST HELPERS
# ==============================================


def build_admin(
    *,
    active: bool = True,
    legacy_role: str = "admin",
    role_code: str | None = "admin",
    role_active: bool = True,
    permission_codes: tuple[str, ...] = (),
) -> SimpleNamespace:
    """Build an isolated administrator authorization context."""
    role_record = None
    if role_code is not None:
        role_record = SimpleNamespace(
            code=role_code,
            is_active=role_active,
            permissions=[
                SimpleNamespace(code=permission_code)
                for permission_code in permission_codes
            ],
        )

    return SimpleNamespace(
        is_active=active,
        role=legacy_role,
        role_record=role_record,
    )


def build_service(*, admin: SimpleNamespace) -> AdminService:
    """Build a service whose repository returns one isolated administrator."""
    service = AdminService(session=MagicMock())
    service.admin_repo = MagicMock()
    service.admin_repo.get_authorization_context = AsyncMock(return_value=admin)
    return service


# ==============================================
# ✅ PERMISSION AUTHORIZATION
# ==============================================


@pytest.mark.asyncio
async def test_permission_is_granted_when_attached_to_active_role() -> None:
    """An active role grants its explicitly assigned permission."""
    service = build_service(
        admin=build_admin(permission_codes=("orders.manage",)),
    )

    assert await service.check_admin_permission(
        admin_id=1,
        required_permission="orders.manage",
    )


@pytest.mark.asyncio
async def test_wildcard_permission_grants_platform_access() -> None:
    """Legacy wildcard behavior remains valid for ordinary platform permissions."""
    service = build_service(
        admin=build_admin(
            legacy_role="super_admin",
            role_code="super_admin",
            permission_codes=("*",),
        ),
    )

    assert await service.check_admin_permission(
        admin_id=1,
        required_permission="rbac.manage",
    )


# ==============================================
# EXPLICIT SAAS PRICING GRANT
# A platform title, wildcard or neighboring management permission cannot supply this grant.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "codes",
    [
        (),
        ("*",),
        ("admins.manage",),
        ("restaurants.manage",),
        ("payments.review",),
        ("admins.manage", "restaurants.manage", "payments.review"),
    ],
)
@pytest.mark.parametrize(
    "permission", ["subscriptions.pricing.manage", "tenant.billing_country.manage"]
)
async def test_pricing_permission_cannot_be_inferred(
    codes: tuple[str, ...], permission: str
) -> None:
    """Exercise the shared existing authorization mechanism without any database or grant write."""
    service = build_service(
        admin=build_admin(
            legacy_role="super_admin", role_code="super_admin", permission_codes=codes
        )
    )
    with pytest.raises(UnauthorizedError):
        await service.check_admin_permission(admin_id=1, required_permission=permission)


# ==============================================
# POSITIVE EXPLICIT PRICING AUTHORIZATION
# An active account must actually carry the new permission in its persisted authorization context.
# ==============================================


@pytest.mark.asyncio
async def test_explicit_pricing_permission_is_accepted() -> None:
    """The new strict requirement does not accidentally reject an explicitly assigned grant."""
    service = build_service(
        admin=build_admin(permission_codes=(SUBSCRIPTION_PRICING_MANAGE,))
    )
    assert await service.check_admin_permission(
        admin_id=1, required_permission=SUBSCRIPTION_PRICING_MANAGE
    )


@pytest.mark.asyncio
async def test_permission_is_denied_without_normalized_active_role() -> None:
    """Legacy role text alone cannot bypass normalized RBAC authorization."""
    service = build_service(
        admin=build_admin(role_code=None),
    )

    with pytest.raises(UnauthorizedError, match="دور RBAC نشط"):
        await service.check_admin_permission(
            admin_id=1,
            required_permission="orders.manage",
        )


@pytest.mark.asyncio
async def test_inactive_role_is_denied_even_when_it_has_permission() -> None:
    """An inactive normalized role is fail-closed."""
    service = build_service(
        admin=build_admin(
            role_active=False,
            permission_codes=("orders.manage",),
        ),
    )

    with pytest.raises(UnauthorizedError, match="دور RBAC نشط"):
        await service.check_admin_permission(
            admin_id=1,
            required_permission="orders.manage",
        )


@pytest.mark.asyncio
async def test_legacy_role_remains_available_for_role_only_checks() -> None:
    """Role-only checks retain transition compatibility until role_id is backfilled."""
    service = build_service(
        admin=build_admin(
            legacy_role="support",
            role_code=None,
        ),
    )

    assert await service.check_admin_permission(
        admin_id=1,
        required_role="support",
    )
