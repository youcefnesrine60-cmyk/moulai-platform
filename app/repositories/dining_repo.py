# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICITLY SCOPED DINING REPOSITORY
# Retain restaurant and branch predicates on every dining read and row lock.
# ==============================================

"""No commits, remote configuration, permission fallback or unscoped ID lookup."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND GENERIC ORM SELECT CONTRACT
# The BASE SELECT helper is SQL-only and does not authorize its caller.
# ==============================================

from typing import TypeVar

from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.security.tenant_types import positive_id
from app.models.dining import (
    DiningBase,
    DiningPolicy,
)
from app.services.business.dining.values import DiningError

DiningRecord = TypeVar("DiningRecord", bound=DiningBase)


# ==============================================
# BASE SELECT ROOT
# Keep this DB helper's positional SQL model argument and concrete result type.
# ==============================================


def base_select(model: type[DiningRecord]) -> Select[tuple[DiningRecord]]:
    """Build a SELECT without ownership claims, I/O or eager relationship loads."""
    return select(model).options(raiseload("*"))


# ==============================================
# ONE RESTAURANT AND BRANCH REPOSITORY
# The authorized business unit owns scope verification, locks and the commit.
# ==============================================


class DiningRepository:
    """Enforce scalar scope on resources and persist only inside a caller transaction."""

    def __init__(
        self, *, session: AsyncSession, restaurant_id: int, branch_id: int
    ) -> None:
        """Bind positive keys without opening a connection or resolving authority."""
        self.session = session
        self.restaurant_id = positive_id(value=restaurant_id)
        self.branch_id = positive_id(value=branch_id)

    # ==============================================
    # STATEMENT
    # Preserve both scope predicates; an arbitrary global ID is never enough.
    # ==============================================

    def statement(self, *, model: type[DiningRecord]) -> Select[tuple[DiningRecord]]:
        """Preserve both scope predicates; an arbitrary global ID is never enough."""
        return base_select(model).where(
            model.restaurant_id == self.restaurant_id, model.branch_id == self.branch_id
        )

    # ==============================================
    # ONE
    # Reload one owned row; absent and foreign keys receive the same rejection.
    # ==============================================

    async def one(
        self, *, model: type[DiningRecord], identifier: int, lock: bool = False
    ) -> DiningRecord:
        """Reload one owned row; absent and foreign keys receive the same rejection."""
        positive_id(value=identifier)
        statement = (
            self.statement(model=model)
            .where(model.id == identifier)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).scalar_one_or_none()
        if row is None:
            raise DiningError(code="dining_resource_unavailable")
        return row

    # ==============================================
    # POLICY
    # Serialize branch planning writes on an explicit existing policy row.
    # ==============================================

    async def policy(self, *, lock: bool = False) -> DiningPolicy:
        """Serialize branch planning writes on an explicit existing policy row."""
        statement = self.statement(model=DiningPolicy).execution_options(
            populate_existing=True
        )
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).scalar_one_or_none()
        if row is None:
            raise DiningError(code="dining_policy_configuration_missing")
        return row

    # ==============================================
    # PERSIST
    # Flush a correctly scoped record without any independent commit.
    # ==============================================

    async def persist(self, *, record: DiningRecord) -> DiningRecord:
        """Flush a correctly scoped record without any independent commit."""
        if (record.restaurant_id, record.branch_id) != (
            self.restaurant_id,
            self.branch_id,
        ):
            raise DiningError(code="dining_record_scope_mismatch")
        if not self.session.in_transaction():
            raise DiningError(code="dining_owned_transaction_required")
        self.session.add(record)
        await self.session.flush()
        return record
