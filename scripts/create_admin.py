# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Provision the first normalized RBAC administrator from explicit operator data.

This bootstrap never replaces an existing identity, invents a Telegram chat ID,
or grants authority from a client-supplied role string. Run billing migrations
first. OIDC subject binding is a separate guarded billing_operations command.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Select,
    select,
    text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.logger import logger
from app.models.admin import Admin
from app.models.admin_log import AdminLog
from app.models.rbac import Role
from scripts.billing_operations import (
    BillingOperationError,
    DEPLOYMENT_LOCK_ID,
    OperationReport,
    _review_permission,
    _schema_snapshot,
    expected_head,
    operation_engine,
    validate_database_confirmation,
)

# ==============================================
# BASE ADMINISTRATOR SELECT
# ==============================================


def _base_admin_select() -> Select[Any]:
    """Read existing bootstrap identities without loading relationship graphs."""
    return select(
        Admin.id,
        Admin.chat_id,
        Admin.username,
        Admin.is_active,
        Admin.role_id,
    )


# ==============================================
# INITIAL ADMINISTRATOR PROVISIONING
# ==============================================


async def create_admin(
    *,
    database_name: str,
    chat_id: int,
    username: str,
    full_name: str,
) -> OperationReport:
    """Create the initial administrator atomically using an active RBAC role.

    Repeated provisioning of the same active administrator is harmless. Any other
    existing administrator blocks bootstrap so identity changes use an explicitly
    authenticated administrative workflow instead.
    """
    validate_database_confirmation(database_name=database_name)
    if (
        chat_id <= 0
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,31}", username) is None
        or not full_name
        or full_name != full_name.strip()
        or len(full_name) > 255
    ):
        raise BillingOperationError("explicit_valid_administrator_identity_required")
    engine = operation_engine()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": DEPLOYMENT_LOCK_ID},
            )
            snapshot = await connection.run_sync(_schema_snapshot)
            if (
                snapshot["installed_revisions"] != [expected_head()]
                or not snapshot["billing_schema_ready"]
            ):
                raise BillingOperationError(
                    "billing_schema_must_be_migrated_before_admin_bootstrap"
                )
            existing = (
                (
                    await connection.execute(
                        _base_admin_select().order_by(Admin.id).limit(2)
                    )
                )
                .mappings()
                .all()
            )
            if existing:
                if (
                    len(existing) == 1
                    and existing[0]["chat_id"] == chat_id
                    and existing[0]["username"] == username
                    and existing[0]["is_active"]
                    and await _review_permission(connection, existing[0]["role_id"])
                ):
                    return {"changed": False, "admin_id": existing[0]["id"]}
                raise BillingOperationError(
                    "administrator_bootstrap_is_already_completed"
                )
            role_id = (
                await connection.execute(
                    select(Role.id)
                    .where(Role.code == "super_admin", Role.is_active.is_(True))
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if role_id is None or not await _review_permission(connection, role_id):
                raise BillingOperationError(
                    "active_super_administrator_role_not_provisioned"
                )
            admin_id = (
                await connection.execute(
                    Admin.__table__.insert()
                    .values(
                        chat_id=chat_id,
                        username=username,
                        full_name=full_name,
                        role="super_admin",
                        role_id=role_id,
                        is_active=True,
                    )
                    .returning(Admin.id)
                )
            ).scalar_one()
            await connection.execute(
                AdminLog.__table__.insert().values(
                    admin_id=admin_id,
                    action="bootstrap_admin",
                    resource="admin",
                    resource_id=admin_id,
                    details=json.dumps(
                        {"source": "create_admin", "role_code": "super_admin"}
                    ),
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
        logger.info("initial_administrator_provisioned", extra={"admin_id": admin_id})
        return {"changed": True, "admin_id": admin_id}
    finally:
        await engine.dispose()


# ==============================================
# COMMAND-LINE ENTRY POINT
# ==============================================


def main() -> int:
    """Require concrete operator identity and an exact database confirmation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--chat-id", type=int, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    arguments = parser.parse_args()
    try:
        report = asyncio.run(
            create_admin(
                database_name=arguments.confirm_database,
                chat_id=arguments.chat_id,
                username=arguments.username,
                full_name=arguments.full_name,
            )
        )
    except Exception as error:
        reason = (
            str(error)
            if isinstance(error, BillingOperationError)
            else "administrator_bootstrap_failed"
        )
        logger.error(
            "administrator_bootstrap_failed", extra={"error_type": type(error).__name__}
        )
        print(
            json.dumps(
                {"ok": False, "reason": reason, "error_type": type(error).__name__}
            )
        )
        return 1
    print(json.dumps({"ok": True, **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
