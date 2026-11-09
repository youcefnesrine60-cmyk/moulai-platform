# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED LOCAL DINING TEST CONNECTIONS
# Admit only the fresh loopback server prepared by the explicit dining launcher.
# ==============================================

"""No external transaction rollback fixture can conceal service commit defects."""

# isort: split
# ==============================================
# IMPORTS AND REAL LOCAL ENGINE
# Use independent sessions for writers and observers on the migrated D1 schema.
# ==============================================

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

from migration_support.dining_d1d import D1D_REVISION
from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# ADMITTED OWNED LOCAL SERVER
# Refuse every permanent profile before the first connection can be opened.
# ==============================================


@pytest.fixture
async def dining_engine(request: pytest.FixtureRequest) -> AsyncIterator[AsyncEngine]:
    """Open only the disposable dining profile; never read a configured remote URL."""
    if not request.config.getoption("--local-postgres-tests", default=False):
        pytest.skip("Dining live proofs require the isolated local launcher")
    configuration = LocalPostgresSettings()
    assert configuration.PROFILE == "dining"
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        hide_parameters=True,
        connect_args={"ssl": False, "timeout": 10, "command_timeout": 30},
        pool_size=6,
        max_overflow=4,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == D1D_REVISION
            )
        yield engine
    finally:
        await engine.dispose()
