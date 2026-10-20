# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Immutable OIDC identity data, independent of database tenant permissions."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# ==============================================
# VERIFIED IDENTITY AND REALM ROLE EXTRACTION
# ==============================================


@dataclass(frozen=True)
class OIDCPrincipal:
    """Represent verified identity only; roles grant no business ownership."""

    subject: str
    issuer: str
    realm_roles: frozenset[str]


def extract_realm_roles(*, claims: Mapping[str, Any]) -> frozenset[str]:
    """Read realm roles from already verified claims, rejecting malformed data.

    Client roles, top-level roles, and permissions are deliberately unrelated.
    An absent realm role claim represents an authenticated identity with no
    realm roles, rather than an authentication or authorization bypass.
    """
    if "realm_access" not in claims:
        return frozenset()
    realm_access = claims["realm_access"]
    if not isinstance(realm_access, dict):
        raise ValueError("Malformed realm role claims")
    roles = realm_access.get("roles", [])
    if not isinstance(roles, list) or any(
        not isinstance(role, str)
        or not role
        or role != role.strip()
        or any(ord(character) < 32 for character in role)
        for role in roles
    ):
        raise ValueError("Malformed realm role claims")
    return frozenset(roles)
