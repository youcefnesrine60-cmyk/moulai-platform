# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔒 ORDERS TRANSACTION BOUNDARY
# إدارة المعاملات ونقاط الحفظ لعمليات الطلبات
# ==============================================

"""Transaction boundary for order use cases.

A read-triggered AUTOBEGIN belongs to this use case. Explicit caller transactions
remain caller-owned. Composed order services share the outer unit of work.
"""

from contextlib import asynccontextmanager
from functools import wraps
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    ParamSpec,
    TypeVar,
    cast,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import SessionTransactionOrigin

# ==============================================
# TRANSACTION TYPES
# ==============================================

P = ParamSpec("P")
ResultT = TypeVar("ResultT")


# ==============================================
# ORDER TRANSACTION CONTEXT
# ==============================================


@asynccontextmanager
async def order_transaction(session: AsyncSession) -> AsyncIterator[None]:
    """Provide the transaction boundary shared by order business operations."""
    info: dict[str, Any] = session.info
    if info.get("order_unit_of_work"):
        # A caught child failure must not leak its partial writes into a batch.
        async with session.begin_nested():
            yield
        return
    active = session.in_transaction()
    current = session.get_transaction() if active else None
    # Only a read-triggered transaction is owned and committed by this boundary.
    owns_autobegin = bool(
        current
        and current.sync_transaction.origin is SessionTransactionOrigin.AUTOBEGIN
    )
    previous = info.get("defer_repository_commit")
    info["defer_repository_commit"] = True
    info["order_unit_of_work"] = True
    try:
        async with session.begin_nested() if active else session.begin():
            yield
        if owns_autobegin:
            await session.commit()
    except BaseException:
        if owns_autobegin:
            await session.rollback()
        raise
    finally:
        info.pop("order_unit_of_work", None)
        if previous is None:
            info.pop("defer_repository_commit", None)
        else:
            info["defer_repository_commit"] = previous


# ==============================================
# ORDER TRANSACTION DECORATOR
# ==============================================


def transactional_order(
    function: Callable[P, Awaitable[ResultT]],
) -> Callable[P, Awaitable[ResultT]]:
    """Wrap an order operation in its session's transaction boundary."""

    # ==============================================
    # WRAPPED
    # ==============================================

    @wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        session = cast(AsyncSession | None, kwargs.get("session"))
        if session is None:
            if not args:
                raise TypeError("transactional order operations require a session")
            session = cast(AsyncSession | None, getattr(args[0], "session", None))
        if session is None:
            raise TypeError("transactional order operations require a session")
        async with order_transaction(cast(AsyncSession, session)):
            return await function(*args, **kwargs)

    return wrapped
