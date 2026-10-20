# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Build only disposable K10 HTTP routes; never import/register the runtime app."""

from collections.abc import (
    AsyncIterator,
    Callable,
)
from typing import (
    Annotated,
    TypeAlias,
)

from fastapi import (
    Depends,
    FastAPI,
    Path,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tenant_dependencies import (
    get_own_tenant_memberships,
    tenant_read_access,
)
from app.core.database import get_db
from app.schemas.tenant_access import (
    MembershipSummary,
    RestaurantSummary,
)
from app.services.business.tenant_access import TenantReadUnit

SessionDependency: TypeAlias = Callable[..., AsyncIterator[AsyncSession]]

# ==============================================
# EXPLICIT TEST-ONLY APPLICATION FACTORY
# ==============================================


def create_tenant_test_app(
    *,
    session_dependency: SessionDependency,
    restaurant_permission: str = "tenant.restaurants.read",
) -> FastAPI:
    """Use the existing guards with test-provided storage; own no runtime routes."""
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.dependency_overrides[get_db] = session_dependency
    read = tenant_read_access(permission=restaurant_permission)

    # ==============================================
    # PERSONAL ASSOCIATIONS, WITHOUT IMPLICIT COMPANY SELECTION
    # ==============================================

    @app.get("/test/memberships")
    async def memberships(
        rows: Annotated[
            tuple[MembershipSummary, ...], Depends(get_own_tenant_memberships)
        ],
    ) -> tuple[MembershipSummary, ...]:
        """Return authorized personal metadata, not business permissions or JWTs."""
        return rows

    # ==============================================
    # ONE EXPLICITLY SELECTED COMPANY'S RESTAURANTS
    # ==============================================

    @app.get("/test/organizations/{organization_id}/restaurants")
    async def restaurants(
        unit: Annotated[TenantReadUnit, Depends(read, scope="function")],
        after_id: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> tuple[RestaurantSummary, ...]:
        """Serialize detached, scoped outputs after the owned transaction closes."""
        return await unit.restaurants(after_id=after_id, limit=limit)

    # ==============================================
    # ONE COMPANY-QUALIFIED AND GRANT-QUALIFIED RESTAURANT
    # ==============================================

    @app.get("/test/organizations/{organization_id}/restaurants/{restaurant_id}")
    async def restaurant(
        restaurant_id: Annotated[int, Path(gt=0)],
        unit: Annotated[TenantReadUnit, Depends(read, scope="function")],
    ) -> RestaurantSummary:
        """Hide whether a denied restaurant is absent, foreign or ungranted."""
        return await unit.restaurant(restaurant_id=restaurant_id)

    return app
