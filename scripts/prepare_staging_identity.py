# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SECRET-FREE STAGING REALM MANIFEST
# Generate exact HTTPS callbacks and a tester admission scope without importing
# local users, client secrets, tenant roles or business permissions.
# ==============================================

"""Preparation only: this command never contacts or configures Keycloak."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT IDENTITY INPUTS
# Operator-supplied public URLs are validated before a manifest can be reviewed.
# ==============================================

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

# ==============================================
# DEDICATED REALM AND CONFIDENTIAL CODE CLIENT
# The environment role admits testers only and grants no restaurant authority.
# ==============================================


def realm_manifest(*, origin: str, client_id: str, audience: str) -> dict[str, object]:
    """Return a no-user/no-secret realm with exact callback and PKCE requirements."""
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or not client_id
        or not audience
    ):
        raise ValueError("staging_exact_https_origin_required")
    return {
        "realm": "moulai-staging",
        "enabled": True,
        "sslRequired": "external",
        "registrationAllowed": False,
        "resetPasswordAllowed": False,
        "rememberMe": False,
        "accessTokenLifespan": 300,
        "roles": {
            "realm": [
                {
                    "name": "moulai-staging-tester",
                    "description": "Synthetic acceptance host access only; no business authority",
                }
            ]
        },
        "users": [],
        "scopeMappings": [{"client": client_id, "roles": ["moulai-staging-tester"]}],
        "clients": [
            {
                "clientId": client_id,
                "protocol": "openid-connect",
                "enabled": True,
                "publicClient": False,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "fullScopeAllowed": False,
                "redirectUris": [origin + "/api/web/auth/callback"],
                "webOrigins": [origin],
                "defaultClientScopes": ["profile", "roles"],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "protocolMappers": [
                    {
                        "name": "staging-api-audience",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.custom.audience": audience,
                            "access.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    }
                ],
            }
        ],
    }


# ==============================================
# REVIEW ARTIFACT OUTPUT
# Do not import or modify an existing realm implicitly.
# ==============================================


def main() -> int:
    """Write a new public manifest only when its output path does not already exist."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--audience", required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    value = realm_manifest(
        origin=options.origin, client_id=options.client_id, audience=options.audience
    )
    with options.output.open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(value, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
