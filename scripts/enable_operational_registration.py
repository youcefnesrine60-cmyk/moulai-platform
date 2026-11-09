# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT LOCAL KEYCLOAK SELF-REGISTRATION
# Enable only the existing owned realm's native account form, without changing credentials or tenant grants.
# ==============================================

"""No remote issuer, email delivery, password database, commercial account or paid service."""

from __future__ import annotations

# isort: split
# ==============================================
# PINNED LOCAL ADMINISTRATION
# Keep the bootstrap token in RAM and verify the existing TLS trust and realm identity.
# ==============================================

import asyncio
import json
import ssl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from scripts.run_operational_local import (
    IntegrationNetworkGuard,
    resolve_instance,
)

# ==============================================
# ONE LOCAL CONFIGURATION CHANGE
# Reject unreviewed realm settings before mutation and verify unchanged session/security flags afterward.
# ==============================================


async def enable_registration() -> None:
    """Enable local self-registration; do not claim email ownership or password-reset delivery."""
    configuration = resolve_instance(supplied=None)
    endpoint = "https://127.0.0.1:8444"
    async with httpx.AsyncClient(
        verify=ssl.create_default_context(cafile=str(configuration.ca_file)),
        trust_env=False,
        follow_redirects=False,
        timeout=60,
    ) as client:
        response = await client.post(
            endpoint + "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "bootstrap",
                "password": configuration.admin_password,
            },
        )
        response.raise_for_status()
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        response = await client.get(
            endpoint + "/admin/realms/moulai-local", headers=headers
        )
        response.raise_for_status()
        before = response.json()
        if (
            before.get("realm") != "moulai-local"
            or before.get("accessTokenLifespan") != 300
            or before.get("enabled") is not True
        ):
            raise RuntimeError("local_registration_realm_changed")
        if before.get("registrationAllowed") is not True:
            response = await client.put(
                endpoint + "/admin/realms/moulai-local",
                headers=headers,
                json={"registrationAllowed": True},
            )
            response.raise_for_status()
        response = await client.get(
            endpoint + "/admin/realms/moulai-local", headers=headers
        )
        response.raise_for_status()
        after = response.json()
        preserved = [
            "accessTokenLifespan",
            "sslRequired",
            "bruteForceProtected",
            "verifyEmail",
            "resetPasswordAllowed",
        ]
        if after.get("registrationAllowed") is not True or any(
            after.get(key) != before.get(key) for key in preserved
        ):
            raise RuntimeError("local_registration_postcondition_failed")
    report = {
        "status": "PASS",
        "realm": configuration.issuer,
        "registration_allowed": True,
        "email_ownership_verified": False,
        "password_reset_delivery_verified": False,
        "other_security_flags_preserved": True,
        "remote_change": False,
    }
    (
        ROOT / "artifacts/operational-followup-20261109/registration-configuration.json"
    ).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    sys.addaudithook(IntegrationNetworkGuard())
    asyncio.run(enable_registration())
