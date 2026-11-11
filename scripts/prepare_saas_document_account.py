# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT SYNTHETIC DOCUMENT ADMINISTRATOR
# Provision one new local Keycloak account with precisely the two documentary grants, leaving existing administrators unchanged.
# ==============================================

"""Local recipe setup only; credentials stay in the protected instance directory and no remote identity is contacted."""

from __future__ import annotations

# isort: split
# ==============================================
# PINNED LOCAL PROVISIONING DEPENDENCIES
# No ambient database URL, personal account, grant inference or password output is accepted.
# ==============================================

import asyncio
import json
import secrets
import sys
from pathlib import Path

from httpx import HTTPError
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# SINGLE DELIBERATE LOCAL ACCOUNT
# Refuse an existing preparation file instead of repeating partially completed identity operations.
# ==============================================


async def prepare() -> None:
    """Create one fictitious administrator and explicitly assign both approved independent permissions."""
    configuration = resolve_instance(supplied=None)
    configuration.process_environment()
    from app.integration.provision import (
        create_account,
        create_platform_admin,
    )

    path = configuration.directory / "private/saas-document-account.json"
    if path.exists():
        raise RuntimeError("document_recipe_account_already_prepared_or_interrupted")
    username = "saas-document-admin"
    password = secrets.token_urlsafe(32)
    record = {"username": username, "password": password, "status": "prepared"}
    path.write_text(json.dumps(record), encoding="utf-8")
    result = await create_account(
        configuration=configuration, username=username, password=password
    )
    record.update(subject=result["subject"], status="identity_created")
    path.write_text(json.dumps(record), encoding="utf-8")
    grants = ("subscriptions.documents.issue", "subscriptions.documents.invalidate")
    administrator = await create_platform_admin(
        configuration=configuration,
        subject=result["subject"],
        legacy_id=-2026111101,
        permissions=grants,
    )
    record.update(status="completed", admin_id=administrator["admin_id"])
    path.write_text(json.dumps(record), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "synthetic_account": username,
                "explicit_permissions": grants,
                "existing_accounts_changed": False,
            }
        )
    )


# ==============================================
# ALLOWLISTED LOCAL ENTRY
# Surface only a failure category; credentials and provider response bodies remain private.
# ==============================================


if __name__ == "__main__":
    sys.addaudithook(IntegrationNetworkGuard())
    try:
        asyncio.run(prepare())
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        HTTPError,
        SQLAlchemyError,
    ) as error:
        print(
            json.dumps({"status": "STOPPED", "type": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
