# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT E1 RESTAURANT COMPANY PROJECTION
# Read the reviewed E1/O4 column without forcing a later field into the historical S1b restaurant mapping.
# ==============================================

"""Static SQL expression only; ownership and current tenant authority remain mandatory at every caller."""

# isort: split
# ==============================================
# TRUSTED COLUMN EXPRESSION
# Neither its identifier nor its type can be supplied through an HTTP request.
# ==============================================

from sqlalchemy import (
    Integer,
    literal_column,
)
from sqlalchemy.sql.elements import ColumnClause


def company_column() -> ColumnClause[int]:
    """Return the fixed E1 column for BASE SELECT statements already rooted in restaurants."""
    return literal_column("restaurants.organization_id", Integer)
