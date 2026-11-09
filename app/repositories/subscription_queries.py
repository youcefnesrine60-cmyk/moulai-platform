# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION BASE SELECT HELPER
# Build typed ORM SELECT roots without executing queries or granting tenant access.
# ==============================================

"""Typed BASE SELECT helper for subscription services; no session or I/O."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from typing import TypeVar

from sqlalchemy import (
    Select,
    select,
)

from app.models.base import Base

# ==============================================
# QUERY MODEL TYPE
# Keep ORM model identity in the generic SELECT return contract.
# ==============================================

QueryModel = TypeVar("QueryModel", bound=Base)


# ==============================================
# BUILD BASE SELECT
# Build an ORM SELECT; projections and tenant predicates belong to its caller.
# ==============================================


def base_select(model: type[QueryModel]) -> Select[tuple[QueryModel]]:
    """Build an ORM SELECT; projections and tenant predicates belong to its caller.

    This DB helper accepts its SQL model positionally, following the project's
    explicit exception for database helpers. It never removes ownership filters.
    """

    return select(model)
