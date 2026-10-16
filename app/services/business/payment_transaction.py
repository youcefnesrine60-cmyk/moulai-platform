# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""SQLAlchemy transaction boundary for subscription billing operations."""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import SessionTransactionOrigin

# ==============================================
# MANAGE BILLING TRANSACTION OWNERSHIP
# ==============================================


@asynccontextmanager
async def payment_transaction(*, session: AsyncSession) -> AsyncIterator[None]:
    """Keep billing atomic without committing an explicitly owned transaction.

    An existing transaction receives a savepoint. Only an implicit SQLAlchemy
    AUTOBEGIN transaction owned by this operation may be committed or rolled
    back here; an explicit outer transaction remains under its caller's control.
    """
    active = session.in_transaction()
    current = session.get_transaction() if active else None
    sync_transaction = current.sync_transaction if current is not None else None
    owns_autobegin = (
        sync_transaction is not None
        and sync_transaction.origin is SessionTransactionOrigin.AUTOBEGIN
        and not session.info.get("defer_repository_commit")
    )
    previous = session.info.get("defer_repository_commit")
    session.info["defer_repository_commit"] = True
    try:
        transaction = session.begin_nested() if active else session.begin()
        async with transaction:
            yield
        if owns_autobegin:
            await session.commit()
    except BaseException:
        if owns_autobegin:
            await session.rollback()
        raise
    finally:
        if previous is None:
            session.info.pop("defer_repository_commit", None)
        else:
            session.info["defer_repository_commit"] = previous
