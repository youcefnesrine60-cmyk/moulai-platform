# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Use the established repository transaction convention for catalog batches."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import SessionTransactionOrigin

# ==============================================
# CATALOG BATCH TRANSACTION OWNERSHIP
# ==============================================


@asynccontextmanager
async def catalog_transaction(*, session: AsyncSession) -> AsyncIterator[None]:
    """Commit an owned batch once, retaining explicit caller-owned transactions.

    Match the existing billing/order convention without changing those domains:
    repositories flush while ``defer_repository_commit`` is set. Existing
    transactions receive a savepoint; a clean AUTOBEGIN can belong to this use
    case, whereas an explicit or already-managed transaction remains external.
    Refuse pending work before begin_nested can flush unrelated caller changes.
    """
    if session.new or session.dirty or session.deleted:
        raise ValueError("catalog_batch_requires_clean_unit_of_work")

    active = session.in_transaction()
    previous = session.info.get("defer_repository_commit")
    if previous and not active:
        raise ValueError("catalog_deferred_transaction_requires_active_transaction")
    current = session.get_transaction() if active else None
    sync_transaction = current.sync_transaction if current is not None else None
    owns_autobegin = (
        sync_transaction is not None
        and sync_transaction.origin is SessionTransactionOrigin.AUTOBEGIN
        and not previous
    )
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
