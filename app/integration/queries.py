# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# INTEGRATION BASE SELECT ROOT
# Keep both staged tenant mappings and legacy business mappings on the shared declarative base.
# ==============================================

"""Typed SQL helper only; all authority predicates belong to the calling transaction."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# No connection or model-specific authorization is created by this helper.
# ==============================================

from typing import TypeVar

from sqlalchemy import (
    Select,
    select,
)

from app.models.base import Base

QueryModel = TypeVar("QueryModel", bound=Base)


# ==============================================
# PARAMETERIZED ORM ROOT
# SQL helpers keep positional model arguments, as required by the shared project convention.
# ==============================================


def base_select(model: type[QueryModel]) -> Select[tuple[QueryModel]]:
    """Build a typed root without executing SQL, changing locks or granting access."""
    return select(model)
