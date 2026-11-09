# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT DEVELOPMENT ACCOUNT AND COMPANY PROVISIONING
# Create genuine local Keycloak users and explicitly requested persisted associations.
# ==============================================

"""Administrative development CLI only; never a login fixture or public enrollment API."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Apply only administrator-supplied values after attesting the exact local instance.
# ==============================================

import json
import ssl
from datetime import (
    datetime,
    timezone,
)

import httpx
from sqlalchemy import (
    insert,
    text,
)
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.core.logger import logger
from app.core.security.platform_permissions import PLATFORM_PERMISSION_REFERENCE
from app.integration.config import IntegrationConfig
from app.integration.queries import base_select

# ==============================================
# CREATE ACCOUNT
# Create an actual local provider account, then one exact issuer/subject association.
# ==============================================


async def create_account(
    *, configuration: IntegrationConfig, username: str, password: str
) -> dict[str, str]:
    """Create an actual local provider account, then one exact issuer/subject association."""
    if (
        not username
        or len(username) > 80
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in username)
        or len(password) < 14
    ):
        raise ValueError("explicit_local_account_or_password_invalid")
    async with httpx.AsyncClient(
        verify=ssl.create_default_context(cafile=str(configuration.ca_file)),
        trust_env=False,
        timeout=15,
        follow_redirects=False,
    ) as client:
        response = await client.post(
            "https://127.0.0.1:8444/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "bootstrap",
                "password": configuration.admin_password,
            },
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        response = await client.post(
            "https://127.0.0.1:8444/admin/realms/moulai-local/users",
            headers=headers,
            json={
                "username": username,
                "enabled": True,
                "firstName": username,
                "lastName": "Development",
                "email": username + "@moulai.local.invalid",
                "emailVerified": True,
                "credentials": [
                    {"type": "password", "value": password, "temporary": False}
                ],
            },
        )
        response.raise_for_status()
        location = response.headers["location"]
        subject = location.rsplit("/", 1)[1]
    configuration.process_environment()
    from app.models.tenant.schema import Identity

    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine)() as session:
            from app.integration.web import attest_database

            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                session.add(
                    Identity(
                        issuer=configuration.issuer,
                        subject=subject,
                        status="active",
                        revision=1,
                    )
                )
        record = {
            "username": username,
            "issuer": configuration.issuer,
            "subject": subject,
        }
        with (configuration.directory / "provisioning.jsonl").open(
            "a", encoding="utf-8"
        ) as log:
            log.write(
                json.dumps({"kind": "development-account-created", **record}) + "\n"
            )
        logger.info(
            "Local development account association committed",
            extra={"event": "local_account_provisioned", "provider": "keycloak-local"},
        )
        return record
    finally:
        await engine.dispose()


# ==============================================
# CREATE COMPANY
# Bootstrap an explicitly requested development owner/company; grant no trial or commercial
# plan.
# ==============================================


async def create_company(
    *,
    configuration: IntegrationConfig,
    subject: str,
    name: str,
    restaurant_name: str,
    branch_name: str,
    legacy_id: int,
    permissions: tuple[str, ...],
) -> dict[str, int]:
    """Bootstrap an explicitly requested development owner/company; grant no trial or commercial plan."""
    configuration.process_environment()
    from app.core.security.tenant_types import (
        BLOCKED_B1_PERMISSIONS,
        permission_ceiling,
    )
    from app.integration.web import attest_database
    from app.models.branch import Branch
    from app.models.owner import Owner
    from app.models.tenant.schema import (
        Identity,
        Organization,
        OrganizationMembership,
        TenantRole,
        TenantRolePermission,
    )

    if (
        legacy_id >= 0
        or not all(
            value.strip() and len(value) <= 255
            for value in (subject, name, restaurant_name, branch_name)
        )
        or not {"tenant.membership.self.read", "tenant.restaurants.read"}
        <= set(permissions)
        or set(permissions) - permission_ceiling(role_code="owner")
        or set(permissions) & BLOCKED_B1_PERMISSIONS
    ):
        raise ValueError("explicit_development_company_input_invalid")
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                identity = (
                    await session.execute(
                        base_select(Identity).where(
                            Identity.issuer == configuration.issuer,
                            Identity.subject == subject,
                            Identity.status == "active",
                        )
                    )
                ).scalar_one()
                existing = (
                    (
                        await session.execute(
                            base_select(TenantRolePermission)
                            .with_only_columns(TenantRolePermission.permission_code)
                            .where(TenantRolePermission.role_code == "owner")
                        )
                    )
                    .scalars()
                    .all()
                )
                if existing and set(existing) != set(permissions):
                    raise ValueError("existing_owner_policy_would_change")
                role = await session.get(TenantRole, "owner")
                if role is None:
                    session.add(TenantRole(code="owner", policy_revision=1))
                    await session.flush()
                if not existing:
                    session.add_all(
                        [
                            TenantRolePermission(
                                role_code="owner", permission_code=code
                            )
                            for code in sorted(set(permissions))
                        ]
                    )
                owner = Owner(
                    chat_id=legacy_id,
                    auth_subject=subject,
                    full_name=name,
                    registration_status="approved",
                    trial_used=False,
                )
                organization = Organization(
                    name=name,
                    status="draft",
                    revision=1,
                    tenant_enforced_at=None,
                )
                session.add_all([owner, organization])
                await session.flush()
                session.add(
                    OrganizationMembership(
                        organization_id=organization.id,
                        identity_id=identity.id,
                        role_code="owner",
                        access_mode="company-wide",
                        status="active",
                        revision=1,
                        enrollment_generation=1,
                        accepted_at=datetime.now(timezone.utc),
                        activated_at=datetime.now(timezone.utc),
                    )
                )
                # The accepted E1 DDL owns organization_id; the legacy ORM deliberately stages it separately.
                restaurant_id = int(
                    await session.scalar(
                        text(
                            "INSERT INTO restaurants(owner_id,organization_id,name,type,phone,wilaya,is_active) VALUES (:owner,:organization,:name,'restaurant','','',true) RETURNING id"
                        ),
                        {
                            "owner": owner.id,
                            "organization": organization.id,
                            "name": restaurant_name,
                        },
                    )
                )
                branch = Branch(
                    restaurant_id=restaurant_id, name=branch_name, is_active=True
                )
                session.add(branch)
                await session.flush()
                # Membership triggers serialize ownership by advancing the organization revision.
                await session.refresh(organization)
                organization.revision += 1
                organization.status = "active"
                organization.tenant_enforced_at = datetime.now(timezone.utc)
                await session.flush()
                result = {
                    "organization_id": organization.id,
                    "restaurant_id": restaurant_id,
                    "branch_id": branch.id,
                }
        with (configuration.directory / "provisioning.jsonl").open(
            "a", encoding="utf-8"
        ) as log:
            log.write(
                json.dumps(
                    {
                        "kind": "development-company-created",
                        "subject": subject,
                        "permissions": permissions,
                        **result,
                    }
                )
                + "\n"
            )
        logger.info(
            "Local development company committed",
            extra={"event": "local_company_provisioned", **result},
        )
        return result
    finally:
        await engine.dispose()


# ==============================================
# CREATE PLATFORM ADMIN
# Explicitly provision a separate local platform administrator without tenant ownership.
# ==============================================


async def create_platform_admin(
    *,
    configuration: IntegrationConfig,
    subject: str,
    legacy_id: int,
    permissions: tuple[str, ...],
) -> dict[str, int]:
    """Explicitly provision a separate local platform administrator without tenant ownership."""
    configuration.process_environment()
    from app.integration.web import attest_database
    from app.models.admin import Admin
    from app.models.rbac import (
        Permission,
        Role,
        role_permissions,
    )

    if (
        legacy_id >= 0
        or not set(permissions) <= PLATFORM_PERMISSION_REFERENCE
        or not permissions
    ):
        raise ValueError("explicit_platform_permissions_required")
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                role = Role(
                    code="development-" + subject[:20],
                    name="Explicit local platform grants",
                    is_active=True,
                )
                session.add(role)
                await session.flush()
                for code in sorted(set(permissions)):
                    permission = (
                        await session.execute(
                            base_select(Permission).where(Permission.code == code)
                        )
                    ).scalar_one_or_none()
                    if permission is None:
                        permission = Permission(code=code, name=code)
                        session.add(permission)
                        await session.flush()
                    await session.execute(
                        insert(role_permissions).values(
                            role_id=role.id, permission_id=permission.id
                        )
                    )
                admin = Admin(
                    auth_subject=subject,
                    chat_id=legacy_id,
                    full_name="Development platform administrator",
                    role="admin",
                    role_id=role.id,
                    is_active=True,
                )
                session.add(admin)
                await session.flush()
                result = {"admin_id": admin.id}
        logger.info(
            "Explicit local platform grants committed",
            extra={
                "event": "local_platform_grants_committed",
                "admin_id": result["admin_id"],
                "grant_count": len(set(permissions)),
            },
        )
        return result
    finally:
        await engine.dispose()


# ==============================================
# CONFIGURE ROLE POLICY
# Initialize only an explicitly supplied empty local policy; refuse implicit policy
# replacement.
# ==============================================


async def configure_role_policy(
    *, configuration: IntegrationConfig, role_code: str, permissions: tuple[str, ...]
) -> dict[str, object]:
    """Initialize only an explicitly supplied empty local policy; refuse implicit policy replacement."""
    configuration.process_environment()
    from app.core.security.tenant_types import (
        BLOCKED_B1_PERMISSIONS,
        permission_ceiling,
    )
    from app.integration.web import attest_database
    from app.models.tenant.schema import (
        TenantRole,
        TenantRolePermission,
    )

    if (
        not permissions
        or set(permissions) - permission_ceiling(role_code=role_code)
        or set(permissions) & BLOCKED_B1_PERMISSIONS
    ):
        raise ValueError("explicit_role_policy_invalid")
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with async_sessionmaker(engine)() as session:
            await attest_database(session=session, configuration=configuration)
            await session.rollback()
            async with session.begin():
                existing = (
                    (
                        await session.execute(
                            base_select(TenantRolePermission)
                            .with_only_columns(TenantRolePermission.permission_code)
                            .where(TenantRolePermission.role_code == role_code)
                        )
                    )
                    .scalars()
                    .all()
                )
                if existing:
                    if set(existing) != set(permissions):
                        raise ValueError("existing_role_policy_would_change")
                else:
                    role = await session.get(TenantRole, role_code)
                    if role is None:
                        session.add(TenantRole(code=role_code, policy_revision=1))
                        await session.flush()
                    session.add_all(
                        [
                            TenantRolePermission(
                                role_code=role_code, permission_code=code
                            )
                            for code in sorted(set(permissions))
                        ]
                    )
        logger.info(
            "Explicit local role policy verified",
            extra={
                "event": "local_role_policy_verified",
                "role_code": role_code,
                "permission_count": len(set(permissions)),
            },
        )
        return {"role": role_code, "permissions": sorted(set(permissions))}
    finally:
        await engine.dispose()
