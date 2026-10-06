from types import SimpleNamespace

import pytest

from app.repositories.base import BaseRepository


class FakeSession:
    def __init__(self, *, defer_commit: bool):
        self.info = {"defer_repository_commit": defer_commit}
        self.flushes = 0
        self.commits = 0
        self.rollbacks = 0

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_repository_update_defers_commit_inside_composed_transaction():
    session = FakeSession(defer_commit=True)
    entity = SimpleNamespace(status="pending")
    repository = BaseRepository.__new__(BaseRepository)
    repository.model = type("FakeOrder", (), {})
    repository.session = session

    async def get_by_id(*, id):
        return entity

    repository.get_by_id = get_by_id

    updated = await repository.update(id=1, data={"status": "cancelled"})

    assert updated is entity
    assert entity.status == "cancelled"
    assert session.flushes == 1
    assert session.commits == 0
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_repository_update_keeps_default_commit_behavior():
    session = FakeSession(defer_commit=False)
    entity = SimpleNamespace(status="pending")
    repository = BaseRepository.__new__(BaseRepository)
    repository.model = type("FakeOrder", (), {})
    repository.session = session

    async def get_by_id(*, id):
        return entity

    repository.get_by_id = get_by_id

    await repository.update(id=1, data={"status": "cancelled"})

    assert session.commits == 1
