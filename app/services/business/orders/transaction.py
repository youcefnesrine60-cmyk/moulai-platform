"""Transaction boundary for order use cases.

A read-triggered AUTOBEGIN belongs to this use case. Explicit caller transactions
remain caller-owned. Composed order services share the outer unit of work.
"""
from contextlib import asynccontextmanager
from functools import wraps

from sqlalchemy.orm import SessionTransactionOrigin


@asynccontextmanager
async def order_transaction(session):
    info = session.info
    if info.get("order_unit_of_work"):
        # A caught child failure must not leak its partial writes into a batch.
        async with session.begin_nested():
            yield
        return
    active = session.in_transaction()
    current = session.get_transaction() if active else None
    owns_autobegin = bool(current and
        current.sync_transaction.origin is SessionTransactionOrigin.AUTOBEGIN)
    previous = info.get("defer_repository_commit")
    info["defer_repository_commit"] = True
    info["order_unit_of_work"] = True
    try:
        async with (session.begin_nested() if active else session.begin()):
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


def transactional_order(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        session = kwargs.get("session")
        if session is None:
            session = args[0].session
        async with order_transaction(session):
            return await function(*args, **kwargs)
    return wrapped
